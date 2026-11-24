import io
import tomllib
from datetime import date
from pathlib import Path

import pytest

from gta7_wishlist import Evidence, Proposal, mine
from gta7_wishlist.cli import main

PROPOSALS_DIR = Path(__file__).resolve().parent.parent / "proposals"
EVIDENCE_URL = "https://www.rockstargames.com/gta-vi"
TEXT = "What GTA 6 does today, written out at a believable length for a test."

NOTE = 'She said "replay it" and left.\nBack-slash: \\ and a tab:\tdone.'


def proposal(proposal_id, title=None, category="missions"):
    return Proposal(
        id=proposal_id,
        title=title or f"Wish about {proposal_id}",
        category=category,
        problem=TEXT,
        proposal=TEXT,
        status="open",
        evidence=(Evidence(url=EVIDENCE_URL, checked_on="2026-11-22"),),
    )


CATALOGUE = [
    proposal(
        "mission-replay", "Ship mission replay and chapter select on day one", "missions"
    ),
    proposal(
        "pc-at-launch",
        "Announce the PC date together with the console date",
        "platforms",
    ),
    proposal(
        "cheats-before-credits",
        "Allow single-player cheats from the start of the game",
        "progression",
    ),
]


def empty():
    return mine.Wishlist(handle="polycratia", updated_on="2026-11-24")


def three_picks():
    wishlist = empty()
    for item in CATALOGUE:
        wishlist = mine.pick(wishlist, item.id, CATALOGUE)
    return wishlist


def ranked(wishlist):
    return [(item.id, item.rank) for item in wishlist.picks]


def test_pick_appends_at_the_next_rank():
    assert ranked(three_picks()) == [
        ("mission-replay", 1),
        ("pc-at-launch", 2),
        ("cheats-before-credits", 3),
    ]


def test_an_unknown_proposal_is_refused():
    with pytest.raises(mine.WishlistError) as error:
        mine.pick(empty(), "flying-cars", CATALOGUE)

    assert error.value.code == mine.UNKNOWN_PROPOSAL
    assert "flying-cars" in str(error.value)


def test_the_same_proposal_cannot_be_picked_twice():
    wishlist = mine.pick(empty(), "pc-at-launch", CATALOGUE)

    with pytest.raises(mine.WishlistError) as error:
        mine.pick(wishlist, "pc-at-launch", CATALOGUE)

    assert error.value.code == mine.ALREADY_PICKED


def test_ranks_stay_dense_after_a_drop():
    wishlist = mine.drop(three_picks(), "pc-at-launch")

    assert ranked(wishlist) == [("mission-replay", 1), ("cheats-before-credits", 2)]


def test_dropping_a_proposal_that_was_never_picked_is_refused():
    with pytest.raises(mine.WishlistError) as error:
        mine.drop(three_picks(), "flying-cars")

    assert error.value.code == mine.NOT_PICKED


def test_ranks_stay_dense_after_a_move():
    to_the_top = mine.move(three_picks(), "cheats-before-credits", 1)

    assert ranked(to_the_top) == [
        ("cheats-before-credits", 1),
        ("mission-replay", 2),
        ("pc-at-launch", 3),
    ]

    to_the_bottom = mine.move(to_the_top, "cheats-before-credits", 3)

    assert ranked(to_the_bottom) == [
        ("mission-replay", 1),
        ("pc-at-launch", 2),
        ("cheats-before-credits", 3),
    ]


def test_a_rank_outside_the_list_is_refused():
    for rank in (0, 4):
        with pytest.raises(mine.WishlistError) as error:
            mine.move(three_picks(), "mission-replay", rank)
        assert error.value.code == mine.BAD_RANK


def test_the_26th_pick_is_refused():
    catalogue = [proposal(f"wish-{index:02d}") for index in range(mine.MAX_PICKS + 5)]
    wishlist = empty()
    for item in catalogue[: mine.MAX_PICKS]:
        wishlist = mine.pick(wishlist, item.id, catalogue)

    assert len(wishlist.picks) == mine.MAX_PICKS

    with pytest.raises(mine.WishlistError) as error:
        mine.pick(wishlist, catalogue[mine.MAX_PICKS].id, catalogue)

    assert error.value.code == mine.TOO_MANY


