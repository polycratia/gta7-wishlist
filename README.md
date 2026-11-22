# GTA 7 Wishlist - what players want next, based on GTA 6

## What is this

An open, community-editable list of improvements players want in the next Grand
Theft Auto. Every wish has to be grounded in what GTA 6 (Grand Theft Auto VI)
actually does today, so the list stays a record of real friction instead of a
pile of fantasies.

One wish lives in one TOML file. A small Python library loads those files and
reports everything that does not meet the format.

## Status

What exists today:

- `gta7_wishlist.model` - the `Proposal` and `Evidence` types, the category and
  status lists, and loaders for a single file (`load_proposal`) or a whole
  directory (`load_all`).
- `gta7_wishlist.validate` - `validate(proposals)` returns a list of readable
  problems and never raises on bad data.
- `tests/` - run them with `python -m pytest` from the repository root.

There is no command line interface and no `proposals/` directory yet. Voting,
ranking and patch tracking are not built.

## Proposal format

A proposal is a single file at `proposals/<id>.toml`:

```toml
# proposals/interiors-stay-loaded.toml

# Kebab-case, and it must match the file name without the .toml suffix.
id = "interiors-stay-loaded"

# 8 to 90 characters. Write the wish, not a review score.
title = "Let shop interiors stay open without a loading screen"

# One of: missions, world, online, controls, performance,
# platforms, progression, accessibility, other.
category = "world"

# At least 40 characters: what GTA 6 does today and why it gets in the way.
problem = "Shop interiors in GTA 6 open with a short loading screen that breaks the flow of a chase."

# At least 40 characters: what the next game could do instead.
proposal = "Stream interiors with the rest of the world so a door can be entered without a cut."

# open while nothing has changed, addressed once a patch fixes it,
# declined once the idea is dropped.
status = "open"

# Optional free-form labels.
tags = ["interiors", "streaming"]

# At least one evidence item. The url must be public and https, and
# checked_on is the day you last looked at it (YYYY-MM-DD).
[[evidence]]
url = "https://www.rockstargames.com/gta-vi"
checked_on = "2026-11-20"
```

## Rules

- One wish per file. Split anything that needs the word "and" twice.
- Evidence is required. A wish must point at something public that shows how
  GTA 6 behaves today; without it the proposal is refused.
- No leaks and no datamined content. Public, official or clearly published
  sources only.
- No harassment of developers. Describe the behaviour, not the people.

## Disclaimer

Unofficial fan project, not affiliated with or endorsed by Rockstar Games or
Take-Two Interactive. Grand Theft Auto and GTA are their trademarks. No next
game has been announced, and nothing here is a prediction.

Maintained by polycratia (https://polycratia.com).
