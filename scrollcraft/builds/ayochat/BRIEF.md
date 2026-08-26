# BRIEF — yt-ayochat

Authored from the user's written /goal brief (their words quoted verbatim below).
Not a live interview: the user supplied the full conceptual brief up front and
the session is autonomous. Marked accordingly.

## The eight answers

1. **Vibe (3–5 words + references):** "bold, high-end tech manifesto" ·
   "premium" · "avoid generic AI slop aesthetics" · "raw, custom terminal
   aesthetic". References implied: phosphor-era CRT terminals, protest-poster
   typography.
2. **The scroll journey, in their words:**
   - "Act 1 (The Problem): The attention economy is broken. Creators get
     millions of Shorts views but zero click-throughs. The scroll is dead
     traffic."
   - "Act 2 (The Shift): Introduce yt-ayochat. Visuals shift dramatically.
     Show a silent, brutalist terminal running a Python RAG pipeline in the
     background using CSS-only motion."
   - "Act 3 (The Engineered Peak): A massive, bold visual moment. A YouTube
     comment appears ('SEND IT'), and instantly, an automated DM slides in
     with a community link. The scroll physics must sharply slow down here to
     let this monetization conversion moment land heavily."
   - "Act 4 (The Close): Call to action featuring the open-source GitHub repo
     link and the terminal command to install the agent."
3. **Energy curve:** loud declarative open, tightening tension, a quiet held
   breath, then the single loudest moment on the page at Act 3, then near
   silence at the close. Their instruction: the peak must "land heavily".
4. **Feeling, stage by stage + the one moment:** see the feeling curve below.
   The one moment: the comment-to-DM conversion.
5. **One thing no site they've seen does:** "As the user scrolls, the
   on-screen text must simulate being typed out into a command-line
   interface." (their words, the seed of the signature move)
6. **Distance from premium-minimal:** brutalist. "stark", "brutalist
   terminal", "sharp, unexpected accent colors", dark dominant ground.
7. **One unbroken world or distinct scenes:** distinct scenes. "Visuals shift
   dramatically" between acts. Grammar named by the user: "Typographic
   poster."
8. **Assets they already have:** none supplied; no photography wanted. Type is
   the imagery. Real repo content is the asset: module names
   (listener.py, gateway.py), the Chroma + Vertex AI pipeline, the real
   install commands.

## Feeling curve

| Act | Feeling | What on screen causes it |
|---|---|---|
| 1 Hero | Recognition | "THE SCROLL IS DEAD." at poster scale, assembling line by line under the hand |
| 2 The cost | Unease | a broken grid of fact fragments; the word "ZERO." wiped in huge while the qualifiers stay tiny |
| 3 The shift | Curiosity | the ground darkens, an amber phosphor terminal is already running; scroll types the run command |
| 4 Silence | Held breath | a near-empty viewport, one small mono line: "then, under your latest Short:" (AUTHORED SILENCE, not dead scroll) |
| 5 Peak | Impact | the visitor's own scrolling types "SEND IT" at ~18vw, and the DM transcript wipes in the instant it completes |
| 6 Close | Resolve | the page inverts to its smallest type; the real install commands and a plain underlined GitHub link, holding |

## The peak

Act 5. The sentence a visitor would say to a friend:

> "my scrolling literally typed SEND IT into the page, and the DM snapped back
> before I could blink"

It gets: the largest span on the page (3.4vh vs ≤2.4 everywhere else), a dwell
of 0.5 so the scroll physics visibly slow and settle on the moment (the user's
explicit ask), and an authored silence act directly before it.

## The completed tell-someone sentence

It's the site where your own scrolling types "SEND IT" into a giant comment
and the automated DM fires back on screen the moment the last letter lands.

## Authored silence

Act 4 (the small mono line before the peak) is deliberate near-emptiness: one
line, huge negative space. It is a flow act, excluded from dead-scroll checks
by design; noted here so the verification pass reads it as intent.

## Structure decisions

- **Grammar: typographic poster** (user-named). No photographic ground, no
  scrub, no scrims, no cards, no decorative motion. Type scale does the work.
- **Signature move:** scroll-as-keystrokes. Page-local JS reads each act's
  `--sc-p` and reveals text character by character behind a block caret, so
  the wheel is a keyboard. It carries the peak: SEND IT is typed by the
  visitor's own scroll. The terminal's ambient pipeline log is CSS-only
  motion (steps() keyframes), per the brief.
- **Honesty:** the terminal is real markup running real page logic on the
  repo's actual module names, labeled "simulated session · demo data". No
  invented statistics anywhere; the only numbers on the page are the real
  install commands.
- **Palette:** warm near-black canvas (#0B0A08), bone ink, one accent: amber
  phosphor (#FFB000), the color of a real terminal's ink. In the brief's
  "electric orange" family while refusing the default acid-green-on-black.
- **Type:** Bricolage Grotesque (display, characterful brutalist grotesque),
  Newsreader (refined serif body, the manifesto voice), IBM Plex Mono only
  for genuine terminal/CLI content.
