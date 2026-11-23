import io
from pathlib import Path

from gta7_wishlist.cli import main

PROPOSALS_DIR = Path(__file__).resolve().parent.parent / "proposals"

CHEATS_EVIDENCE = (
    "https://www.redbull.com/us-en/gta-6-cheat-codes",
    "https://www.pcguide.com/news/gta-6-cheat-codes-list-for-playstation-5"
    "-xbox-series-xs-and-how-to-unlock-them/",
)

BROKEN_PROPOSAL = """id = "no-evidence-at-all"
title = "Let the radio keep playing when a cutscene starts"
category = "world"
status = "open"
problem = "In GTA 6 the radio cuts out whenever a cutscene begins, and the song restarts."
proposal = "Keep the current station playing under cutscenes so a song is never lost."
"""


def run(*argv, directory=PROPOSALS_DIR):
    out = io.StringIO()
    code = main(["--dir", str(directory), *argv], out=out)
    return code, out.getvalue()


def test_list_shows_every_shipped_proposal():
    code, output = run("list")

    assert code == 0
    for proposal_id in ("cheats-before-credits", "mission-replay", "pc-at-launch"):
        assert proposal_id in output


def test_list_filters_by_category():
    code, output = run("list", "--category", "platforms")
    lines = output.strip().splitlines()

    assert code == 0
    assert len(lines) == 1
    assert lines[0].startswith("pc-at-launch")
    assert "platforms" in lines[0]


def test_list_filters_by_status():
    code, output = run("list", "--status", "addressed")

    assert code == 0
    assert output.strip() == "no proposal matches"


def test_unknown_category_exits_2():
    code, output = run("list", "--category", "vehicles")

    assert code == 2
    assert "vehicles" in output
    assert "platforms" in output


def test_show_prints_both_evidence_urls():
    code, output = run("show", "cheats-before-credits")

    assert code == 0
    for url in CHEATS_EVIDENCE:
        assert url in output
    assert "2026-11-22" in output
    assert "progression" in output


def test_unknown_id_exits_2_and_names_the_closest_id():
    code, output = run("show", "mission-replays")

    assert code == 2
    assert "mission-replays" in output
    assert "mission-replay" in output.splitlines()[1]


def test_check_passes_on_the_shipped_proposals():
    code, output = run("check")

    assert code == 0
    assert "no problems" in output


def test_check_reports_a_broken_proposal(tmp_path):
    path = tmp_path / "no-evidence-at-all.toml"
    path.write_text(BROKEN_PROPOSAL, encoding="utf-8")

    code, output = run("check", directory=tmp_path)
    lines = output.strip().splitlines()

    assert code == 1
    assert len(lines) == 1
    assert lines[0].startswith(f"{path}: ")
    assert "evidence" in lines[0]


def test_categories_counts_each_proposal():
    code, output = run("categories")
    counts = dict(line.split() for line in output.strip().splitlines())

    assert code == 0
    assert counts["missions"] == "1"
    assert counts["platforms"] == "1"
    assert counts["progression"] == "1"
    assert counts["online"] == "0"


def test_directory_comes_from_the_environment(monkeypatch):
    monkeypatch.setenv("GTA7_WISHLIST_DIR", str(PROPOSALS_DIR))
    out = io.StringIO()

    assert main(["check"], out=out) == 0


def test_missing_directory_exits_2(tmp_path):
    out = io.StringIO()

    assert main(["--dir", str(tmp_path / "nowhere"), "list"], out=out) == 2
