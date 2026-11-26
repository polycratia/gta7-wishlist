import io
from datetime import date
from pathlib import Path

from gta7_wishlist import load_all, load_updates, validate, watch
from gta7_wishlist.cli import main

ROOT = Path(__file__).resolve().parent.parent
UPDATES_DIR = ROOT / "updates"

PROPOSAL_URL = "https://www.rockstargames.com/gta-vi"
UPDATE_URL = "https://www.rockstargames.com/newswire/article/gta-vi-title-update"
PROBLEM = "GTA 6 ships without a mission replay option, so a finished mission cannot be repeated."
PROPOSAL = "Add a mission replay menu so any finished story mission can be restarted from a menu."
SUMMARY = "Adds mission replay to the pause menu for finished story missions."


def write_proposal(
    directory,
    proposal_id,
    status="open",
    addressed_by=None,
    addressed_note=None,
    checked_on="2026-11-22",
):
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        f'id = "{proposal_id}"',
        f'title = "Wish about {proposal_id}"',
        'category = "missions"',
        f'status = "{status}"',
        f'problem = "{PROBLEM}"',
        f'proposal = "{PROPOSAL}"',
    ]
    if addressed_by is not None:
        lines.append(f'addressed_by = "{addressed_by}"')
    if addressed_note is not None:
        lines.append(f'addressed_note = "{addressed_note}"')

    dates = (checked_on,) if isinstance(checked_on, str) else tuple(checked_on)
    for moment in dates:
        lines += ["", "[[evidence]]", f'url = "{PROPOSAL_URL}"', f'checked_on = "{moment}"']

    path = directory / f"{proposal_id}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def write_update(
    directory,
    update_id,
    version,
    released_on,
    checked_on="2026-12-11",
    url=UPDATE_URL,
):
    directory.mkdir(parents=True, exist_ok=True)
    lines = [
        f'id = "{update_id}"',
        f'version = "{version}"',
        f'released_on = "{released_on}"',
        f'summary = "{SUMMARY}"',
        "",
        "[[evidence]]",
        f'url = "{url}"',
        f'checked_on = "{checked_on}"',
    ]
    path = directory / f"{update_id}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def dirs(tmp_path):
    proposals = tmp_path / "proposals"
    updates = tmp_path / "updates"
    proposals.mkdir()
    updates.mkdir()
    return proposals, updates


def problems(proposals, updates):
    return validate(load_all(proposals), load_updates(updates))


def run(*argv, proposals, updates):
    out = io.StringIO()
    code = main(["--dir", str(proposals), *argv, "--updates", str(updates)], out=out)
    return code, out.getvalue()


def test_no_update_is_recorded_yet():
    assert load_updates(UPDATES_DIR) == []
    assert (UPDATES_DIR / "README.md").is_file()


def test_an_addressed_proposal_without_an_update_is_refused(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-1-02"
    )

    found = problems(proposals, updates)

    assert len(found) == 1
    assert "gta6-1-02" in found[0]


def test_an_addressed_proposal_needs_addressed_by(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "mission-replay", status="addressed")

    found = problems(proposals, updates)

    assert len(found) == 1
    assert "addressed_by" in found[0]


def test_addressed_by_on_an_open_proposal_is_refused(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "mission-replay", addressed_by="gta6-1-02")
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    found = problems(proposals, updates)

    assert len(found) == 1
    assert "'open'" in found[0]


