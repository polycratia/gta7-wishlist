# GTA 7 Wishlist - what players want next, based on GTA 6

## What is this

An open, community-editable list of improvements players want in the next Grand
Theft Auto. Every wish has to be grounded in what GTA 6 (Grand Theft Auto VI)
actually does today, so the list stays a record of real friction instead of a
pile of fantasies.

One wish lives in one TOML file. A small Python library loads those files and
reports everything that does not meet the format. From that shared list you can
build, rank and share a wishlist of your own, and send it in as a ballot. Once
GTA 6 changes, a title update file can move a wish off the list.

## Status

What exists today:

- `gta7_wishlist.model` - the `Proposal`, `Evidence` and `Update` types, the
  category and status lists, and loaders for a single file (`load_proposal`,
  `load_update`) or a whole directory (`load_all`, `load_updates`).
- `gta7_wishlist.validate` - `validate(proposals, updates)` returns a list of
  readable problems and never raises on bad data.
- `gta7_wishlist.similar` - `similarity(a, b)` scores two wishes in 0..1 and
  `find_duplicates(proposals)` returns the pairs that look like the same wish.
- `gta7_wishlist.mine` - personal wishlists: `pick`, `drop`, `move`,
  `render_markdown`, and a reader and writer for the personal wishlist file.
- `gta7_wishlist.tally` - `tally(wishlists, proposals)` scores the community
  ballots in `wishlists/` and returns the standings, the ballots it refused and
  the picks it ignored.
- `gta7_wishlist.board` - `render_board(tally_result, proposals)` renders the
  leaderboard as Markdown, and `tally_board(wishlists, proposals)` scores only
  the ballots that count toward it.
- `gta7_wishlist.watch` - `status_report(proposals, updates)` groups every wish
  into still open, addressed and declined, and `filter_since(report, date)`
  keeps only the updates recorded since a day.
- `gta7_wishlist.cli` - the `gta7` command: `list`, `show`, `check`, `similar`,
  `categories`, `pick`, `drop`, `move`, `mine`, `board` and `status`.
- `proposals/` - the first three wishes, each grounded in documented GTA 6
  behaviour at launch.
- `wishlists/` - two example ballots.
- `updates/` - one file per official GTA 6 title update. No update is recorded
  yet; `updates/README.md` explains the format.
- `docs/leaderboard.md` - the generated leaderboard, the same text as the board
  block below.
- `tests/` - run them with `python -m pytest` from the repository root.

## Command line

Install the package (`pip install -e .`) and the `gta7` command is available.
Every command reads `./proposals` by default; pass `--dir DIR` or set
`GTA7_WISHLIST_DIR` to read another directory. `gta7 check` and `gta7 status`
also read `./updates`; pass `--updates DIR` or set `GTA7_UPDATES_DIR`.

```console
$ gta7 list
cheats-before-credits  progression  open  Allow single-player cheats from the start of the game
mission-replay         missions     open  Ship mission replay and chapter select on day one
pc-at-launch           platforms    open  Announce the PC date together with the console date

$ gta7 list --category platforms --status open
pc-at-launch  platforms  open  Announce the PC date together with the console date

$ gta7 show pc-at-launch
pc-at-launch
Announce the PC date together with the console date

category: platforms
status:   open
tags:     pc, release-date
file:     proposals/pc-at-launch.toml

Problem
  GTA 6 launched on PlayStation 5 and Xbox Series X|S on 19 November 2026.
  ...

Evidence
  https://www.pcgamer.com/no-gta-6-pc-release-announced  (checked 2026-11-22)

$ gta7 check
3 proposals checked, no problems

$ gta7 similar mission-replay
mission-replay  Ship mission replay and chapter select on day one

0.02  cheats-before-credits  Allow single-player cheats from the start of the game
0.01  pc-at-launch           Announce the PC date together with the console date

$ gta7 categories
missions       1
world          0
online         0
controls       0
performance    0
platforms      1
progression    1
accessibility  0
other          0
```

Exit codes: `0` when everything is fine, `1` when `gta7 check` found at least
one problem (one line per problem, as `path: message`), and `2` for a bad
argument, a missing directory, an unknown proposal id, a refused change to your
own list, a `--since` that is not a date, or a README without a board block. An
unknown id prints the closest ids it knows.

## Duplicates

