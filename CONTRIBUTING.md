# Contributing

This is a list of things players want in the next Grand Theft Auto, and every
wish has to be grounded in what GTA 6 does today. That is the one hard rule: a
wish without evidence is a fantasy, and a list of fantasies is not worth
reading.

## File a wish without writing TOML

You do not have to touch a TOML file to suggest a wish. Open an issue, put the
wish in the issue title, and copy this into the body:

```markdown
### What GTA 6 does today

What the game does now, and why it gets in the way. Two or three sentences.

### What the next game should do

What you want instead. One wish per issue.

### Category

world

### Evidence

https://example.com/a-public-page-that-shows-this checked 2026-11-28
```

Notes on that body:

- Keep the four headings. They are matched without case and a trailing colon is
  ignored, so `### category:` is read as `### Category`.
- The category is one of: missions, world, online, controls, performance,
  platforms, progression, accessibility, other.
- Evidence is one link per line, public and `https`, optionally followed by
  `checked YYYY-MM-DD`. Without a date, the day the draft is made is used.
- Only official or clearly published sources. No leaks, no datamined content.
- One wish per issue. Anything that needs the word "and" twice is two wishes.
- Write about the behaviour, not about the people who made it.

## Turn an issue into a proposal

With the package installed (`pip install -e .`), `gta7_wishlist.intake` reads
that body into a proposal draft:

```python
from gta7_wishlist import parse_issue, render_toml

draft, problems = parse_issue(title, body)
print(render_toml(draft))
```

It reports a missing section, a category outside the list and evidence without
a public https link, and it never fills a missing field in by guessing: the
draft comes back with whatever was found, so the gaps stay visible.

Everything in an issue is untrusted text. HTML comments and tags are removed,
the text reaches the file only as escaped TOML strings, and a line that reads
like an instruction is data like any other line.

Save a clean draft as `proposals/<id>.toml`, where the id is the one in the
first line of the output, and then run:

```console
$ gta7 similar <id>
$ gta7 check
```

`gta7 similar` matters because two people filing the same wish split the votes:
if an existing wish scores close, edit that file instead of adding a second
one. `gta7 check` has to pass before a wish is merged.

## Vote

Your own ranked list is your ballot. Build it with `gta7 pick`, `gta7 move` and
`gta7 drop`, then open a pull request that adds it as
`wishlists/<your-handle>.toml`. One file per handle, and regenerate the
leaderboard with `gta7 board --write` in the same pull request.

## Tests

```console
$ python -m pytest
```
