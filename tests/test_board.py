import io
from pathlib import Path

from gta7_wishlist import Evidence, Proposal, board, load_all, render_board, tally
from gta7_wishlist.board import tally_board
from gta7_wishlist.cli import main

ROOT = Path(__file__).resolve().parent.parent
PROPOSALS_DIR = ROOT / "proposals"
WISHLISTS_DIR = ROOT / "wishlists"
EVIDENCE_URL = "https://www.rockstargames.com/gta-vi"
TEXT = "What GTA 6 does today, written out at a believable length for a test."


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


def write_ballot(directory, handle, picks):
    lines = [f'handle = "{handle}"', 'updated_on = "2026-11-25"']
    for proposal_id, rank in picks:
        lines += ["", "[[picks]]", f'id = "{proposal_id}"', f"rank = {rank}"]
    path = directory / f"{handle}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def committed_board():
    proposals = load_all(PROPOSALS_DIR)
    return render_board(tally_board(WISHLISTS_DIR, proposals), proposals)


def test_the_committed_leaderboard_file_is_up_to_date():
    path = ROOT / board.LEADERBOARD_FILE

    assert path.read_text(encoding="utf-8") == committed_board()


def test_the_readme_board_block_is_up_to_date():
    text = (ROOT / board.README_FILE).read_text(encoding="utf-8")

    assert board.read_block(text) == committed_board()


def test_the_example_ballots_are_left_out_of_the_board():
    proposals = load_all(PROPOSALS_DIR)

    assert tally(WISHLISTS_DIR, proposals).counted == (
        "example-jason",
        "example-lucia",
    )
    assert tally_board(WISHLISTS_DIR, proposals).counted == ()
    assert board.EMPTY in committed_board()
    assert "| Rank |" not in committed_board()


def test_a_real_ballot_builds_the_table_and_the_top_three(tmp_path):
    catalogue = [
        proposal("mission-replay"),
        proposal("pc-at-launch", category="platforms"),
        proposal("quiet-wish"),
    ]
    write_ballot(tmp_path, "alpha", [("mission-replay", 1), ("pc-at-launch", 2)])
    write_ballot(tmp_path, "example-zoe", [("pc-at-launch", 1)])

    rendered = render_board(tally_board(tmp_path, catalogue), catalogue)
    table, section = rendered.split(board.CATEGORY_HEADING)
    rows = [line for line in table.splitlines() if line.startswith("| ")]

    assert "Built from 1 ballot in `wishlists/`." in rendered.splitlines()
    assert len(rows) == 5
    assert "mission-replay.toml" in rows[2]
    assert rows[2].endswith("| missions | 1 | 25 |")
    assert rows[3].endswith("| platforms | 1 | 24 |")
    assert "- **missions**" in section
    assert "  1. Wish about mission-replay - 25 points" in section
    assert "quiet-wish" in table
    assert "quiet-wish" not in section


def test_only_three_wishes_show_per_category(tmp_path):
    catalogue = [proposal(f"wish-{index}") for index in range(1, 6)]
    write_ballot(
        tmp_path, "alpha", [(f"wish-{index}", index) for index in range(1, 6)]
    )

    rendered = render_board(tally_board(tmp_path, catalogue), catalogue)
    section = rendered.split(board.CATEGORY_HEADING)[1]
    listed = [line for line in section.splitlines() if line.startswith("  ")]

    assert len(listed) == board.TOP_PER_CATEGORY
    assert "wish-3" in section
    assert "wish-4" not in section


def test_a_pipe_in_a_title_does_not_break_the_table(tmp_path):
    catalogue = [proposal("radio-wish", title="Keep radio | map [and] calls running")]
    write_ballot(tmp_path, "alpha", [("radio-wish", 1)])

    rendered = render_board(tally_board(tmp_path, catalogue), catalogue)
    row = next(line for line in rendered.splitlines() if line.startswith("| 1 "))

    assert row.count("|") - row.count("\\|") == 6
    assert "\\|" in row
    assert "\\[and\\]" in row


def test_board_prints_the_same_markdown(tmp_path, monkeypatch):
    wishlists = tmp_path / "wishlists"
    wishlists.mkdir()
    write_ballot(wishlists, "alpha", [("mission-replay", 1)])
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()

    code = main(["--dir", str(PROPOSALS_DIR), "board"], out=out)

    proposals = load_all(PROPOSALS_DIR)
    assert code == 0
    assert out.getvalue() == render_board(
        tally_board(wishlists, proposals), proposals
    )


def test_board_write_updates_the_doc_and_the_readme_block(tmp_path, monkeypatch):
    wishlists = tmp_path / "wishlists"
    wishlists.mkdir()
    write_ballot(wishlists, "alpha", [("mission-replay", 1)])
    readme = tmp_path / board.README_FILE
    readme.write_text(
        f"# Title\n\n{board.BOARD_START}\nstale\n{board.BOARD_END}\n\nTail.\n",
        encoding="utf-8",
    )
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()

    code = main(["--dir", str(PROPOSALS_DIR), "board", "--write"], out=out)

    proposals = load_all(PROPOSALS_DIR)
    expected = render_board(tally_board(wishlists, proposals), proposals)
    text = readme.read_text(encoding="utf-8")

    assert code == 0
    assert (tmp_path / board.LEADERBOARD_FILE).read_text(encoding="utf-8") == expected
    assert board.read_block(text) == expected
    assert text.startswith("# Title\n")
    assert text.endswith("Tail.\n")


def test_board_write_without_a_block_exits_2(tmp_path, monkeypatch):
    (tmp_path / "wishlists").mkdir()
    (tmp_path / board.README_FILE).write_text("# Title\n", encoding="utf-8")
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()

    code = main(["--dir", str(PROPOSALS_DIR), "board", "--write"], out=out)

    assert code == 2
    assert "board:start" in out.getvalue()


def test_a_missing_ballots_directory_exits_2(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()

    assert main(["--dir", str(PROPOSALS_DIR), "board"], out=out) == 2


def test_the_ballots_directory_comes_from_the_environment(tmp_path, monkeypatch):
    monkeypatch.setenv("GTA7_WISHLISTS_DIR", str(WISHLISTS_DIR))
    monkeypatch.chdir(tmp_path)
    out = io.StringIO()

    code = main(["--dir", str(PROPOSALS_DIR), "board"], out=out)

    assert code == 0
    assert board.EMPTY in out.getvalue()
