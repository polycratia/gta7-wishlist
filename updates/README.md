# GTA 6 title updates

One file per official GTA 6 title update, at `updates/<id>.toml`. These files
are the only thing that can move a wish from `open` to `addressed`, so nothing
is written here until the update is out and there is a public source for it.

**No update is recorded yet.** The directory ships empty on purpose: an
invented patch note would quietly mark wishes as fixed.

## Format

```toml
# updates/gta6-1-02.toml

# Kebab-case, and it must match the file name without the .toml suffix.
id = "gta6-1-02"

# The version as Rockstar Games writes it.
version = "1.02"

# The day the update went out (YYYY-MM-DD).
released_on = "2026-12-10"

# At least 20 characters: what the update changed, in your own words.
summary = "Adds mission replay to the pause menu for finished story missions."

# At least one evidence item. The url must be public and https, and
# checked_on is the day you last looked at it. released_on cannot be later
# than the last checked_on: an update is recorded once it is out.
[[evidence]]
url = "https://www.rockstargames.com/newswire/article/gta-vi-title-update"
checked_on = "2026-12-11"
```

## Pointing a wish at an update

A proposal that a patch answered names the update and says what it covered:

```toml
status = "addressed"
addressed_by = "gta6-1-02"
addressed_note = "Replay works from the pause menu; chapter select is still missing."
```

`gta7 check` refuses `status = "addressed"` without an `addressed_by` that
names a file in this directory, and refuses `addressed_by` on a wish that is
still `open`. `gta7 status` groups every wish into still open, addressed and
declined; `gta7 status --since YYYY-MM-DD` lists only the updates recorded
since that day.

Only official sources count here: a Rockstar Games newswire post or the patch
notes on a platform store page. No leaks and no datamined content.
