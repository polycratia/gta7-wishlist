from pathlib import Path

from gta7_wishlist import load_all, validate

PROPOSALS_DIR = Path(__file__).resolve().parent.parent / "proposals"

SHIPPED_IDS = ("mission-replay", "cheats-before-credits", "pc-at-launch")


def test_shipped_proposals_are_well_formed():
    assert validate(load_all(PROPOSALS_DIR)) == []


def test_shipped_ids_are_present():
    ids = {proposal.id for proposal in load_all(PROPOSALS_DIR)}

    assert set(SHIPPED_IDS) <= ids
