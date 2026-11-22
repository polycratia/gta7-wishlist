from gta7_wishlist import load_all, load_proposal, validate

DEFAULT_ID = "interiors-stay-loaded"
DEFAULT_TITLE = "Let shop interiors stay open without a loading screen"
DEFAULT_PROBLEM = (
    "Shop interiors in GTA 6 open with a short loading screen that breaks a chase."
)
DEFAULT_PROPOSAL = (
    "Stream interiors with the rest of the world so a door can be entered without a cut."
)
DEFAULT_EVIDENCE = (("https://www.rockstargames.com/gta-vi", "2026-11-20"),)


def proposal_toml(
    proposal_id=DEFAULT_ID,
    title=DEFAULT_TITLE,
    category="world",
    status="open",
    problem=DEFAULT_PROBLEM,
    proposal=DEFAULT_PROPOSAL,
    tags=("interiors",),
    evidence=DEFAULT_EVIDENCE,
):
    lines = [
        f'id = "{proposal_id}"',
        f'title = "{title}"',
        f'category = "{category}"',
        f'status = "{status}"',
        f'problem = "{problem}"',
        f'proposal = "{proposal}"',
        "tags = [" + ", ".join(f'"{tag}"' for tag in tags) + "]",
    ]
    for url, checked_on in evidence:
        lines += ["", "[[evidence]]", f'url = "{url}"', f'checked_on = "{checked_on}"']
    return "\n".join(lines) + "\n"


def write_proposal(directory, filename, **overrides):
    path = directory / filename
    path.write_text(proposal_toml(**overrides), encoding="utf-8")
    return path


def test_well_formed_proposal_has_no_problems(tmp_path):
    path = write_proposal(tmp_path, f"{DEFAULT_ID}.toml")

    assert validate([load_proposal(path)]) == []


def test_proposal_without_evidence_is_refused(tmp_path):
    path = write_proposal(tmp_path, f"{DEFAULT_ID}.toml", evidence=())

    problems = validate([load_proposal(path)])

    assert len(problems) == 1
    assert "evidence" in problems[0]
    assert str(path) in problems[0]


def test_http_url_is_refused(tmp_path):
    path = write_proposal(
        tmp_path,
        f"{DEFAULT_ID}.toml",
        evidence=(("http://example.com/gta6-interior-clip", "2026-11-20"),),
    )

    problems = validate([load_proposal(path)])

    assert len(problems) == 1
    assert "https://" in problems[0]


def test_impossible_date_is_refused(tmp_path):
    path = write_proposal(
        tmp_path,
        f"{DEFAULT_ID}.toml",
        evidence=(("https://www.rockstargames.com/gta-vi", "2026-02-30"),),
    )

    problems = validate([load_proposal(path)])

    assert len(problems) == 1
    assert "checked_on" in problems[0]
    assert "2026-02-30" in problems[0]


def test_id_must_match_file_name(tmp_path):
    path = write_proposal(tmp_path, f"{DEFAULT_ID}.toml", proposal_id="something-else")

    problems = validate(load_all(tmp_path))

    assert len(problems) == 1
    assert str(path) in problems[0]
    assert DEFAULT_ID in problems[0]


def test_duplicate_ids_are_reported_once_with_both_paths(tmp_path):
    first = write_proposal(tmp_path, f"{DEFAULT_ID}.toml")
    second = write_proposal(tmp_path, f"{DEFAULT_ID}-copy.toml", proposal_id=DEFAULT_ID)

    problems = validate(load_all(tmp_path))
    duplicates = [problem for problem in problems if "duplicate id" in problem]

    assert len(duplicates) == 1
    assert str(first) in duplicates[0]
    assert str(second) in duplicates[0]
