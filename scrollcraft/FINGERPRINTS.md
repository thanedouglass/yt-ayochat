# Fingerprints

Every site you build with **scrollcraft** gets one row here, appended after it
ships. The registry exists so your next build can prove it is a different page
rather than a re-skin of one you already made.

This file is **yours**. It starts empty on purpose: the gate is about not
repeating *yourself*, so it has nothing to say until you have built something.

The rules and the gate live in the skill's
`references/uniqueness.md`. Short version:

**A new build must differ from EVERY row below on at least 4 of the 6
dimensions.** Four against each row individually, not four on average across the
table. If a planned build fails, change the plan. Never edit a row to make room
for it.

The six dimensions are: **grammar**, **nav treatment**, **hero device**,
**act-sequence shape**, **close pattern**, **signature move**.

Dimension 6 is free, because a signature move is unique by definition. So the
gate really asks for three more out of the remaining five, and a build that
changes only grammar and world will fail it.

---

## The registry

| Build | Grammar | Nav treatment | Hero device | Act-sequence shape | Close pattern | Signature move | World | Port |
|---|---|---|---|---|---|---|---|---|
| ayochat | Typographic poster | None. Wordmark set into the hero composition; no persistent bar | Pinned kinetic headline at ~12.5vw, greet cue, scale eased from `--sc-p` | pin·kinetic → flow·reveal → pin·typed-terminal → flow·silence → pin·typed-peak+reveal → flow·close; 6 acts, ~11.4vh | Page inverts to its smallest type; CTA is a plain underlined mono link; static flow section holds | Scroll-as-keystrokes: act progress types on-page text char by char behind a block caret; the peak comment "SEND IT" is typed by the visitor's own scroll | No media. Type on warm near-black, amber phosphor accent, one CSS-animated terminal surface | 4500 |

---

## What is taken

Add a bullet here whenever a build claims something a later build should avoid
reusing: a grammar, a nav treatment, a close pattern, a signature move, an
act-count-and-length band. The shared columns are what the next build inherits
as a constraint, so writing them down is the whole point.

- **Taken by `ayochat`:** the typographic-poster grammar; the no-nav wordmark-in-composition treatment; the giant-typed-word peak; the scroll-as-keystrokes signature; the quiet inverted close with an underlined mono link; the 6-acts-at-~11.4vh band; amber-phosphor-on-near-black as a palette.

---

## Appending a row

After shipping, add one line to the table and one bullet to **What is taken** if
the build claimed something new. Fill every column. Say what the build shares
with existing rows.

Rows are append-only. A build that has been superseded stays in the table,
because the space it occupies is still occupied.

---

## Worked example

The skill's author kept a registry of twelve builds across eight page grammars.
If you want to see what a filled-in table looks like, and which shapes tend to
collide, read `EXAMPLES.md` in the scrollcraft repository. Treat it as
illustration only: those rows are somebody else's builds and they do **not**
constrain yours.