Two people filing the same wish split the votes, so `gta7 check` compares every
pair of proposals. The score comes from two-word shingles of the normalised
title, problem and proposal text (lowercase, punctuation stripped, common
English words dropped, a crude suffix stemmer) compared with Jaccard, with the
title counted double. A pair at or above `0.45` is printed as a warning:

```console
$ gta7 check
warning: mission-replay and replay-finished-missions look like the same wish (similarity 0.54); keep one, or declare not_duplicate_of on both sides
4 proposals checked, no format problems, 1 possible duplicate pair

$ gta7 check --strict
...
$ echo $?
1
```

A warning never changes the exit code on its own; `--strict` turns duplicates
into a failure. Two wishes that read alike but are genuinely different declare
each other with `not_duplicate_of`, and that declaration has to exist on both
sides or `gta7 check` reports it as a problem.

## Your own wishlist

The shared list says what exists. Your own list says what you would fix first.
Pick proposals from the shared list, rank them, and print a card you can paste
anywhere.

```console
$ gta7 pick mission-replay --handle polycratia
picked mission-replay at rank 1 (1 of 25)

$ gta7 pick pc-at-launch --note "I only have a PC."
picked pc-at-launch at rank 2 (2 of 25)

$ gta7 move pc-at-launch 1
moved pc-at-launch to rank 1

$ gta7 mine
@polycratia  2 of 25 picks  updated 2026-11-24

 1  pc-at-launch    platforms  Announce the PC date together with the console date
      I only have a PC.
 2  mission-replay  missions   Ship mission replay and chapter select on day one

$ gta7 drop mission-replay
dropped mission-replay, 1 pick left

$ gta7 mine --markdown
# My GTA 7 wishlist

By @polycratia, updated 2026-11-24.

1. **Announce the PC date together with the console date** (platforms) - `pc-at-launch`
   I only have a PC.

1 pick: platforms 1.
```

Ranks are always `1..n` with no gaps: `drop` closes the gap it leaves and `move`
renumbers everything around the proposal you moved. A list holds at most 25
picks, so a ranking means something; the 26th is refused until you drop one.
Picking an id twice, or an id that is not in the proposals directory, is
refused too.

Your list lives in `./my-wishlist.toml` unless you pass `--file FILE` or set
`GTA7_MY_WISHLIST`. It is a file you can hand-edit:

```toml
handle = "polycratia"
updated_on = "2026-11-24"

[[picks]]
id = "pc-at-launch"
rank = 1
note = "I only have a PC."

[[picks]]
id = "mission-replay"
rank = 2
```

Only the order of the ranks is read, so you can renumber by hand with gaps or
duplicates and the next command writes them back dense.

## How voting works

Your own list is also your ballot. A ballot is a file in `wishlists/`, named
after the handle that owns it - `wishlists/<handle>.toml` - in exactly the
personal wishlist format above. One file per handle is the only identity rule
here: nothing proves a handle belongs to a player, so this is a community poll
of the people who sent a file, not a measurement of what all GTA 6 players
want. Read it that way, and do not quote it as one.

`tally(wishlists, proposals)` reads those files and scores them with a Borda
count over a fixed ballot length of 25: rank 1 is worth 25 points, rank 2 is
worth 24, rank 25 is worth 1. A short ballot is never padded, so every player
spends the same weight on their top pick. Per proposal the tally reports
`picks` (how many players chose it), `points`, `first_places` and a `rank`. The
standings are ordered by points, then picks, then first places, then id, and
proposals that tie on all three counts share a rank while the next rank skips:
`1, 2, 2, 4`.

A ballot is rejected whole, with a reason in the report instead of an
exception, when:

- the `handle` inside the file does not match the file name,
- it picks an id that is not in the proposals directory,
- it picks the same id twice,
- its ranks are not exactly `1..n` - one gap or one repeat rejects the file,
- it holds more than 25 picks, or none at all.

Picks of proposals that are `declined` are ignored and listed separately; the
rest of that ballot still counts, and declined proposals stay out of the
standings.

`wishlists/example-jason.toml` and `wishlists/example-lucia.toml` are examples,
marked as such in a `note`. To vote, open a pull request that adds one file
named after your handle.

## The leaderboard

