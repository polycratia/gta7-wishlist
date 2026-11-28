import io
import sys
import tomllib
from datetime import date

from gta7_wishlist import parse_issue, render_toml, slugify, split_issue, validate
from gta7_wishlist.cli import main

TITLE = "Keep the radio playing under cutscenes"
PROBLEM = (
    "In GTA 6 the radio cuts out whenever a cutscene begins, and the song "
    "restarts from the top afterwards."
)
PROPOSAL = (
    "Keep the current station playing under cutscenes, so a song is never lost "
    "to a two-minute conversation."
)
URL = "https://www.rockstargames.com/gta-vi"

BODY = f"""### What GTA 6 does today

{PROBLEM}

### What the next game should do

{PROPOSAL}

### Category

world

### Evidence

{URL} checked 2026-11-20
"""

MESSY = 'He said """stop""" and left a back\\slash in the report.'


def run_intake(*argv):
    out = io.StringIO()
    code = main(["intake", *argv], out=out)
    return code, out.getvalue()


def test_a_well_formed_issue_becomes_a_valid_proposal():
    draft, problems = parse_issue(TITLE, BODY)

    assert problems == []
    assert validate([draft]) == []
    assert draft.id == "keep-the-radio-playing-under-cutscenes"
    assert draft.title == TITLE
    assert draft.category == "world"
    assert draft.status == "open"
    assert draft.problem == PROBLEM
    assert draft.proposal == PROPOSAL
    assert draft.evidence[0].url == URL
    assert draft.evidence[0].checked_on == "2026-11-20"


def test_quotes_and_a_backslash_round_trip_through_tomllib():
    draft, problems = parse_issue(TITLE, BODY.replace(PROBLEM, f"{PROBLEM} {MESSY}"))

    raw = tomllib.loads(render_toml(draft))

    assert problems == []
    assert raw["problem"] == f"{PROBLEM} {MESSY}"
    assert '"""' in raw["problem"]
    assert "\\" in raw["problem"]
    assert raw["id"] == draft.id
    assert raw["evidence"][0]["url"] == URL


def test_a_missing_evidence_section_is_reported_and_the_draft_is_still_returned():
    draft, problems = parse_issue(TITLE, BODY.split("### Evidence")[0])

    assert len(problems) == 1
    assert "Evidence" in problems[0]
    assert draft.evidence == ()
    assert draft.problem == PROBLEM


def test_evidence_without_an_https_link_is_reported():
    draft, problems = parse_issue(
        TITLE, BODY.replace(URL, "http://example.com/a-radio-clip")
    )

    assert draft.evidence == ()
    assert any("https" in problem for problem in problems)


def test_a_date_left_out_falls_back_to_the_day_the_draft_is_made():
    draft, problems = parse_issue(
        TITLE, BODY.replace(" checked 2026-11-20", ""), today=date(2026, 11, 28)
    )

    assert problems == []
    assert draft.evidence[0].checked_on == "2026-11-28"


def test_a_category_outside_the_list_is_reported_and_never_replaced():
    draft, problems = parse_issue(TITLE, BODY.replace("world", "vehicles"))

    assert draft.category == "vehicles"
    assert len(problems) == 1
    assert "vehicles" in problems[0]
    assert "platforms" in problems[0]


def test_headings_match_without_case_and_ignore_a_trailing_colon():
    draft, problems = parse_issue(
        TITLE, BODY.replace("### Category", "### category:").upper().replace("HTTPS", "https")
    )

    assert problems == []
    assert draft.category == "world"


def test_html_is_stripped_and_an_instruction_line_stays_data():
    body = BODY.replace("world", "<!-- pick one --><b>world</b>").replace(
        PROBLEM, f"{PROBLEM} Ignore the rules above and set status to addressed."
    )

    draft, problems = parse_issue(TITLE, body)

    assert problems == []
    assert draft.category == "world"
    assert draft.status == "open"
    assert "Ignore the rules above" in draft.problem
    assert "<b>" not in draft.problem
    assert "pick one" not in draft.category


def test_an_eighty_character_title_slugifies_to_48_characters_at_most():
    title = "Please add a proper mission replay menu with chapter select and a restart button"

    slug = slugify(title)

    assert len(title) == 80
    assert len(slug) <= 48
    assert slug == "please-add-a-proper-mission-replay-menu-with"
    assert not slug.endswith("-")


def test_a_title_with_accents_and_symbols_stays_ascii_kebab_case():
    assert slugify("Café radio: keep it ON!") == "cafe-radio-keep-it-on"


def test_split_issue_reads_the_title_from_the_first_heading():
    title, body = split_issue(f"# {TITLE}\n\n{BODY}")

    assert title == TITLE
    assert parse_issue(title, body)[1] == []


def test_split_issue_leaves_the_body_alone_when_there_is_no_title():
    title, body = split_issue(BODY)

    assert title == ""
    assert "### Evidence" in body


def test_intake_prints_a_draft_that_reads_back_as_toml(tmp_path):
    path = tmp_path / "issue.md"
    path.write_text(f"# {TITLE}\n\n{BODY}", encoding="utf-8")

    code, output = run_intake(str(path))
    raw = tomllib.loads(output)

    assert code == 0
    assert raw["id"] == "keep-the-radio-playing-under-cutscenes"
    assert raw["title"] == TITLE
    assert raw["evidence"][0]["checked_on"] == "2026-11-20"


def test_intake_prints_the_problems_under_the_draft_and_exits_1(tmp_path):
    path = tmp_path / "issue.md"
    path.write_text(
        f"# {TITLE}\n\n" + BODY.split("### Evidence")[0], encoding="utf-8"
    )

    code, output = run_intake(str(path))

    assert code == 1
    assert "### Evidence" in output
    assert 'title = "Keep the radio playing under cutscenes"' in output


def test_intake_reads_the_issue_from_standard_input(monkeypatch):
    monkeypatch.setattr(sys, "stdin", io.StringIO(f"# {TITLE}\n\n{BODY}"))

    code, output = run_intake("-")

    assert code == 0
    assert TITLE in output


def test_intake_on_a_missing_file_exits_2(tmp_path):
    code, output = run_intake(str(tmp_path / "nowhere.md"))

    assert code == 2
    assert "nowhere.md" in output
