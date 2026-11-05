import os
import sys

import pytest

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, ROOT)
sys.path.insert(0, os.path.join(ROOT, "tests"))

import colorbar_core as core  # noqa: E402
from make_sample import build_pdf  # noqa: E402


def approx(v, target, tol=0.005):
    return abs(v - target) <= tol


def test_horizontal_bar_size_and_map():
    res = core.analyze(build_pdf("horizontal"))
    assert len(res["candidates"]) == 1, "decoys must not become candidates"
    c = res["candidates"][0]
    assert c["orientation"] == "horizontal"
    assert approx(c["patch_w_mm"], 4.0) and approx(c["patch_h_mm"], 6.0)
    assert approx(c["pitch_mm"], 4.0)
    assert c["patch_count"] == 16
    assert c["slot_count"] == 18
    assert c["empty_slots"] == [8, 9]
    assert approx(c["origin_mm"]["x"], 14.0, 0.05)
    assert c["warnings"] == []


def test_spot_colors_are_numbered_not_named():
    c = core.analyze(build_pdf("horizontal"))["candidates"][0]
    assert [s["label"] for s in c["spots"]] == ["S1"]
    labels = [p["label"] for p in c["patches"]]
    assert "S1 100" in labels and "S1 25" in labels and "S1 75" in labels
    assert "K100" in labels and "C50 M40 Y40" in labels and "Paper (no ink)" in labels


def test_production_ink_and_rgb_decoys_are_ignored():
    res = core.analyze(build_pdf("horizontal"))
    assert res["ignored"]["production_ink_rectangles"] >= 5
    # no candidate should sit in the decoy area (the bar is at the bottom of the page)
    for c in res["candidates"]:
        assert c["origin_mm"]["y"] > 50  # mm from top; decoys are above this


def test_vertical_bar():
    c = core.analyze(build_pdf("vertical"))["candidates"][0]
    assert c["orientation"] == "vertical"
    assert approx(c["patch_w_mm"], 6.0) and approx(c["patch_h_mm"], 4.0)
    assert approx(c["pitch_mm"], 4.0)
    assert c["patch_count"] == 16 and c["empty_slots"] == [8, 9]


def test_no_bar_found():
    res = core.analyze(build_pdf("horizontal", with_bar=False, rgb_decoy=False))
    assert res["candidates"] == []


def test_rgb_only_row_is_reported_with_a_warning():
    # No real bar, but a row of RGB swatches: shown as a last resort, never silently.
    res = core.analyze(build_pdf("horizontal", with_bar=False))
    assert len(res["candidates"]) == 1
    assert any("RGB" in w for w in res["candidates"][0]["warnings"])


def test_rgb_row_is_ignored_when_a_real_bar_exists():
    res = core.analyze(build_pdf("horizontal"))
    assert all(not any("RGB" in w for w in c["warnings"]) for c in res["candidates"])


def test_accepts_bytes_path_and_file_object(tmp_path):
    data = build_pdf("horizontal")
    p = tmp_path / "x.pdf"
    p.write_bytes(data)
    a = core.analyze(data)["candidates"][0]["patch_count"]
    b = core.analyze(str(p))["candidates"][0]["patch_count"]
    with open(p, "rb") as fh:
        c = core.analyze(fh)["candidates"][0]["patch_count"]
    assert a == b == c == 16


def test_web_result_has_csv():
    res = core.analyze_for_web(build_pdf("horizontal"))
    csv_text = res["candidates"][0]["csv"]
    header = csv_text.splitlines()[0].split(",")
    assert header[:2] == ["slot", "stacked"] and "S1" in header
    assert len(csv_text.splitlines()) == 1 + 16


def test_committed_sample_matches_generator():
    path = os.path.join(ROOT, "tests", "sample", "sample_bar.pdf")
    if not os.path.exists(path):
        pytest.skip("sample not generated yet")
    assert open(path, "rb").read() == build_pdf("horizontal")