def test_an_update_needs_an_https_source(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_update(
        updates, "gta6-1-02", "1.02", "2026-12-10", url="http://example.com/patch"
    )

    found = problems(proposals, updates)

    assert len(found) == 1
    assert "https://" in found[0]


def test_an_update_released_after_its_own_evidence_is_refused(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-1-02"
    )
    write_update(updates, "gta6-1-02", "1.02", "2026-12-24", checked_on="2026-12-11")

    found = problems(proposals, updates)

    assert any("released_on" in problem for problem in found)
    assert any("not out yet" in problem for problem in found)


def test_a_proposal_appears_under_the_update_that_addressed_it(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "pc-at-launch")
    write_proposal(
        proposals,
        "mission-replay",
        status="addressed",
        addressed_by="gta6-1-02",
        addressed_note="Replay works from the pause menu.",
    )
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    assert problems(proposals, updates) == []

    report = watch.status_report(
        load_all(proposals), load_updates(updates), today=date(2026, 12, 20)
    )

    assert [row.id for row in report.addressed] == ["mission-replay"]
    assert report.addressed[0].version == "1.02"
    assert report.addressed[0].released_on == "2026-12-10"
    assert report.addressed[0].note == "Replay works from the pause menu."
    assert [row.id for row in report.still_open] == ["pc-at-launch"]
    assert report.unmatched == ()


def test_days_open_counts_from_the_earliest_evidence(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "pc-at-launch", checked_on=("2026-12-01", "2026-11-22"))
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-1-02"
    )
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    report = watch.status_report(
        load_all(proposals), load_updates(updates), today=date(2026, 12, 20)
    )

    assert report.still_open[0].since == "2026-11-22"
    assert report.still_open[0].days_open == 28
    assert report.addressed[0].days_open == 18


def test_a_proposal_addressed_by_an_unknown_update_is_kept_apart(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-9-99"
    )

    report = watch.status_report(load_all(proposals), load_updates(updates))

    assert report.addressed == ()
    assert [row.id for row in report.unmatched] == ["mission-replay"]


def test_filter_since_keeps_only_the_newer_update(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-1-02"
    )
    write_proposal(
        proposals, "cheats-before-credits", status="addressed", addressed_by="gta6-1-01"
    )
    write_update(updates, "gta6-1-01", "1.01", "2026-11-28", checked_on="2026-11-29")
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    report = watch.status_report(load_all(proposals), load_updates(updates))
    recent = watch.filter_since(report, "2026-12-01")

    assert [update.id for update in recent.updates] == ["gta6-1-02"]
    assert [row.id for row in recent.addressed] == ["mission-replay"]
    assert recent.still_open == ()


def test_status_prints_every_group(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "pc-at-launch")
    write_proposal(proposals, "flying-cars", status="declined")
    write_proposal(
        proposals,
        "mission-replay",
        status="addressed",
        addressed_by="gta6-1-02",
        addressed_note="Replay works from the pause menu.",
    )
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    code, output = run("status", proposals=proposals, updates=updates)

    assert code == 0
    assert "3 wishes tracked: 1 still open, 1 addressed, 1 declined" in output
    assert "1.02 (gta6-1-02), released 2026-12-10" in output
    assert "Replay works from the pause menu." in output
    assert "Still open" in output
    assert "pc-at-launch" in output
    assert "Declined" in output


def test_status_says_so_when_no_update_is_recorded(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "pc-at-launch")

    code, output = run("status", proposals=proposals, updates=updates)

    assert code == 0
    assert "No GTA 6 title update is recorded yet." in output


def test_status_since_lists_only_the_newer_change(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(
        proposals, "mission-replay", status="addressed", addressed_by="gta6-1-02"
    )
    write_proposal(
        proposals, "cheats-before-credits", status="addressed", addressed_by="gta6-1-01"
    )
    write_update(updates, "gta6-1-01", "1.01", "2026-11-28", checked_on="2026-11-29")
    write_update(updates, "gta6-1-02", "1.02", "2026-12-10")

    code, output = run(
        "status", "--since", "2026-12-01", proposals=proposals, updates=updates
    )

    assert code == 0
    assert "1 update recorded since 2026-12-01" in output
    assert "mission-replay" in output
    assert "cheats-before-credits" not in output


def test_status_since_with_nothing_recorded(tmp_path):
    proposals, updates = dirs(tmp_path)
    write_proposal(proposals, "pc-at-launch")

    code, output = run(
        "status", "--since", "2026-12-01", proposals=proposals, updates=updates
    )

    assert code == 0
    assert "no GTA 6 title update recorded since 2026-12-01" in output


def test_a_bad_since_date_exits_2(tmp_path):
    proposals, updates = dirs(tmp_path)

    code, output = run(
        "status", "--since", "last tuesday", proposals=proposals, updates=updates
    )

    assert code == 2
    assert "YYYY-MM-DD" in output


def test_a_missing_updates_directory_exits_2(tmp_path):
    proposals, _ = dirs(tmp_path)

    code, output = run("status", proposals=proposals, updates=tmp_path / "nowhere")

    assert code == 2
    assert "not an updates directory" in output
