from pathlib import Path

from gta7_wishlist import Evidence, Proposal, load_all, tally
from gta7_wishlist.tally import BALLOT_LENGTH

PROPOSALS_DIR = Path(__file__).resolve().parent.parent / "proposals"
WISHLISTS_DIR = Path(__file__).resolve().parent.parent / "wishlists"
EVIDENCE_URL = "https://www.rockstargames.com/gta-vi"
TEXT = "What GTA 6 does today, written out at a believable length for a test."


def proposal(proposal_id, status="open"):
    return Proposal(
        id=proposal_id,
        title=f"Wish about {proposal_id}",
        category="missions",
        problem=TEXT,
        proposal=TEXT,
        status=status,
        evidence=(Evidence(url=EVIDENCE_URL, checked_on="2026-11-22"),),
    )


CATALOGUE = [
    proposal("mission-replay"),
    proposal("pc-at-launch"),
    proposal("cheats-before-credits"),
]


def write_ballot(directory, handle, picks, handle_in_file=None):
    lines = [
        f'handle = "{handle if handle_in_file is None else handle_in_file}"',
        'updated_on = "2026-11-25"',
    ]
    for proposal_id, rank in picks:
        lines += ["", "[[picks]]", f'id = "{proposal_id}"', f"rank = {rank}"]

    path = directory / f"{handle}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def counts(report):
    return [
        (row.id, row.points, row.picks, row.first_places, row.rank)
        for row in report.standings
    ]


def test_borda_points_over_three_ballots(tmp_path):
    write_ballot(tmp_path, "alpha", [("mission-replay", 1), ("pc-at-launch", 2)])
    write_ballot(
        tmp_path,
        "bravo",
        [("pc-at-launch", 1), ("cheats-before-credits", 2), ("mission-replay", 3)],
    )
    write_ballot(
        tmp_path, "charlie", [("mission-replay", 1), ("cheats-before-credits", 2)]
    )

    report = tally(tmp_path, CATALOGUE)

    assert report.rejected == ()
    assert report.counted == ("alpha", "bravo", "charlie")
    assert counts(report) == [
        ("mission-replay", 73, 3, 2, 1),
        ("pc-at-launch", 49, 2, 1, 2),
        ("cheats-before-credits", 48, 2, 0, 3),
    ]


def test_tied_proposals_share_a_rank_and_the_next_rank_skips(tmp_path):
    catalogue = [proposal(name) for name in ("wish-a", "wish-b", "wish-c", "wish-d")]
    write_ballot(tmp_path, "one", [("wish-a", 1), ("wish-b", 2), ("wish-c", 3)])
    write_ballot(tmp_path, "two", [("wish-a", 1), ("wish-c", 2), ("wish-b", 3)])

    report = tally(tmp_path, catalogue)

    assert counts(report) == [
        ("wish-a", 50, 2, 2, 1),
        ("wish-b", 47, 2, 0, 2),
        ("wish-c", 47, 2, 0, 2),
        ("wish-d", 0, 0, 0, 4),
    ]


def test_a_ballot_with_a_gap_in_the_ranks_is_rejected_and_named(tmp_path):
    write_ballot(tmp_path, "gappy", [("mission-replay", 1), ("pc-at-launch", 3)])

    report = tally(tmp_path, CATALOGUE)

    assert report.counted == ()
    assert len(report.rejected) == 1
    assert report.rejected[0].handle == "gappy"
    assert "gappy.toml" in report.rejected[0].path
    assert "1..2" in report.rejected[0].reason
    assert all(row.points == 0 for row in report.standings)


def test_an_unknown_pick_rejects_the_whole_ballot(tmp_path):
    write_ballot(tmp_path, "dreamer", [("mission-replay", 1), ("flying-cars", 2)])

    report = tally(tmp_path, CATALOGUE)

    assert report.counted == ()
    assert "flying-cars" in report.rejected[0].reason


def test_the_same_proposal_twice_rejects_the_whole_ballot(tmp_path):
    write_ballot(tmp_path, "twice", [("mission-replay", 1), ("mission-replay", 2)])

    report = tally(tmp_path, CATALOGUE)

    assert report.counted == ()
    assert "twice" in report.rejected[0].reason


def test_the_handle_has_to_match_the_file_name(tmp_path):
    path = write_ballot(
        tmp_path, "example-jason", [("mission-replay", 1)], handle_in_file="jason"
    )

    report = tally([path], CATALOGUE)

    assert report.counted == ()
    assert "jason" in report.rejected[0].reason
    assert "example-jason" in report.rejected[0].reason


def test_declined_picks_are_ignored_and_listed(tmp_path):
    catalogue = [proposal("mission-replay"), proposal("flying-cars", status="declined")]
    write_ballot(tmp_path, "hopeful", [("flying-cars", 1), ("mission-replay", 2)])

    report = tally(tmp_path, catalogue)

    assert report.counted == ("hopeful",)
    assert counts(report) == [("mission-replay", 24, 1, 0, 1)]
    assert len(report.ignored) == 1
    assert report.ignored[0].handle == "hopeful"
    assert report.ignored[0].id == "flying-cars"
    assert "declined" in report.ignored[0].reason


def test_a_full_ballot_spends_25_points_down_to_1(tmp_path):
    catalogue = [
        proposal(f"wish-{index:02d}") for index in range(1, BALLOT_LENGTH + 1)
    ]
    write_ballot(
        tmp_path,
        "complete",
        [(item.id, rank) for rank, item in enumerate(catalogue, start=1)],
    )

    report = tally(tmp_path, catalogue)

    assert report.rejected == ()
    assert counts(report)[0] == ("wish-01", BALLOT_LENGTH, 1, 1, 1)
    assert counts(report)[-1] == (f"wish-{BALLOT_LENGTH:02d}", 1, 1, 0, BALLOT_LENGTH)


def test_a_ballot_longer_than_the_ballot_length_is_rejected(tmp_path):
    catalogue = [
        proposal(f"wish-{index:02d}") for index in range(1, BALLOT_LENGTH + 2)
    ]
    write_ballot(
        tmp_path,
        "greedy",
        [(item.id, rank) for rank, item in enumerate(catalogue, start=1)],
    )

    report = tally(tmp_path, catalogue)

    assert report.counted == ()
    assert str(BALLOT_LENGTH) in report.rejected[0].reason


def test_the_example_ballots_count_against_the_shipped_proposals():
    report = tally(WISHLISTS_DIR, load_all(PROPOSALS_DIR))

    assert report.rejected == ()
    assert report.ignored == ()
    assert report.counted == ("example-jason", "example-lucia")
    assert counts(report) == [
        ("mission-replay", 49, 2, 1, 1),
        ("pc-at-launch", 48, 2, 1, 2),
        ("cheats-before-credits", 24, 1, 0, 3),
    ]