def test_a_note_with_a_quote_and_a_newline_survives_the_round_trip(tmp_path):
    wishlist = mine.pick(empty(), "mission-replay", CATALOGUE, note=NOTE)
    path = tmp_path / "my-wishlist.toml"

    mine.save_wishlist(path, wishlist)
    with path.open("rb") as handle:
        raw = tomllib.load(handle)

    assert raw["handle"] == "polycratia"
    assert raw["picks"][0]["note"] == NOTE
    assert mine.load_wishlist(path).picks[0].note == NOTE


def test_a_hand_edited_file_is_renumbered_on_load(tmp_path):
    path = tmp_path / "my-wishlist.toml"
    path.write_text(
        'handle = "polycratia"\n'
        'updated_on = "2026-11-24"\n\n'
        '[[picks]]\nid = "pc-at-launch"\nrank = 9\n\n'
        '[[picks]]\nid = "mission-replay"\nrank = 4\n',
        encoding="utf-8",
    )

    assert ranked(mine.load_wishlist(path)) == [
        ("mission-replay", 1),
        ("pc-at-launch", 2),
    ]


def test_a_missing_file_reads_as_an_empty_wishlist(tmp_path):
    assert mine.load_wishlist(tmp_path / "nothing.toml").picks == ()


def test_render_markdown_is_a_ranked_card_with_a_count_per_category():
    lines = mine.render_markdown(three_picks(), CATALOGUE).splitlines()

    assert lines[0] == "# My GTA 7 wishlist"
    assert "By @polycratia, updated 2026-11-24." in lines
    assert (
        "1. **Ship mission replay and chapter select on day one** (missions) "
        "- `mission-replay`" in lines
    )
    assert lines[-1] == "3 picks: missions 1, platforms 1, progression 1."


def test_render_markdown_keeps_a_multi_line_note_inside_the_item():
    wishlist = mine.pick(empty(), "pc-at-launch", CATALOGUE, note=NOTE)

    lines = mine.render_markdown(wishlist, CATALOGUE).splitlines()

    assert '   She said "replay it" and left.' in lines
    assert lines[-1] == "1 pick: platforms 1."


def run(*argv, path, directory=PROPOSALS_DIR):
    out = io.StringIO()
    code = main(["--dir", str(directory), *argv, "--file", str(path)], out=out)
    return code, out.getvalue()


def test_pick_move_drop_and_mine_from_the_command_line(tmp_path):
    path = tmp_path / "my-wishlist.toml"

    assert run("pick", "mission-replay", "--handle", "polycratia", path=path)[0] == 0
    assert run("pick", "pc-at-launch", "--note", 'I only have a "PC".', path=path)[0] == 0
    assert run("move", "pc-at-launch", "1", path=path)[0] == 0

    code, output = run("mine", path=path)
    lines = output.splitlines()

    assert code == 0
    assert lines[0].startswith("@polycratia  2 of 25 picks")
    assert lines[2].split()[:2] == ["1", "pc-at-launch"]
    assert 'I only have a "PC".' in output
    assert mine.load_wishlist(path).updated_on == date.today().isoformat()

    code, output = run("drop", "mission-replay", path=path)

    assert code == 0
    assert "1 pick left" in output

    code, output = run("mine", "--markdown", path=path)

    assert code == 0
    assert output.startswith("# My GTA 7 wishlist")
    assert "mission-replay" not in output


def test_picking_an_unknown_id_exits_2_and_names_the_closest(tmp_path):
    path = tmp_path / "my-wishlist.toml"

    code, output = run("pick", "mission-replays", path=path)

    assert code == 2
    assert "mission-replay" in output
    assert not path.exists()


def test_mine_says_so_when_nothing_is_picked_yet(tmp_path):
    code, output = run("mine", path=tmp_path / "my-wishlist.toml")

    assert code == 0
    assert "no picks yet" in output


def test_the_wishlist_file_comes_from_the_environment(tmp_path, monkeypatch):
    path = tmp_path / "from-env.toml"
    monkeypatch.setenv("GTA7_MY_WISHLIST", str(path))
    out = io.StringIO()

    code = main(["--dir", str(PROPOSALS_DIR), "pick", "pc-at-launch"], out=out)

    assert code == 0
    assert mine.load_wishlist(path).picks[0].id == "pc-at-launch"
