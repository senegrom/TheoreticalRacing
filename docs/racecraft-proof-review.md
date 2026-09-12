# Endgame proof audit and three-move candidate (2026-09-12)

Base: `39cb7b2689befe57fd953d983f66f12f8a06b096`. The publication and promotion
workflow fixes remain intact. The latest master CI, including Chromium/WebKit
and live Pages gameplay, completed successfully before this work.

## Review findings: the older deep proof did not cover the physical game

The older `RaceAi.egRival` dropped replies whose speed exceeded the AI planning
cap. A detached straight-course fixture exposes a false certificate: our car is
at (61,7) with velocity (11,0), the human rival at (60,13) with (12,0), and the
finish is x=72.5. The old rival node returns true although acceleration (1,0)
legally reaches (73,13) and finishes first. Our own search cap is not a referee
constraint on opponents. The rival node now enumerates all physical replies.

Expanding that domain also requires full state keys, not five-bit velocity
packing: speeds 22 and -10 would otherwise alias. The memo now uses a record
with exact coordinates, velocities, remaining depth and side to move.

The old search also omitted the projected turn limit. A move cannot be promised
when the next own turn times out, and a rival timeout precedes its otherwise
finishing move. The root and recursive nodes now enforce the referee's mover-
first timeout with long arithmetic. Depth fixes the projected clock inside a
single search, whose memo is fresh for each root. No referee rules are changed.

`EndgamePhysicalTests` covers the concrete speed-13 refutation, ordinary next-
move wins, both timeout parities, the int-clock boundary and full-state memo
identity. These are correctness changes to the existing deep endgame search.

## Racecraft candidate: one more certified move, not a caution surcharge

The candidate first retains every existing two-move certificate. Only when that
search abstains does it try a third own move, allowing a longer finish/blockade
setup. Every legal physical reply must still have a winning answer. State is
fully detached; checkpoint/lap progress and timeout precedence use the existing
referee transition. A deterministic 20,000-node per-search budget fails closed:
exhaustion is unknown, not a win. The ordinary scorer handles unproved positions.

The extension remains behind `candidateSlots`. Experimental certificates are
admitted only at real decisions, not at inScorerSim, trueConfirmDepth or simDepth
reentries: a hypothetical board does not establish that the live clock has been
projected consistently. Champion immediate tactics retain their existing path.
There is no yielding, team objective or crash-count veto.

The independent detached-player verifier retains the original 12,000-trial
(two-move) check and adds 2,500 trials for the deeper search. The local check
found 1,067 admissible boards, 356 certificates and 15 certificates absent from
the two-move search, with no refutation. Every earlier certificate retains its
selected move. These finite checks establish additional tested tactical reach,
not a claim of universal correctness or measured campaign improvement.

## Evaluation and publication boundaries

Mirrored place comparisons use the actual production `promotion_pair.py`,
explicit `-Xmx8g`, both cohorts in the same races and all three start modes.
Original and new candidate screens are retained separately. Full-course grids,
strict supported-JDK tests, goldens and champion pins belong to the validation
workflow's evidence. Do not describe an unfinished run as a completed campaign.
The third-move candidate is not automatically promoted by successful tests.

No tracks, user.properties, persisted map formats or golden expectations were
changed. The previous campaign's measured policy is otherwise preserved.
