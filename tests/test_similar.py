import io
from pathlib import Path

from gta7_wishlist import (
    Evidence,
    Proposal,
    find_duplicates,
    load_all,
    similarity,
    validate,
)
from gta7_wishlist.cli import main
from gta7_wishlist.similar import DEFAULT_THRESHOLD

PROPOSALS_DIR = Path(__file__).resolve().parent.parent / "proposals"
EVIDENCE_URL = "https://www.rockstargames.com/gta-vi"

FIRST_ID = "replay-finished-missions"
FIRST_TITLE = "Let players replay finished story missions"
FIRST_PROBLEM = (
    "GTA 6 ships without a mission replay option, so a player who wants to "
    "repeat a finished story mission has to keep a manual save."
)
FIRST_PROPOSAL = (
    "Add a mission replay menu, so any finished story mission can be restarted "
    "without touching the main save file."
)

SECOND_ID = "mission-replay-menu"
SECOND_TITLE = "Players should be able to replay finished story missions"
SECOND_PROBLEM = (
    "GTA 6 ships without any mission replay option, and the player that wants "
    "to repeat a finished story mission has to keep manual saves before every "
    "mission."
)
SECOND_PROPOSAL = (
    "Add the mission replay menu so each finished story mission can be "
    "restarted from the menu without touching the main save file."
)


def make(proposal_id, title, problem, proposal, not_duplicate_of=()):
    return Proposal(
        id=proposal_id,
        title=title,
        category="missions",
        problem=problem,
        proposal=proposal,
        status="open",
        evidence=(Evidence(url=EVIDENCE_URL, checked_on="2026-11-22"),),
        not_duplicate_of=tuple(not_duplicate_of),
    )


def first(not_duplicate_of=()):
    return make(
        FIRST_ID, FIRST_TITLE, FIRST_PROBLEM, FIRST_PROPOSAL, not_duplicate_of
    )


def second(not_duplicate_of=()):
    return make(
        SECOND_ID, SECOND_TITLE, SECOND_PROBLEM, SECOND_PROPOSAL, not_duplicate_of
    )


def write(directory, proposal):
    lines = [
        f'id = "{proposal.id}"',
        f'title = "{proposal.title}"',
        f'category = "{proposal.category}"',
        f'status = "{proposal.status}"',
        f'problem = "{proposal.problem}"',
        f'proposal = "{proposal.proposal}"',
    ]
    if proposal.not_duplicate_of:
        listed = ", ".join(f'"{other}"' for other in proposal.not_duplicate_of)
        lines.append(f"not_duplicate_of = [{listed}]")
    lines += ["", "[[evidence]]", f'url = "{EVIDENCE_URL}"', 'checked_on = "2026-11-22"']

    path = directory / f"{proposal.id}.toml"
    path.write_text("\n".join(lines) + "\n", encoding="utf-8")
    return path


def run(*argv, directory):
    out = io.StringIO()
    code = main(["--dir", str(directory), *argv], out=out)
    return code, out.getvalue()


def test_two_wordings_of_the_same_wish_pair_above_the_threshold():
    assert similarity(first(), second()) > DEFAULT_THRESHOLD

    pairs = find_duplicates([first(), second()])

    assert len(pairs) == 1
    assert {pairs[0][0].id, pairs[0][1].id} == {FIRST_ID, SECOND_ID}


def test_each_pair_is_reported_once_and_never_against_itself():
    assert find_duplicates([first()]) == []
    assert len(find_duplicates([second(), first()])) == 1


def test_mission_replay_and_pc_release_stay_far_below_the_threshold():
    shipped = {proposal.id: proposal for proposal in load_all(PROPOSALS_DIR)}

    score = similarity(shipped["mission-replay"], shipped["pc-at-launch"])

    assert score < 0.1
    assert find_duplicates(load_all(PROPOSALS_DIR)) == []


def test_symmetric_declaration_silences_the_pair():
    proposals = [first([SECOND_ID]), second([FIRST_ID])]

    assert validate(proposals) == []
    assert find_duplicates(proposals) == []


def test_one_sided_declaration_is_reported():
    problems = [
        problem
        for problem in validate([first([SECOND_ID]), second()])
        if "not_duplicate_of" in problem
    ]

    assert len(problems) == 1
    assert SECOND_ID in problems[0]
    assert FIRST_ID in problems[0]


def test_declaring_itself_is_reported():
    problems = validate([first([FIRST_ID])])

    assert len(problems) == 1
    assert "itself" in problems[0]


def test_empty_proposal_text_does_not_divide_by_zero():
    blank = make("blank-wish", "", "", "")

    assert similarity(blank, blank) == 0.0
    assert similarity(first(), blank) == 0.0
    assert find_duplicates([first(), blank]) == []


def test_check_warns_about_duplicates_but_exits_zero(tmp_path):
    write(tmp_path, first())
    write(tmp_path, second())

    code, output = run("check", directory=tmp_path)

    assert code == 0
    assert output.startswith("warning: ")
    assert "1 possible duplicate pair" in output


def test_strict_check_exits_one_on_duplicates(tmp_path):
    write(tmp_path, first())
    write(tmp_path, second())

    code, _ = run("check", "--strict", directory=tmp_path)

    assert code == 1


def test_similar_ranks_the_closest_proposal_first(tmp_path):
    write(tmp_path, first())
    write(tmp_path, second())

    code, output = run("similar", FIRST_ID, directory=tmp_path)
    lines = output.splitlines()

    assert code == 0
    assert lines[0].startswith(FIRST_ID)
    assert SECOND_ID in lines[2]
    assert "possible duplicate" in lines[2]


def test_similar_marks_a_declared_pair(tmp_path):
    write(tmp_path, first([SECOND_ID]))
    write(tmp_path, second([FIRST_ID]))

    code, output = run("similar", FIRST_ID, directory=tmp_path)

    assert code == 0
    assert "declared not a duplicate" in output


def test_similar_with_an_unknown_id_exits_2(tmp_path):
    write(tmp_path, first())

    code, output = run("similar", "replay-finished-mission", directory=tmp_path)

    assert code == 2
    assert FIRST_ID in output
