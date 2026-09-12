# Endgame proof audit and three-move candidate (2026-09-12)

Initial review base: `39cb7b2689befe57fd953d983f66f12f8a06b096`.
Integrated onto `d6412d6adf45fcf72cb5d2ee3af6446e2085e882`, preserving the
intervening round-237 two-move promotion, its golden files and regression pins.
The publication and candidate-cohort workflow fixes remain intact.

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

The additional third-own-move extension remains behind `candidateSlots`.
It is admitted only at real decisions, not at inScorerSim, trueConfirmDepth or
simDepth reentries: a hypothetical board does not establish that the live clock
has been projected consistently. The intervening round-237 promotion is kept:
unselected cars, and all nested decisions, retain the promoted two-move tactic.
The new overload does not demote those cars back to the one-move predecessor.
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

## Completed initial campaign and integration boundary

Validation run 34684034180 completed on prepared source commit
`9d23057d37de220d2301ff26dcda898eef858a53`, tree
`f8bf1099f22262833c0368aeed967784605954a9`. Both JDK 25/26 proof jobs and all six
fleet jobs passed. The JDK 25 job also ran Python, production comparison,
headless/replay/profile, all frozen goldens and all champion regression scripts.
Each fleet contains 84 tracks x 10 seeds x two mirrors: 1,680 races. Across six
field/start combinations that is 10,080 races and 50,400 car-races.

These are candidate-minus-champion mean places and standard errors as reported
by the validated scorer (negative is better):

| Cars | Start | Place difference | Standard error | Wins C:H | Crashes C:H |
| --- | --- | ---: | ---: | ---: | ---: |
| 2 | legacy | -0.049 | 0.007 | 881:799 | 16:132 |
| 2 | informed | -0.049 | 0.007 | 881:799 | 28:140 |
| 2 | scatter | -0.005 | 0.002 | 844:836 | 0:14 |
| 8 | legacy | -0.001 | 0.000 | 840:840 | 61:61 |
| 8 | informed | +0.000 | 0.000 | 840:840 | 57:57 |
| 8 | scatter | -0.000 | 0.000 | 840:840 | 5:5 |

Three-decimal zero standard errors above are rounded, not claims of exact zero.
The original reports and ZIP checksums are retained in
`docs/experiments/three-move-endgame/` and the workflow retains raw race logs.
Crashes describe outcomes; they are not an additional acceptance gate.

IMPORTANT: this initial campaign compares the new two/three-move candidate
against the earlier one-move tactical cohort, with the physical deep-search
fixes shared by both sides. It does NOT isolate the third move against the
newly promoted round-237 two-move champion. Subtracting independently measured
campaign deltas would not establish that gain. The integration therefore keeps
the third move opt-in rather than promoting it from these numbers.

Integration tests additionally require all original two-move setup decisions to
remain available with candidateSlots unset, every shorter certificate to retain
its selected move, and every three-move-only witness to be reachable from the
selected production tactic but absent from unselected and nested decisions.
The 24 champion pins and 12 golden files from current master are not edited.
New integration CI outcomes accompany the final commit; the earlier run's
results must not be presented as a test of the combined source tree.