`gta7 board` prints the leaderboard built from those ballots, and `gta7 board
--write` writes `docs/leaderboard.md` and replaces the generated block below,
the one fenced by the `board:start` and `board:end` comments. It reads
`./wishlists` unless you pass `--wishlists DIR` or set `GTA7_WISHLISTS_DIR`,
and it writes relative to the directory it runs in, so run it from the
repository root.

Ballots whose handle starts with `example-` never count toward the board, so
the two example files score only in the tests. The tests compare both committed
copies against `render_board()` byte for byte: a ballot merged without a
regenerated board fails.

<!-- board:start -->
## GTA 7 wishlist leaderboard

Built from 0 ballots in `wishlists/`.
Ballots whose handle starts with `example-` never count toward the board:
the example files are in the repository to show the format, and they count
only in the tests.

No ballots yet.

Regenerate this with `gta7 board --write` after a ballot is merged.
<!-- board:end -->

## What a GTA 6 patch already addressed

A wish is only worth ranking until the game changes. `updates/` records the
official GTA 6 title updates, one file per update at `updates/<id>.toml`, and a
wish that a patch answered points at one of them:

```toml
status = "addressed"
addressed_by = "gta6-1-02"
addressed_note = "Replay works from the pause menu; chapter select is still missing."
```

That update file is the evidence, so `gta7 check` refuses `addressed` without an
`addressed_by` naming a file in `updates/`, refuses an update that is not out
yet by its own `checked_on` dates, and refuses `addressed_by` on a wish that is
still `open`. An update needs at least one public https source under the same
date rules as a proposal. `updates/README.md` has the full format; the directory
ships empty on purpose, because an invented patch note would quietly mark wishes
as fixed.

`gta7 status` groups every wish into still open, addressed and declined. The day
count runs from the earliest evidence `checked_on`, the first day the behaviour
was written down here; for an addressed wish it stops on the day the update was
released, for the rest it runs to today.

```console
$ gta7 status
3 wishes tracked: 3 still open, 0 addressed, 0 declined

Still open
  cheats-before-credits  progression  4 days since 2026-11-22
  mission-replay         missions     4 days since 2026-11-22
  pc-at-launch           platforms    4 days since 2026-11-22

No GTA 6 title update is recorded yet.

$ gta7 status --since 2026-12-01
no GTA 6 title update recorded since 2026-12-01
```

`gta7 status --since YYYY-MM-DD` lists only the updates released on or after
that day, each with the wishes it addressed, so a patch can be read as a diff
against the list. A wish that names an update nobody recorded is kept apart as a
warning instead of counting as addressed.

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

# Optional. Ids of wishes that score as duplicates but are different wishes.
# The other file has to list this id back, or gta7 check reports it.
not_duplicate_of = ["interiors-load-faster"]

# Only with status = "addressed": the update in updates/ that fixed this,
# and what it covered.
# addressed_by = "gta6-1-02"
# addressed_note = "Interiors load without a cut since this update."

# At least one evidence item. The url must be public and https, and
# checked_on is the day you last looked at it (YYYY-MM-DD).
[[evidence]]
url = "https://www.rockstargames.com/gta-vi"
checked_on = "2026-11-20"
```

## Current proposals

- `mission-replay` (missions) - ship mission replay and chapter select on day
  one, instead of leaving players to keep manual saves before each mission.
- `cheats-before-credits` (progression) - let single-player cheats be enabled
  from the start in a clearly marked mode that disables trophies, instead of
  unlocking them after the final story mission.
- `pc-at-launch` (platforms) - announce the PC date together with the console
  date, even if the PC version ships later.

All three are `open`: nothing about them has changed since launch.

## Rules

- One wish per file. Split anything that needs the word "and" twice.
- Evidence is required. A wish must point at something public that shows how
  GTA 6 behaves today; without it the proposal is refused.
- No duplicates. Run `gta7 similar` against the closest existing wish before
  adding a file, and edit that wish instead of filing a second one.
- One ballot per player. One file per handle, named after the handle.
- A wish is `addressed` only once a file in `updates/` records the title update
  that fixed it. No update file, no addressed wish.
- No leaks and no datamined content. Public, official or clearly published
  sources only.
- No harassment of developers. Describe the behaviour, not the people.

## Disclaimer

Unofficial fan project, not affiliated with or endorsed by Rockstar Games or
Take-Two Interactive. Grand Theft Auto and GTA are their trademarks. No next
game has been announced, and nothing here is a prediction.

Maintained by polycratia (https://polycratia.com).
