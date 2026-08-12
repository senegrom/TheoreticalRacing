# racing-memory.md — full working state for continuing the AI campaign

Written 2026-07-21 at the end of the round-40 session (session id
749c6115-9b8c-4154-9f26-d8f380240d27). A fresh agent should be able to
continue from this file alone. Long-form history: see
`C:\Users\carlg\.claude\projects\E--OneDrive-Coding-Java-theoreticRacing\memory\project_ai_architecture.md`
(auto-memory, ~2000 lines, every round's laws and rejections).

## What this project is

theoreticRacing: Java Swing vector-racing game (grid, state = pos+vel, 9
accelerations/turn, |v| <= 12, up to 8 players, fully deterministic;
`--seed N` seeds start placement only). Modules: `tr.logic` split into
RaceGame (controller) / RaceAi / Reachability / TrackGeometry / TrackIO.
The AI rests on a precomputed reverse-BFS map `turnsToFinish(x,y,vx,vy)` =
EXACT min turns to finish on the empty track.

**Roles: `optimalMoveAI1` = experimental frontier, `optimalMoveAI2` =
frozen standard (champion). They are byte-identical twins at rest; work
happens on AI1; promotion = mirroring into AI2 after the full gate.**

Standing user rules:
- Never declare improvement impossible ("every time you say we can't
  improve you improve").
- NORMAL git now: incremental commits with real messages + plain `git push`
  (the old rolling-squash + force-push workflow is RETIRED).
- Commit + push as one unit. Aggression toward opponents is a FEATURE.

## Multi-agent coordination (2026-08-08)

Two agents now work this repo (one local with full bench hardware, one
GitHub-API-only that ships patches via one-off Actions workflows). Rules
of the road, learned from a mid-merge collision:
- racing-memory.md is the single shared ledger: every experiment, fix
  and gate result lands here BEFORE or WITH its push. Both agents
  already honor this -- it is what made the 37-commit merge reviewable.
- Prefer branches + PRs for multi-commit work; if pushing to master,
  keep each push self-contained and green (CI + golden corpus).
- The golden corpus pins AI2: regenerating fixtures IS a promotion
  action and must ship with the promotion commit.
- Champion caches (BENCH_BASELINE) and canonical numbers live on the
  LOCAL agent's side and are invalidated by ANY both-bodies behavioral
  change (e.g. the futureMobility4 fix) -- re-baseline before judging
  candidates against stale numbers.
- LESSON: the session scratchpad is volatile (a purge deleted the whole
  oracle toolchain, all 22 reach dumps and the archived champion logs
  between sessions). Durable tooling and reference races belong in the
  repo -- the toolchain now lives in tracks/, documented in
  AI_DEVELOPMENT.md.

## Round 79 (AI1 frontier): aligned-convoy field neutrality

FORENSICS: the fully integrated Round 78 battery was crash-free and about one
move per finisher faster on the regular 22-track stages, but the slow gate was
one net move slower. Exact per-seed diagnosis isolated all of the delta to Cog:
seed 1 was +2 moves, seed 2 was -1, and every other slow race tied. At Cog seed
1 global move 89, player 1 changed champion `E` to private-lane `S`; the
faithful rollout improved the mover's TTF 35 -> 34, but the real race gained one
move for that car and cost the other finishers three. This was a field
externality, not a survival or empty-map error.

WHY ROUND 78 MISSED IT: its comparative field gate required every live rival
within Chebyshev radius 10. The Cog train was narrow but longitudinally spread:
all seven rivals lay along the mover's velocity corridor out to 18 cells. A
larger isotropic radius would expose unrelated two-sided packs to the expensive
and model-sensitive comparison.

FIX: retain the radius-10 compact-pack arm, and add a kinematic aligned-convoy
arm. With at least five live rivals and landing speed^2 >= 49, every rival must
be within `max(10, 2 * max(|vx|, |vy|))`, no more than four cells from the
mover's velocity ray (`cross^2 <= 16 * speed^2`), and at most one rival may be
ahead (`dot > 0`). Only then run the existing five-round, six-rival comparative
scorer world. The candidate still needs strict self improvement and
non-worsening aggregate rival cost. The trigger is geometry/kinematics based;
there is no Cog or slow-track special case.

TARGET VERDICT: Cog seed 1 becomes move-identical to AI2 with finish list
`[46, 46, 46, 47, 48, 48, 48]`; Cog seed 2 keeps its one-move AI1 gain. The
full slow stage is 140/0 in both columns and one net AI1 move faster (both print
104.16). Existing Monaco pace, mixed Le Mans safety and Zigzag field-neutral
regressions remain green. An eight-track seeds-1-2 stress slice stays 112/0 in
both columns at 98.29 vs 100.93 moves per finisher (-2.64). Cog seed 1 is added
to the deterministic field-neutral regression.

FULL GATE VERDICT: the exact Round 79 source completes all three 22-track
8-car bands at 770/0 versus 770/0, with mean moves 62.73/63.69, 62.69/63.66
and 62.70/63.64; no track is slower in any band. Mixed 4v4 places are
4.472/4.528, 4.473/4.527 and 4.477/4.523, all at 0/0 crashes. The 2v2 and 1v1
stages are 2.461/2.539 and 1.486/1.514, also 0/0. Slow remains 140/0 at
104.16/104.16 with a one-move AI1 advantage before rounding. The candidate
therefore clears the no-slower-track and safety standards as an AI1 frontier;
AI2 promotion remains a separate mirror-and-self-tie action.

## Round 78 (AI1 frontier): field-neutral adversarial private lanes

INTEGRATION: refreshed from `origin/master` at `fd88906`, after the local
Round 76 L2 arm was rejected and reverted under the no-slower-track rule.
Round 75's promoted finish sprint is therefore the frozen AI2 comparison. The
private-lane work was rebased around that source; AI2 and all golden fixtures
remain untouched.

PACE PROOF: a strictly faster candidate must preserve the scorer's non-spread
quality, avoid worst-case sealing, remain on an empty-track-optimal route and
keep a private continuation against an adversarial rival occupancy envelope.
The first stage uses three-ply acceleration rectangles and three exits. A
bounded geometry-aware fallback explores every legal rival acceleration only
for queried cells through four plies, ignores collisions conservatively,
removes finishers and fails closed after 512 expanded states. It may use two
exits only at low speed or in a homogeneous AI1 field with uncertainty <=15.
The selected candidate then needs an independent faithful scorer-rival
survival certificate; the promoted seal and DJS guards still run afterwards.

FIELD EXTERNALITY: the first composition was 770/0 and materially faster on
the regular gate, but Zigzag seed 1 became four field moves slower. At global
move 71, player 7 accelerated `NE` instead of champion `NW`; the faithful
rollout improved its own final TTF from 54 to 52, but another rival failed and
the field cost changed from 368 to 1,000,318. The mover's real finish time did
not improve while two other finishers lost two moves each.

FIX: only for high-speed candidates with every live rival in a field of at
least six cars compressed within Chebyshev radius 10, compare candidate and
incumbent in the same five-round, six-rival scorer world. Field cost is the sum
of surviving rivals' final empty-map TTF, zero for finishers, and 1,000,000 per
simulated failure. Require strict self improvement and non-worsening field
cost. The target keeps `NW`; AI1 and AI2 are move-identical on Zigzag seeds
1-5. Deterministic regressions pin Monaco seed-1 pace, heterogeneous Le Mans
seed-2 safety and the Zigzag seed-1 field boundary.

PREVIOUS REGULAR GATE: all three 22-track bands were 770/0 with no track
slower, for **2,310 finishers / 0 crashes** across 330 races. Seeds 1-5 were
**62.73 vs 63.69**, seeds 6-10 **62.69 vs 63.66**, and seeds 11-15 **62.70 vs
63.64**. The integrated current-master branch must re-run the official JDK-25
battery before promotion; mixed and small-field stages remain mandatory.

## Round 78 — scorer smoke test + scorer-me certification (PROMOTED 2026-08-12, per user)

Promotion executed: smoke test + escalation mirrored into AI2 (shared
scorerSelf machinery), strict probe ALL IDENTICAL 0/27, golden corpus
regenerated with the new `zandvoort-s45-8p` fixture pinning the rescue
(1177 turns, 7/0) and two intentional slow-class reflows (lemans-s4
crash-free, monaco-s9-4p crash-free and 3 turns FASTER); every other
hash unchanged. Docs record the eighth bounded safety proof.
Post-promotion self-tie battery in flight; certification appended on
completion. AI1 and AI2 are identical again.

## Round 78 (local agent, gates PASSED): scorer smoke test + scorer-me certification

THE ZANDVOORT-S45 FORENSICS found a TWO-LAYER gap at m920 (p8, spd^2=40
braking while p7 chases at spd^2=53 down the same straight):
1. TRIGGER: the r60 smoke test's smom-5 read the doomed chosen ALIVE
   tier-3 while orivals kills it @r2 -- the THIRD member of the
   nurburgring-m260 / interlagos-m103 fidelity class, this time a
   BEHIND-convergence (chaser), invisible to the ahead-gated corridor
   check and the pack gates.
2. CERTIFICATION (new gap class): the true survivor SE dies in BOTH
   offline worlds because both model ME as the selfMove proxy -- the
   survivor exists only under the champion's own continued play
   (oracle t=26). Even a perfect trigger had nothing certifiable to
   switch to: survival-only switching finds no survivor.

Per-shape trigger gates were measured and REJECTED before building
(chaser-converging slow moves: 121-235/race -- chasing is just racing).
THE FIX reuses existing surfaces and machinery, no new gates:
(a) the r60 smoke test (already on every trap-0 slow move) runs the
    SCORER-RIVAL world instead of smom -- the chaser lands in the
    round-59 nearest-3 set and the death is seen;
(b) new scorerSelf flag through simOutcome/dangerJointSearch: the slow
    escalation certifies ALTERNATIVES with a scorer-modeled me
    (scorerMoveOverState applied to myself, recursion-guarded exactly
    like scorer rivals). All other call sites byte-identical.

SITE PROOF: zandvoort s45 saved (ESC scorer-dies at m920, DJS switch to
SE simT=30, race 0-crash); BONUS: zandvoort s34 and hungaroring s40
also saved -- 3 of the 5 harvest-2 crashes killed by one upgrade; the
zandvoort doom band s31-45 improves 3 crashes -> 1. Coil s32 and
zandvoort s42 remain open (different classes). All promoted saves
intact; goldens pass; probe 2/27.

GATES vs the r75 champion: never-worse everywhere -- 8car 770/0 x3 with
exact-tie aggregates (63.69/63.66/63.64) and balanced +/-0.1 track
reflows (hungaroring +0.1 on s1-5, slalom -0.1/gear +0.1 on s6-10,
sprint -0.1/chicane +0.1 on s11-15 -- the safety-round reflow precedent
of r72); h2h c=0 both bands with places netting BETTER (4.494/4.499 vs
4.506/4.501); 4car/1v1/slow exact ties. COST: +29% wall on crawl-heavy
monaco (worst case), ties on fast tracks. ROUND 78 IS PROMOTION-READY;
the word is the user's.

## OPEN CLASS (2 sites, ONE shape): the deep-horizon commitment class

Both remaining harvest-2 crashes classify IDENTICALLY, and the shape is
new: **zandvoort s42** (p6, death m614; sealed by m582, last avoidable
**m566** with SIX survivors, chosen SW dies @r6) and **coil s32** (p7,
death m319; sealed by m263, last avoidable **m247** with SEVEN
survivors, chosen NE dies @r9).

THE DEFINING PROPERTY: at both entries the faithful scorer-rival
replica is EXACTLY AS BLIND as the cheap one --
  zandvoort m566: chosen SW smom=alive t=67 tier=3, orivals=alive t=67 tier=3
  coil    m247:   chosen NE smom=alive t=22 tier=3, orivals=alive t=22 tier=3
(contrast the FIDELITY class -- m260/m103/m920 -- where orivals sees
DEAD@r2 and only the in-game model was blind). No model upgrade can
reach these: the deaths are 6 and 9 rounds out while every promoted
rollout horizon is 3-8, and the entries are open, roomy, tier-3 states
with no local danger signature at all. THE INSTRUMENT ITSELF IS
EXHAUSTED for this class; the fidelity ladder is finished.

Both survivors' signature is the same: at zandvoort m566 the chosen
holds spd^2=58 into the coming narrowing while survivors shed to 34-53;
at coil m247 the chosen holds spd^2=36 into a monotonically narrowing
spiral while survivors shed to 16-26. CANDIDATE DIRECTIONS (unclaimed):
(a) STATIC funnel/cut-set analysis on the reachability map -- the doom
is a track-topology property, visible without any rollout, and matches
AI_DEVELOPMENT.md's standing "bottleneck-aware triggers" direction;
(b) speed-vs-corridor-width certification at entry. Rollout deepening
is NOT the answer: 9-10 rounds at every fast fire is outside the
measured budget and r65 showed horizon alone perturbs fields into new
pockets.

## OPEN CLASS: coil s32 -- the 9-round commitment horizon (measured, unfixed)

Forensics on the second harvest-2 crash (p7, m319 death). The oracle
walk-back is the DEEPEST commitment the campaign has measured: sealed
by m263 (7 rounds out), and **m247 is the last avoidable move** --
SEVEN survivors on the table (NW/N/W/NONE/SW/S/SE, oracle t=20-21) and
the chosen NE dies @round 9. Every intermediate move (255-311) is
already lost.

WHY NO INSTRUMENT SEES IT: policy_matrix at m247 -- chosen NE
smom=alive t=22 tier=3 AND **orivals=alive t=22 tier=3**. This is NOT a
fidelity gap (unlike m260/m103/m920): the faithful scorer-rival world
is equally blind, because the death is 9 rounds out while every
promoted rollout horizon is 3-8. The class is a HORIZON limit, not a
model limit -- the first such class since the campaign began.

WHY NOT JUST DEEPEN: AI1_DEEP_HORIZON=8 already costs; a 9-10 round
scorer-rival rollout at every fast-pack fire is far outside the
measured budget (r73 measurements: ~20 ahead-pack fires/race), and the
r65 evidence says horizon alone perturbs fields into new pockets.
CANDIDATE DIRECTIONS (unclaimed, for a future round): (a) a cheap
STATIC funnel/cut-set test on the reachability map -- coil's spiral
narrows monotonically, so the doom is a track-topology property visible
without rollout; this is also AI_DEVELOPMENT.md's standing
"bottleneck-aware triggers" direction; (b) speed-vs-corridor-width
certification: at m247 the survivors all shed speed while NE holds
spd^2=36 into a narrowing spiral.

## Round 78 — scorer smoke test + scorer-me certification (PROMOTED 2026-08-12, per user)

Promotion executed: smoke test + escalation mirrored into AI2 (shared
scorerSelf machinery), strict probe ALL IDENTICAL 0/27, golden corpus
regenerated with the new `zandvoort-s45-8p` fixture pinning the rescue
(1177 turns, 7/0) and two intentional slow-class reflows (lemans-s4
crash-free, monaco-s9-4p crash-free and 3 turns FASTER); every other
hash unchanged. Docs record the eighth bounded safety proof.
POST-PROMOTION SELF-TIE BATTERY CERTIFIED: probe 0/27 and ALL 8 stages
exact self-ties with zero crashes anywhere -- 770/0 x3
@63.69/63.66/63.64, h2h 4.500 c=0 both bands, 4car 330/0/61.75, 1v1
110/0/60.64, slow 28/0/104.11. The canonical record is 2310/2310 again,
now with the r78 fidelity stack. Champion baselines re-seeded from the
self-tie logs (extract_baseline col=1 -> scratchpad/baseline_*.json).
AI1 and AI2 are identical again.

CAMPAIGN STATE after r78: the FIDELITY ladder is complete (every known
class where a faithful model sees a death the cheap model misses is
closed: r59 scorer rivals, r67/r71 dense packs, r73 ahead-corridor +
widened cap, r74 compressed queue, r78 smoke test + scorer-me). The
only open crash class is the DEEP-HORIZON COMMITMENT class above, which
that ladder provably cannot reach. Harvest-2 tally: 5 crashes found, 3
fixed, 2 open and classified.

## Round 78 (local agent, gates PASSED): scorer smoke test + scorer-me certification

THE ZANDVOORT-S45 FORENSICS found a TWO-LAYER gap at m920 (p8, spd^2=40
braking while p7 chases at spd^2=53 down the same straight):
1. TRIGGER: the r60 smoke test's smom-5 read the doomed chosen ALIVE
   tier-3 while orivals kills it @r2 -- the THIRD member of the
   nurburgring-m260 / interlagos-m103 fidelity class, this time a
   BEHIND-convergence (chaser), invisible to the ahead-gated corridor
   check and the pack gates.
2. CERTIFICATION (new gap class): the true survivor SE dies in BOTH
   offline worlds because both model ME as the selfMove proxy -- the
   survivor exists only under the champion's own continued play
   (oracle t=26). Even a perfect trigger had nothing certifiable to
   switch to: survival-only switching finds no survivor.

Per-shape trigger gates were measured and REJECTED before building
(chaser-converging slow moves: 121-235/race -- chasing is just racing).
THE FIX reuses existing surfaces and machinery, no new gates:
(a) the r60 smoke test (already on every trap-0 slow move) runs the
    SCORER-RIVAL world instead of smom -- the chaser lands in the
    round-59 nearest-3 set and the death is seen;
(b) new scorerSelf flag through simOutcome/dangerJointSearch: the slow
    escalation certifies ALTERNATIVES with a scorer-modeled me
    (scorerMoveOverState applied to myself, recursion-guarded exactly
    like scorer rivals). All other call sites byte-identical.

SITE PROOF: zandvoort s45 saved (ESC scorer-dies at m920, DJS switch to
SE simT=30, race 0-crash); BONUS: zandvoort s34 and hungaroring s40
also saved -- 3 of the 5 harvest-2 crashes killed by one upgrade; the
zandvoort doom band s31-45 improves 3 crashes -> 1. Coil s32 and
zandvoort s42 remain open (different classes). All promoted saves
intact; goldens pass; probe 2/27.

GATES vs the r75 champion: never-worse everywhere -- 8car 770/0 x3 with
exact-tie aggregates (63.69/63.66/63.64) and balanced +/-0.1 track
reflows (hungaroring +0.1 on s1-5, slalom -0.1/gear +0.1 on s6-10,
sprint -0.1/chicane +0.1 on s11-15 -- the safety-round reflow precedent
of r72); h2h c=0 both bands with places netting BETTER (4.494/4.499 vs
4.506/4.501); 4car/1v1/slow exact ties. COST: +29% wall on crawl-heavy
monaco (worst case), ties on fast tracks. ROUND 78 IS PROMOTION-READY;
the word is the user's.

## HARVEST 2 INTERIM (2026-08-12, local agent): fresh-seed crash rate up 5x

Phase 1 of the second fresh-seed harvest (8-car seeds 31-45, all 22
tracks, the r75 champion) found **5 crashes in 330 races**: coil s32
m319, zandvoort s34/s42/s45, hungaroring s40 (all last-runner deaths at
mid speed). ATTRIBUTION COMPLETE (A/B replays on the r74 and r71
champions) -- the initial "5x regression, hold promotions" reading was
WRONG and is retracted: **four of the five are ANCIENT classes** (coil
s32, zandvoort s34/s42, hungaroring s40 crash on the r71 champion too;
seeds 31-45 are simply doom-denser than 16-30, so the harvest-1
comparison conflated champion with seed band). The pace stack is NOT
implicated; in-flight pace gates stand. ONE genuine regression:
**zandvoort s45** -- clean on r71, crashes on r74/r75, introduced
somewhere in the r72-r74 window (trap-monotone / corridor /
compressed-queue). SYSTEMIC LESSON: the canonical seed-1-15 battery is
mined out as crash evidence; doom-dense fresh bands (zandvoort 31-45
foremost) should join future promotion gates. The five sites are the
open counterexample queue; forensics follow harvest completion.

## Round 77 (local agent, REJECTED at stage 1): strict filter overreach

The r76 refinement executed: certified trap<=L2 faster lines must now
STRICTLY IMPROVE the widened scorer-rival final tt vs the incumbent
(incumbent sim evaluated lazily, cached per turn) -- survival alone let
empty-track-faster lines lose their gain to traffic. On the exact r76
failure band (seeds 6-10, 5 tracks): the zigzag regression is GONE
(within rounding), interlagos/spielberg/lemans each -0.1, spa tied,
TOTAL -0.06, 0 crashes. BUT the probe showed the true footprint: 21/27
races divergent -- the strict filter did not only gate the NEW L2
admissions, it ALSO stripped the promoted trap-0/smom-3 r58 behavior
(proven lines now rejected for not beating the incumbent in-sim).
STAGE 1 VERDICT: 769/1 (A CRASH) with FOUR tracks +0.1 slower
(silverstone/monaco/spielberg/lemans) and aggregate +0.01 -- rejected
on the spot, battery aborted, arm reverted.

LESSON (the certified-pace ladder): the r58 trap-0 + smom-3 admission
is load-bearing champion behavior -- filters may only be ADDED to new
admission classes, never substituted under existing ones. NEXT ARM
(recorded): two-tier admission -- keep r58 byte-identical for trap==0
lines; require the widened scorer-rival STRICT-IMPROVEMENT certificate
only for the newly admitted 0<trap<=L2 lines. The r76/r77 evidence pair
suggests the L2 class carries the zigzag risk (r76) while the trap-0
class carries the broad pace (r77), so the two-tier split is exactly
the shape both rejections point at.

## Round 76 (local agent, REJECTED under the no-slower-track standard)

The r58 certified-pace override composed with the r75 finish sprint:
admit trap<=L2 (0.5) strictly-faster lines (was trap==0.0 only) and
certify with the widened scorer-rival world (cap AI1_DEEP_CERT_RIVALS=6,
AI1_DJS_ROUNDS) instead of smom-3 -- the world the r73/r74
counterexamples proved blind at pack sites. Weaker filter, stronger
proof. AI1 only; AI2 mirror untouched.

HISTORY: originally gated clean as a round-75 candidate vs the r74
champion (770/0 x3 with -0.01/-0.01/+0.00; h2h c=0 both bands, places
net better on aggregate) -- superseded mid-flight by the finish-sprint
promotion and renumbered. RE-COMPOSED on the new champion: 6-track
seeds-1-5 bench -0.01 total, interlagos -0.1, lemans a hair faster, NO
TRACK SLOWER (spa -- the rejected remote arm's failure track -- exactly
tied), 0 crashes. Probe on the composition: 3/27 divergent (a pace arm
should fire; divergences bench-verdicted). FULL-BATTERY VERDICT
(2026-08-12): zero crashes everywhere, aggregate -0.01 on 8car s6-10
(63.65 vs 63.66) with s1-5/s11-15 exact ties, h2h/4car/1v1/slow ties --
but the per-track sweep found **zigzag s6-10 +0.1 slower** per finisher
(vs interlagos -0.1 and spielberg -0.1 faster). The same signature that
rejected the remote comparative-certificate arm; the standard applies
symmetrically, so the arm is REJECTED in this form and reverted from
master (the ledger record stays). REFINEMENT PATH for a future round:
the 3 probe-divergent races pinpoint the fire sites -- bisect which
certified-L2 fire slows zigzag s6-10 and tighten the admission (e.g.
require the certified line to also be strictly better on the
scorer-rival final tt, not merely surviving). The instrument itself
(widened scorer-rival certification) remains promoted and trusted via
r73/r74.

## Round 75 - dual-model finish sprint (PROMOTED 2026-08-12)

REFRESH: local and `origin/master` began at the Round 74 champion `b5348a9`.
The fresh `origin/agent/random-track-speedups` branches contained only a
temporary source-export workflow and no racing-code candidate, so the round
was derived locally. The pre-existing primitive-geometry experiment remains
preserved in `stash@{0}` and was not applied or dropped.

FORENSICS: a component-level scan of Monaco eight-car seed 16 found a genuine
late-race pace concession at global move 789. Player 5 at `(5,95)`, velocity
`(1,-6)`, chose `S`, landing at map ttf 15. `SW` lands at ttf 14 but carries a
higher local trap price. Faithful joint replay showed `SW` finishing in exactly
14 rounds and `S` in 15; every other candidate died. The simulation must run
`ttf+1` rounds because its first partial round contains only players after the
mover. Earlier apparent one-turn concessions were rejected when longer oracle
rollout showed equal actual finish rounds.

FIX: when the scorer is within 15 empty-map turns of the flag, examine only
strictly faster candidates at trap tier L1 or better. Accept one only if two
independent joint worlds - exact self with score-shaped rivals, and exact self
with up to six real-scorer rivals - both return finish at the candidate's
empty-map lower bound. The normal danger-joint search still runs afterwards as
an independent survival veto. A 110-race seeds-1-to-5 trigger audit observed
100 successful certificates, all at ttf 14 or below; the cap remains 15 to
avoid overfitting future races to that sample.

GATES: across all 22 tracks, the three eight-car bands were 770/0 vs 770/0
with mean finisher moves 63.69 vs 63.82, 63.66 vs 63.79, and 63.64 vs 63.78;
no track was slower. Mixed 4v4 won all three bands at zero crashes:
4.483/4.517, 4.483/4.517, and 4.475/4.525. The 2v2 gate slightly won
2.498/2.502, 1v1 tied 1.500/1.500, and slow mode improved 140/0 at 104.16
vs 140/0 at 104.27. Seven warm interleaved Monaco seed-16 pairs measured a
small compute overhead (1.8% trimmed mean, 3.2% median), accepted for the
verified on-track pace gain.

PROMOTION: the rule was mirrored into AI2 and the nine-track x three-seed
strict probe returned 0/27 divergences. JDK warning-as-error compilation, 26
track-data tests, core/main tests, headless smoke and all eleven golden races
pass. Five existing golden races become 1-6 turns faster with zero crashes;
five old hashes remain byte-identical. The new `monaco-s16-8p` fixture pins
950 turns, 7/0, hash
`67c69dacd5844cc0a4aa8d31b4b43b2c9be87398221ef3b3fe5dedfb24a45f4b`.
AI1 and AI2 are identical again.

REMOTE FOLLOW-UP (REJECTED): the final pre-push fetch revealed the newly
published `origin/agent/ai-pace-round-75` at `d49e9eb`. Its AI1-only
comparative eight-round certificate was composed on top of the promoted
finish sprint and evaluated against Round 75 AI2, rather than trusted against
the older base used by the branch. The nine-track x three-seed probe changed
seven races with zero crashes, but only Hairpin seed 2 immediately saved a
turn; Interlagos and Hungaroring reflowed at equal pace, while Nurburgring
redistributed finisher turns without reducing the total. The full 22-track
seeds-1-to-5 band remained 770/0 on both sides and was effectively flat
(63.68 vs 63.69), while making Spa and Zandvoort about 0.1 move per finisher
slower; Nurburgring and Coil gained about 0.1. The complete A/B took 479.5s.
This fails the no-slower-track standard and adds expensive deep rollouts for
a negligible aggregate result, so the remote candidate was removed. Its
branch remains available for future forensic ideas; none of its code entered
the champion.

## Round 74 — compressed rear-queue certificate (PROMOTED 2026-08-11)

REFRESH: `origin/master` was already at the local Round 73 plus primitive
edge-cache champion (`998d48d`). The fresh `origin/agent/ai-round-74` and
`origin/agent/ai-speedups-75` branches contained source-export workflows,
not candidate racing code; `origin/agent/random-track-speedups-76` pointed
at `998d48d` with no distinct commit. This round was therefore derived
locally from new races.

FAILURE HARVEST: the regular 22-track suite over seeds 16-20 completed all
110 eight-car races with 770/770 finishers and zero crashes. Extending the
historically hard tracks over seeds 21-50 found the first failure after 19
more races: Zigzag seed 22, player 8 crashing at global move 104. Exact
oracle replay found move 72 as the last avoidable decision: from `(51,55)`
at velocity `(8,0)`, champion `S` is doomed while `NW` and `N` survive at
least 14 rounds. The empty-track map gives all three the same ttf=56, and
the smom model reads `S` alive/tier-3 at every tested horizon. The faithful
scorer-rival model instead proves `S` dead at round 2 while retaining both
escapes. This is the side/rear complement of Round 73's ahead-convergence
failure, not a horizon shortage.

FIX: inside the existing fast deep-pack blind-alive path, invoke the widened
six-rival scorer certificate when the whole seven-rival field is within
Chebyshev radius 10, at most one rival is ahead, at least two rival bodies
already occupy the mover's neutral 3x3 landing grid, and a near-equal low-trap
escape exists. The switch remains survival-only. At the target it changes
`S` to `NW` and converts 6 finishes / 1 crash to 7 / 0. The structural gate
occurred 13 times across the 129 harvested logs, in only six races; five
remained move-identical and only Zigzag s22 changed.

PROMOTION GATES: all three canonical eight-car bands remain exact champion
ties with zero crashes: 770/0 at 63.82, 770/0 at 63.79, and 770/0 at 63.78.
All three 4v4 bands are exact 4.500/4.500 ties with zero crashes; 2v2 is
2.500/2.500, 1v1 is 1.500/1.500, and slow mode is 28/0 at 104.25 for both.
After mirroring AI1 into AI2, the nine-track x three-seed strict probe is
0/27 divergent, Java tests/build and headless smoke pass, and all ten golden
races pass. The additions-only `zigzag-s22-8p` fixture pins 529 turns, 7/0,
hash `ca4ab1d3f7ab66277f3cca60d1376544e115f1742ab91f08551195d3759de606`.
AI1 and AI2 are identical again.

## Round 73 — certified corridor check (PROMOTED 2026-08-11, per user)

Promotion executed: the corridor check mirrored into AI2 (shared
scorerCap machinery; AI2 mirror comment convention), strict probe ALL
IDENTICAL 0/27, golden corpus regenerated ADDITIONS-ONLY (every prior
hash unchanged -- the check is inert on all existing fixtures) with the
new `interlagos-s10-8p` case pinning the save (1049 turns, 7/0), docs
updated (sixth bounded safety proof). POST-PROMOTION SELF-TIE BATTERY
CERTIFIED: probe 0/27, ALL 8 stages exact self-ties with ZERO crashes
anywhere -- 770/0 x3 @63.82/63.79/63.78 (the s6-10 slice back to
crash-free), h2h 4.500 c=0 BOTH seed bands, 4car 330/0/61.81, 1v1
110/0/60.64, slow 28/0/104.25. The canonical record is 2310/2310 again.
Champion baselines re-seeded from the self-tie logs (extract_baseline
col=1 -> scratchpad baseline_*.json; consumed via BENCH_BASELINE). AI1
and AI2 are identical again.

## Round 73 (local agent, gates PASSED): certified corridor check for convergence dooms

THE R72 PROMOTION REGRESSED INTERLAGOS: the post-promotion self-tie
battery (both bodies = r72 champion) came back 769/1 on 8car s6-10 --
interlagos s10, p7 crash at m143 (plus 1 crash in mixed h2h s6-10, same
track/seed band). The old champion is 770/0 head-to-head on the same
seed. Their round-72 split gates HAD flagged "interlagos s10", but the
promotion evidence re-checked only interlagos FOUR-car; the 8-car slice
regressed. Root shape: the trap-monotone guard changed a slow
start-funnel choice at m19 (p3 SW->S), and the perturbed field reached a
LATENT doom pocket 124 moves later -- the ancestral-perturbation class,
so the fix targets the latent weakness, not the (principled) r72 gate.

FORENSICS: p7 fully sealed by m127; **m103 is the last avoidable move**
(chosen NE, accel to spd^2=68; survivors NONE/E/S all brake/hold, oracle
t=105). The 3-round fast DJS world misses the @r5 death; the r65 smom-8
deep pre-screen read it ALIVE **tier 3** (not even fragile -- silent
keep). policy_matrix: chosen NE smom=alive t=104 tier=3 vs
**orivals=DEAD@r2** -- the SECOND member of the nurburgring-m260
fidelity class, and this one at speed. The kill is CONVERGENCE: the
killers (p4/p6/p1, ranks 4-6 by landing distance) brake INTO the
shedding corridor over r1-3.

NEGATIVE RESULT (recorded): a frozen-rival triage (rivals held static)
does NOT see convergence dooms -- the killers start OUTSIDE the corridor
and move in; static pessimism points the wrong way. Only faithful
forward rival models see it. Also decisive: the round-59 nearest-3
scorer set at m103 is exactly the harmless REAR queue (p2/p5/p8); the
killers are beyond the cap -- the MAXRIVALS fidelity gap biting in the
wild, as predicted in the round-72 review.

R73 FIX (AI1): in the deep block's blind-alive path (smom-8 alive and
non-fragile), with >= AI1_DEEP_PACK rivals AHEAD of the landing
(positive dot with the landing velocity, Cheb 10), run the certified
scorer-rival DJS at the widened **AI1_DEEP_CERT_RIVALS=6** cap
(simOutcome/dangerJointSearch got a scorerCap parameter; all existing
call sites keep the round-59 cap of 3). Survival-only switch as
everywhere. Trigger rates measured over the 330-race harvest BEFORE
building (the law): fast&pack>=3 48/race (= existing pre-screen rate),
fast&ahead>=3 19.8/race, at spd^2>=64 11.0/race; in-race CORR fires ~16
on interlagos s10. Spot saves: interlagos s10 0 crashes (CORR at m103,
chosen DIES in certified sim, switch), s6-9 clean, nurburgring s19 7/0
and monaco s9 intact. GATES COMPLETE (2026-08-11): probe 0/27 inert; never-worse on all 8
stages with BOTH regression stages strictly improved -- 8car s6-10
770/0/63.79 vs the champion's 769/1/63.79 (interlagos row 35/0 vs 34/1)
and mixed h2h s6-10 c=0 (4.498) vs c=1 (4.502); everything else exact
ties (770/0/63.82, 770/0/63.78, h2h 4.500 c=0, 4car 330/0/61.81, 1v1
110/0/60.64, slow 28/0/104.25). ROUND 73 IS PROMOTION-READY; the word
is the user's.

## 2026-08-11 speedup: primitive geometry-edge cache (behavior-invisible)

Pulled the Round 73 champion at `76ff22f` and re-profiled both cold and
warm Nurburgring seed 19. The remaining shared-runtime allocation hotspot
was the geometry cache's `HashMap<Long,Boolean>`: every lookup boxed the
mixed edge key, and every new edge also allocated a node and boxed value.

FIX: `RaceGame.EdgeLegalCache` is a single-writer open-addressed primitive
long-to-boolean table. A state byte distinguishes missing, false and true,
so zero and every other 64-bit key remain valid. It grows at two-thirds
load and retains the bijective SplitMix key finalizer. Direct tests cover
misses, both values, zero/high-bit keys, updates and a 10,000-entry resize.

MEASURED (three cold and five warm interleaved pairs, separate disk caches):
Nurburgring seed 19 cold median 13.533s -> 12.628s (**6.7% faster**), warm
median 2.584s -> 2.535s (**1.9% faster**). All 16 measured logs had one
SHA-256 hash. Warm JFR `Long.valueOf` allocation pressure fell from 21.46%
to 2.81%. Validation: Java unit suites, headless smoke, all nine golden
races, strict 27-case AI1/AI2 probe, and cold/warm reach-cache log+dump
comparison all pass.

REJECTED FOLLOW-UP: primitive blocked-cell and long-to-double mobility
tables were not kept. A separate nine-pair warm A/B against the edge-only
build was slightly worse: median 2.564s vs 2.533s and trimmed mean 2.546s
vs 2.525s (0.8% slower), despite exact logs. Do not repeat without a design
that reuses storage across turns and proves a gain.

## 2026-08-11 speedup: reachability disk cache (behavior-invisible)

JFR profiling of a nurburgring race showed the CPU is dominated by
REACHABILITY CONSTRUCTION, not AI search (post int-array):
isMoveLegalGeometryCached+isMoveLegalGeometry ~2300 samples and
computeReachability ~1950 vs ~180 for the AI search stack. The BFS is a
pure function of track geometry (seeds only move start placements) yet
every race recomputed it — 12-17s per nurburgring-class race, and the
whole EDT wait the user hit interactively.

FIX: cache turnsArr + the legal-alive mask per geometry hash
(SHA-256 over cols/rows/vmax/border points) in
%LOCALAPPDATA%/theoreticRacing/reach_cache (RACING_REACH_CACHE
overrides; NOT the install dir — OneDrive must not sync multi-MB
caches). Load re-derives the cheap roomy/shed/cert sweeps (~0.3s pure
array passes). The legal-alive mask MUST be stored: rebuilding it cold
pays nearly the full geometry bill again (the mask pass relies on the
edge cache the BFS warms). Atomic tmp+move writes (pid-suffixed);
any validation/IO failure falls back to a fresh compute.

MEASURED (nurburgring s19): cold bfs=12406ms -> warm total=358ms (~35x).
PROOF (tracks/verify_reach_cache.sh): byte-identical race logs AND
byte-identical --dump-reach maps cold vs warm, on nurburgring and
sprint. Benches inherit the speedup automatically (same jar, shared
cache dir); the forensic dump format and oracle tooling are untouched.

NEXT SPEEDUP TARGET (recorded, unclaimed): a segment-legality bitset
inside the BFS/mask — geometry queries repeat massively across velocity
states; a flat (x,y,dx,dy) bitset (~2MB) could halve the remaining cold
compute. Overlaps the runtime-cleanup territory of the other agent's
int-array line — coordinate via this ledger before building.

## Round 72 — trap-monotone seal guard (PROMOTED 2026-08-10)

### Failure class

The 770-race fresh-seed harvest left one eight-car crash after Round 71: Nurburgring seed 19. At player 4 move 260, the main scorer selected `N` with score 64.275 and trap penalty 0.5. The legacy `sealGuard` then discarded it as worst-case sealable and selected the fastest unsealable alternative, `E`, despite `E` scoring 73.161 with trap penalty 2.0. `E` entered the doomed thread and player 4 crashed at move 292; the scorer's original `N` was oracle-alive.

This is the same structural disease seen in earlier pace regressions: an auxiliary selector ignored the scorer's load-bearing trap ladder. The seal proof is useful, but it is not coherent to avoid a theoretical future box by choosing a state with strictly fewer safe local continuations.

### Change

The seal guard now accepts an unsealable replacement only when its trap penalty is no worse than the scorer choice. The existing geometry, occupancy, alive-state and fastest-time requirements remain unchanged. No score threshold or track-specific constant was added.

### Evidence

- Nurburgring eight-car seed 19: 6 finishes / 1 crash / 698 turns becomes 7 / 0 / 760. The rescued car completes the race rather than disappearing early, so total turns rise as expected.
- Mixed Nurburgring seed 19: AI1 0 crashes versus pre-promotion AI2 1 crash. Mean place moves 4.625 versus 4.375 because the rescued back-marker now occupies a finishing place; crash count is the governing metric for this safety proof.
- Le Mans seed 4, Hungaroring seeds 6 and 20, Monaco four-car seed 9, and Interlagos four-car seeds 3 and 4 remain move-for-move identical to Round 71.
- Short-track eight-car A/B, seeds 1–5 on sprint, hairpin, triangle, chicane and curve: 23 of 25 logs exact. The two seal-guard divergences are both crash-free; sprint seed 5 costs one turn and chicane seed 4 saves one, for net zero.
- Four-car seeds 1–5 on sprint, hairpin, triangle, chicane and bigoval are all exact.
- New frozen golden fixtures pin Nurburgring eight-car seed 19 and Monaco four-car seed 9.
- The pre-existing zigzag eight-car seed-4 fixture changes safely: 7 finishes / 0 crashes remain unchanged, total turns improve from 532 to 530, and the middle finishing order reflows. Its hash/summary are deliberately promoted with the policy.

Round 72 was promoted into both AI bodies. AI1 and AI2 are identical again.

### Open frontier recorded at review (local agent, merge-preserved)

The trap-monotone gate removes m260 from the decision path but the
ROLLOUT FIDELITY GAP it exposed is still real and unfixed: the in-game
scorer-rival rollout read the doomed E ALIVE (t=58) while orivals sees
DEAD@r2. Review discrimination of the r71 suspects: the me-proxy is
ELIMINATED (orivals uses the same selfMove me and still sees the death);
prime suspect is **AI1_SCORER_MAXRIVALS=3** -- rollout membership is the
3 nearest rivals of my landing, fixed at start, so at crawl queues
(~7 near rivals at m260) the actual box formers run the drifting smom
proxy and the box never forms in-sim. Second suspect: the
IN_SCORER_SIM suppressions (1v1 solver, certified-pace, certified-UNC,
all DJS machinery are OFF for sim rivals; the sealGuard runs). Fallback
arm for a future round if the class resurfaces: parameterize the scorer
cap (dense/certification fires get the whole near field, ordinary slow
fires keep 3), then a survival-only certified sealGuard swap. Anchor
soundness of the promoted gate was verified locally: every
guard-eligible direction is also scored, so no swap target carries a
phantom zero trap tier.

---

## Round 71 — fresh-seed harvest + small-field pack gate (PROMOTED WITH ROUND 72)

COUNTEREXAMPLE HARVEST on the round-70 champion: 770 fresh races (8-car
s16-30, 4-car s6-15, 2-car s6-15, all 22 tracks) found exactly TWO
crashes -- strong generalization evidence for the mechanism stack.

1. **monaco 4-car s9 (FIXED AND PROMOTED): the small-field funnel class.**
   Entry m27 (spd^2=13, all 3 rivals within Chebyshev 10): chosen NONE
   dies @r3 with survivors N/SE (oracle). smom is BLIND and NON-FRAGILE
   (alive t=100 tier=3) but orivals sees DEAD@r2 -- only the trigger was
   missing: the round-67 dense-pack gate requires sealRivals >= 7 and
   spd^2 >= 16. R71 FIX (AI1): generalize to small fields --
   whole-live-field-packed + closeEscape with sealRivals >=
   AI1_SLOW_PACK_MIN=3 and spd^2 >= AI1_SLOW_PACK_SPD2_SMALL=12 (start
   grids stay below). Race saved (26 escalations, 3 verdicts, 2
   switches); 8-car keeps the original 7/16 gate.
2. **nurburgring 8-car s19 (FIXED BY ROUND 72): compound sealGuard +
   fidelity failure.** Entry m260: the scorer's own argmin picked the
   oracle-alive N (score 64.28) but the SEALGUARD swapped to the doomed
   E (73.16 -- trap 2.0 + unc 3.46 + ce 4.16 ignored by the "fastest
   unsealable" rule): a paranoid 1-ply sealability distinction discarded
   a 9-point score advantage, the round-35 disease resurfacing in an
   auxiliary selector. The trap trigger then fired and the 6-round
   scorer-rival rollout said ALIVE though the death is @r4 real /
   DEAD@r2 under orivals -- the in-game rollout behaves like smom at
   crawl-queue sites (both matrix rows measured; smom blind t=58
   tier=3). Round 72 fixes the earlier selector error directly: an
   unsealable replacement may no longer worsen the scorer's trap tier.
   The deeper rollout-fidelity mismatch remains a research topic, but it
   is no longer on the decision path for this counterexample.

**Promotion result:** the small-field gate was promoted with Round 72. On Monaco four-car seeds 6–10 it improves 14 finishes / 1 crash to 15 / 0; the target 2v2 seed keeps exact 2.500 place parity while removing the crash.

**Certification record (merge-preserved):** round 71 was fully gated
TWICE before promotion -- on the pre-int-array body (r71g) and again on
the int-array body (r71b) after the rework landed mid-round: probe 0/27
inert both times, monaco s9 save exact both times (0 crashes, 26
dense-pack escalations), and ALL 8 battery stages exact ties both times
(770/0 x3 @63.81/63.78/63.77, h2h 4.500 c=0 x2, 4car 330/0/61.81, 1v1
110/0/60.64, slow 28/0/104.25). The composition on the int-array body
was committed by the user (d413cf9) with goldens hash-identical.

## 2026-08-09 round-70 promotion: close the four-car Interlagos gap

**Round 70 was the champion at this point; AI1 and AI2 were identical at rest.**
The only known round-69 promotion-battery failures were four-car Interlagos
seeds 3 and 4. Both converge to the same p4 trajectory and crash at move 480.
The generalized four-car oracle reproduced 20 logged moves exactly and found
move 456 as the last save: from `(53,155) v(-5,-1)`, champion `W` dies at the
six-round frontier, while `NONE`, `E`, `S` and `SE` all finish. The existing
slow danger rollout stopped at five rounds and therefore called `W` alive.

Round 70 extends the scorer-rival verdict to six rounds **only** for slow
chosen moves already at trap tier L1 (penalty 2.0). It switches `W -> NONE` in
the shared failure board. Promotion evidence:

- full 22-track four-car s1-5: **330/0/61.81 vs round-69 328/2/61.79**;
  every track except Interlagos is exact, and the move-average increase is the
  two rescued third finishers;
- mixed 2v2 s1-5: exact **2.500/2.500** place parity, crashes **0 vs 2**;
  Interlagos s1-15 also keeps 2.500 parity while improving crashes **0 vs 7**;
- canonical eight-car s1-5: exact **770/0/63.81** in both bodies;
- 1v1 s1-5: exact **1.500/1.500**, zero crashes; slow suite: exact
  **28/0/104.25**; the pre-promotion 27-race eight-car screen was inert.

The forensic tools now infer active player count from each log; `oracle_roll`
also accepts `RACING_PROPS`, and its rollout/verification loops use the actual
field length rather than a hard-coded eight. This makes the same exact-oracle
workflow reusable for 2-, 4- and 8-car failures.

## Superseded champion: round-69 promotion and runtime cleanup

**Round 69 was the prior champion; AI1 and AI2 were identical at rest.**
It builds on the round-68 dense slow-pack champion and promotes a new
cross-model survivor certificate:

- Hungaroring seed 20: the old line chooses `NONE` at p5 move 181, enters an
  oracle-proven doom and crashes at move 221. The topology-shaped eight-round
  model proves that locally narrow pick dies and proposes `NE`; the independent
  scorer-rival model must also certify `NE` alive before the switch is allowed.
- The broad cross-model rule was REJECTED after it created a Hungaroring seed-6
  crash. Requiring the current pick's trap penalty to be at least 0.5 removes
  that false switch while retaining the seed-20 rescue.

Promotion evidence: the round-69 candidate column in the full default 22-track
seeds-1-to-5 self-play gate was **770/0/63.81**; the round-68 champion baseline
was **770/0/63.82**. Difficult-track fresh seeds and synthetic gates added no
candidate crashes; affected-track mixed fields over seeds 1-15 slightly favored
AI1, and Hungaroring seeds 16-25 mixed
fields favored AI1 in both place and crashes. After mirroring into AI2, the
nine-track x three-seed probe was **27/27 move-identical**. JDK-25 warnings-as-
errors compilation, 26 track-data tests, core tests, headless smoke and all six
golden races passed. Round 69 does not require a new golden fixture; the
round-68 corpus already records the Le Mans rescue and one-move Zigzag seed-4
pace/order change.

Shared behavior-preserving cleanup shipped with the champion: a cached
`Direction.values()` array; one opponent mobility projection and transposition
memo per real turn instead of rebuilding them per candidate; and a bijective
SplitMix64 finalizer on packed edge-cache keys to avoid `Long` hash bucket
clustering. Focused A/B measurements were 29.5s without the mobility memo versus
20.6-20.7s with it under the exercised load; repeated reachability median was
1.915s versus 2.160s on untouched HEAD (about 11%). Do not reinterpret those
focused measurements as a whole-benchmark speedup.

## 2026-08-07 repository and AI1 frontier update

The repository now has portable JDK-25+ build/test scripts, genuine Linux
headless auto-play, lint-clean dependency-free unit tests, structural checks for
all bundled tracks, a deterministic AI2 golden-race corpus, a cheap AI1/AI2
move-log probe, and a manual nine-stage GitHub Actions promotion battery. The
benchmark now uses isolated temporary properties/logs and fails non-zero on
invalid Java runs. `user.properties` and Eclipse metadata are no longer tracked.

Two source defects were fixed in both bodies before new experimentation:
`RaceGame.gameLogPath()` no longer recurses, and `futureMobility4` now excludes
the correct one-based player number. AI1 and AI2 remain separate full scorer
bodies by user choice.

**Round-67 candidate record (promoted as part of round 68): dense slow-pack
escape proof.** In the sole canonical round-66 failure (Le Mans seed 4), the victim
entered a moving eight-car funnel at move 55 while the cheap smom model missed
the future box. AI1 now escalates trap-0 slow moves only when all seven live
rivals are within Chebyshev 10, landing speed^2 >= 16, and a near-equal low-trap
alternative exists. The real-scorer-rival rollout changes p7's move 55 SE->SW
and converts 6 finishes / 1 crash into 7 / 0.

## Superseded champion (round 68, promoted per user 2026-08-08)

**The round-66 base + the other agent's futureMobility4/gameLogPath
fixes (both bodies) + the round-67 dense slow-pack escape proof,
mirrored into AI2: on trap-0 slow moves, when the WHOLE live field is
packed within Chebyshev AI1_SLOW_PACK_R=10 of the landing (sealRivals
>= AI1_SLOW_PACK=7, spd^2 >= AI1_SLOW_PACK_SPD2=16) and a near-equal
low-trap alternative exists, the scorer-rival rollout arbitrates even
when the smom smoke test reads alive -- the lemans-s4 funnel.**
Canonical numbers (both columns live, post-fix): **8-car s1-5
770/0/63.82; s6-10 770/0/63.78; s11-15 770/0/63.76 -- 2310/2310, the
first ZERO-CRASH 15-seed battery in campaign history; h2h 4.497/4.497
(places won both sets) c=0; 4-car 328/2/61.79 (see interlagos note);
1v1 110/0/60.64; slow 28/0/104.25.** Round-67 vs the fixed champion
was never worse on any stage. Self-tie: inert_probe 27/27
move-identical; caches re-seeded from the r67 AI1 columns; golden
corpus regenerated (lemans-s4-8p now pins 7/0, case renamed from
-known-crash).

RESOLVED BY ROUND 70 -- forensic anatomy (local agent's oracle
walk-back, which both agents' fixes address): the interlagos 4-car
crashes were ONE deterministic doom reached from two seeds
(byte-identical deaths at m480), an ENDGAME finish-corridor class. The
scorer takes the fastest line (m456 W, speed 6, t=14) into a corridor
whose exit two crawling rivals consume; options narrow 5 -> 2 -> 1 -> 0
over four rounds; at m476 the only open cell is segment-illegal so the
scorer regresses to the foresight-free bestLegal path (reach-dead
candidates are skipped before scoring at `ownTurns == MAX_VALUE`). The
trap trigger FIRED at the m456 entry and the scorer-rival rollout RAN
-- but the death sits at ROUND 5, one beyond AI1_DJS_SLOW_ROUNDS=5,
while four healthy survivors existed (oracle m456: NONE/E/S/SE all
finish, t=9). The DJS then diagnosed "DIES, no survivor" correctly at
m460-472 -- true but too late.

CONVERGENT FIXES, one shipped: both agents independently built the
horizon extension the same day. The other agent's promoted round 70
(slow L1 traps -> 6 rounds) is the cheaper variant and empirically
saves both interlagos races (verified locally on the promoted build);
the local agent's variant (endgame-gated: sealRivals <= 3 && landing
ttf <= 20 -> 8 rounds) gated fully clean against BOTH champion bases
(probe 0/27; 8car exact ties x3; h2h parity c=0; 4car 330/0/61.81 vs
328/2; 1v1/slow ties) but was DROPPED as redundant per the
one-proof-one-mechanism law. If a future endgame doom enters through an
L2-severity trap (their L1 gate would miss it; the endgame gate would
not), the dropped variant is the ready answer.

## Superseded champion (round 66, promoted per user 2026-07-28)

**The round-63 champion PLUS the round-65 pack-gated deep escalation,
mirrored into AI2 (one call-site branch; the simOutcome outFinalTier
overload and constants were already shared): fast fires with >= 3
rivals within Chebyshev 10 of the landing run the cheap smom pre-screen
at horizon 8 and escalate to the scorer-rival world on a
dead-or-FRAGILE (final tier <= 1) verdict.** Canonical numbers:
**8-car s1-5 769/1/63.81; s6-10 770/0/63.79; s11-15 770/0/63.79
(2309/2310 finishers, the sole crash = lemans s4, provably invisible);
4-car 330/0/61.84; 1v1 110/0/60.62; slow 28/0/104.25.** Self-tie:
inert_probe 27/27 move-identical + bench-vs-cache per-track rows
identical. Caches re-seeded from the r65 gate's AI1 columns. Both AI
bodies identical again; AI1 free to diverge.

## Superseded champion (round 63, promoted per user 2026-07-26)

**The round-58 base (DJS + sealfix + 1v1 solver + certified pace
tie-break + exact-self/finish-vanish + wide speed trigger + smom rival
sim) PLUS the rounds 59-62 stack, mirrored into AI2 via
patch_promote_r62.py: (r59) recursion-guarded REAL-SCORER rivals for
slow-class DJS fires (scorerMoveOverState, nearest 3 within Chebyshev
10, horizon 5); (r60) the trap-0 smom smoke test escalating to the
scorer rollout on a death verdict; (r61) rival-conditional trap relief
(L1/L2 waived with no rival within Chebyshev 16 of the landing); (r62)
the certified UNC override (pay unc except where a strictly faster line
wins the unc-free comparison AND passes zero-trap + !sealable +
scorer-rival survival).** Canonical numbers: **8-car s1-5 769/1/63.81;
s6-10 769/1/63.78; s11-15 770/0/63.78; 4-car 330/0/61.84; 1v1
110/0/60.62; slow 28/0/104.25.** vs the round-58 champion: 8-car
crashes 2 vs 6 over 15 seeds at mv -0.22 uniform; h2h places won on
ALL THREE seed sets (4.483/4.481/4.465) at 15-seed crash parity 5-5;
4car/1v1/slow all faster, all crash-free. Residual crashes (2/15
seeds): lemans s4 (smom-invisible funnel) + hairpin s10 (strategic,
doomed 7+ rounds out) -- both oracle-classified beyond rollout reach.
Self-tie verified: inert_probe 27/27 move-identical + 22-track
bench-vs-cache exact tie; caches re-seeded from the r62 gate's AI1
columns. Both AI bodies identical again; AI1 free to diverge.

(Superseded: round-58 champion 47b74c8, canonical 768/2/64.04;
round-54 C+2 champion 4df1866, canonical 767/3/64.04; round-44
champion b0f64c5, canonical 767/3/64.07; round-40 DJS-only champion
9ad009b, canonical 767/3/64.06.)

## Rounds 55-57: the queue-box class cracked (candidate in gates)

The remaining crash class was named in round 44 ("a body takes the escape")
and this arc finally REPRODUCED it in-sim. Story, laws and tools:

- **R55 (wide DJS trigger, AI1_DJS_SPD2=49): byte-inert alone, KEPT as
  enabler.** Landing spd^2 >= 49 fires on 16.3% of moves (spd_rate.py;
  silverstone 28.8%, sprint/triangle 0%) yet 27/27 probe races were
  move-identical: under the champion's greedy-rival sim NO death verdict
  fires anywhere -- trigger timing was never the frontier, sim fidelity was.
- **LAW (cost a day): `-Dai.debug.djs` is Boolean.getBoolean -- it MUST be
  `-Dai.debug.djs=true`.** The bare flag silently disables printing; several
  "zero AIDBG events" reads were meaningless until this was caught via a
  SIM_TRACE that also failed to print.
- **Oracle tooling (the arc's permanent yield, all in scratchpad):**
  `--query-moves - -` is now INTERACTIVE (stdin/stdout, one JVM serves
  sequential queries; ~18s reachability once) and each reply carries a
  9-candidate mask in Direction order (F finish / X illegal / B body /
  D reach-dead / A alive). Drivers: oracle_roll.py (verify mode = roll the
  real scorer as every car's policy and diff vs the log -- validated EXACT
  MATCH; cand mode = per-candidate fate of a mover at any log move),
  policy_matrix.py (replicates any cheap sim policy offline via mask
  queries), board_at.py (board + candidate classification at any log move),
  crash_scan.py (find crashed players in logs), champ_logs/ (round-54
  champion move logs, 27 races). This kills the guess-build-replay loop:
  policies are DERIVED offline, only the winner gets built in Java.
- **Doom mechanics of the three covered champion crashes** (board_at +
  oracle cand): silverstone s6 = one-cell certified corridor (83,117), p2
  claims it one move early, the "open" (83,118) is segment-illegal, 7
  dead-states -- all 9 fatal at m161, doom entered between m145 and m153.
  hungaroring s6 = same corridor-queue shape (8 dead + 1 body at m197).
  zandvoort s7 = empty-track doom (every candidate reach-dead by m140) --
  entered a certified-dead corridor rounds earlier.
- **Oracle verdicts: 2/3 saveable at wide-trigger points within horizon 3**
  (silverstone m145: chosen W dies r2, brake N survives t=62; hungaroring
  m181: chosen W dies r2, SIX survivors) -- only the rival model blocked
  the saves. zandvoort not saveable at m140+ (all dead).
- **Policy matrix (the decisive artifact): both boxes need BOTH terms.**
  Rival policy vs (chosen / survivor) on both sites:
  greedy: alive/alive + alive/alive (misses both boxes -- vacates lines);
  gmom (greedy, tie->faster): catches silverstone only;
  shape (ttf+trap ladder): catches hungaroring only (corridor claim);
  **smom (ttf + trap, tie -> HIGHER landing speed): DEAD/alive on BOTH --
  matches the real-scorer reference on all four cells.** The momentum
  tie-break models the scorer holding speed down the racing line; the trap
  term models it claiming one-lane corridors (ttf gain > trap 2.0). The
  r56 lexicographic selfMove-as-rivals arm (tier FIRST) is the opposite
  failure: refuses the corridors the real scorer claims -- probed inert,
  reverted same day.
- **R57 build: `rivalMoveOverState` (smom) behind exactRivals in the DJS
  rollout only** (certification vetoes keep greedy rivals; exactSelf
  unchanged -- one variable). AI1 DJS call = (true, true, true). In-game
  replays: silverstone s6 saved (ONE intervention, m145 W->N, 0 crashes),
  hungaroring s6 saved (m181 W->NW, 0 crashes). 27-race probe: 6/27
  diverge; crashes 3 -> 1 -- ALL champion crashes saved including
  zandvoort s7 (intervention at m124, BEFORE the oracle's doomed window:
  the new sim sees the danger while escapes still exist); 1 NEW crash
  (hungaroring s7, an early m29 switch reflowed the race; slow queue death
  at m413 -- board_at: all 9 candidates reach-dead, the zandvoort doom
  class, formed at low speed below every trigger).
- **R57 8car screens (3 independent seed sets, vs cached champion): the
  biggest crash gain since DJS itself, at DEAD-FLAT pace.**
  | seed set | R57 f/c/mv | champion f/c/mv |
  |----------|------------|-----------------|
  | 1-5      | 768/**2**/64.04 | 767/3/64.04 |
  | 6-10     | 768/**2**/64.00 | 765/5/63.99 |
  | 11-15    | 768/2/63.99 | 770/**0**/64.01 |
  | total    | **c=6** f=2304 | c=10 f=2302 |
  Sites: silverstone/interlagos/zandvoort crashes GONE (s6-10 3->0);
  hungaroring 2->3 across sets (s1-5 1->0, s6-10 1->1 wash, s11-15 0->2
  NEW -- its one-lane corridor absorbs the reflow risk); lemans/zigzag/
  hairpin slow-class untouched. The s11-15 regression is the round-52
  warning shape but here the 15-seed total is strongly net (-4 crashes,
  +2 finishers) rather than reversed. smom sim cost: NEGLIGIBLE (~17
  min/set cached, same as champion).
- **R57 FULL BATTERY: PASSED, the strongest gate of the campaign** --
  wins or ties EVERY stage, no stage worse:
  | stage | R57 (AI1) | champion (AI2) |
  |-------|-----------|----------------|
  | 8car s1-5   | 768/**2**/64.04 | 767/3/64.04 |
  | 8car s6-10  | 768/**2**/64.00 | 765/5/63.99 |
  | 8car s11-15 | 768/2/63.99 | 770/**0**/64.01 |
  | h2h s1-5    | **4.491** c=**2** | 4.509 c=3 |
  | h2h s6-10   | **4.486** c=**2** | 4.514 c=5 |
  | 4car s1-5   | 330/**0**/61.98 | 329/1/61.97 |
  | 1v1 s1-5    | 110/0/60.95 (exact tie) | 110/0/60.95 |
  | slow        | 28/0/104.39 (exact tie) | 28/0/104.39 |
  8car crashes 6 vs 10 over 15 seeds; h2h wins BOTH axes on BOTH sets
  (margins beat even the C+2 promotion battery); 4car save; sparse/slow
  untouched. Better than the round-40 DJS gate (net -5) on breadth AND
  the h2h margin. PROMOTED round 58 (user-approved 2026-07-26) -- see
  the champion header.
## Round 59 (AI1, in gates): real-scorer rivals for the slow class

The round-58 champion's ENTIRE residual (6 crashes/15 seeds) is the SLOW
class (spd^2 <= 25): queue pockets + endgame scrums. Oracle census of all
six: hungaroring s7/s12/s13 = the (64,115) pocket (doom-entry m389-class,
saveable, chosen dies r2-3 with TWO survivors); lemans s4 = start-funnel
doom entered at m63 through a TRAP-0 state (1-ply ladder reads 3 open,
all secretly dead in 2-4 rounds; only visible at horizon 4-5); zigzag s4
and hairpin s10 (race-end scrum at spd^2~2) unclassified in depth.

KEY MEASUREMENT (policy_matrix, horizon 4-5): the smom proxy FAILS the
slow class both ways (misses the pocket death AND falsely kills the good
escape) -- dense slow traffic drifts beyond any 2-term proxy within ~2
rounds. Real-scorer rivals + selfMove me ("orivals") flags BOTH slow
dooms with survivors intact => recursion is the only faithful world.

BUILD: scorerMoveOverState -- installs the sim board into the live
Player objects (processQueries pattern), runs the rival's OWN scorer
with recursive machinery suppressed (IN_SCORER_SIM static guards at the
solver / certified tie-break / DJS in both bodies), restores in a
finally. simOutcome gains scorerRivals: nearest AI1_SCORER_MAXRIVALS=3
rivals within Chebyshev AI1_SCORER_NEAR=10 roll via the real scorer.
AI1's DJS call: slow-class fires (landing spd^2 < 49) use scorer-rivals
at AI1_DJS_SLOW_ROUNDS=5; fast fires keep smom at 3 (proven, untouched).

SITE RESULTS: hungaroring s13 saved at exactly the oracle's doom-entry
(m389 NONE->E, one intervention, 0 crashes); s7 + s12 saved; the whole
pocket class is GONE. lemans s4 NOT saved (its trap-fires correctly say
"no survivor"; the m63 entry is trap-0 so nothing fires -- KNOWN GAP).
zigzag s4 / hairpin s10 not saved.

GATES (round 59, ALL PASSED, never worse on any stage): probe 2/27
diverge (the s7 save + a crash-neutral lemans-s3 funnel flip). 8car:
s1-5 EXACT tie 768/2/64.04; s6-10 768/2/63.99 vs 768/2/64.00 (s7 saved,
monaco s7 NEW -- see below); s11-15 **770/0/64.01** vs 768/2 (both
pocket crashes saved, the perfect set). 15-seed c=4 vs 6 at flat pace.
h2h: s1-5 exact parity 4.500/4.500 c=2/2; s6-10 4.501/4.499 (noise)
c=1 vs 2. 4car/1v1/slow: EXACT ties (330/0, 110/0, 28/0).

The monaco s7 relocation (oracle-classified): p8 squeezed in the tunnel
narrows (x66-71,y75-76) at speed ~5, TOTALLY boxed by m480 (all 9
segment-illegal -- board_at's "open" cells were wall-cut illusions,
only the oracle mask sees segment legality), doomed before m472. Same
slow-class family (trap-0 funnel entry), walk-back pending -- a
round-60 target alongside lemans s4 / zigzag s4 / hairpin s10.

ROUND-60 LEAD (measured, do NOT build a blanket trigger): slow+crowd2
fires 218/race (crowd_rate.py) -- far too hot for scorer rollouts. The
lemans entry needs a SELECTIVE escalation, e.g. run the cheap smom
rollout first and escalate to scorer-rivals only when its final state is
fragile (died OR final tier <= 1). Escalation rate unmeasured.

## Round 60 (AI1, in gates): smoke-test escalation for trap-0 entries

Census of the round-59 residual (oracle walk-backs, per site):
- **lemans s4**: last save m63, death 3-5 rounds out; smom rollout MISSES
  it (says alive t=55) -- only scorer-rivals see it. NOT caught by r60a;
  needs a future escalation signal (final-state fragility?).
- **zigzag s4**: last save m102, chosen W dies @r4 (real) but even the
  CHEAP smom-5 rollout flags it (@r1, me-proxy walks in faster); one
  survivor SW (swing wide before the kink). The entry is trap-0 via
  vacate-optimism: W's ladder read roomy at m102, actual 1-ply count 0
  at m110. => Only a TRIGGER was missing.
- **hairpin s10**: doom >= 7 rounds deep (all fatal at m98, best @r6,
  race is ~17 rounds total) -- STRATEGIC class, beyond any rollout.
  ACCEPT.
- **monaco s7**: tunnel squeeze, totally boxed by m480 (all 9
  segment-illegal; board_at's "open" cells were wall-cut illusions --
  only the oracle mask sees segment legality), doomed before m472,
  deep-commitment class like hairpin. ACCEPT (walk-back not exhausted).

R60a BUILD (AI1): trap-0 slow moves (spd^2 < 49, trap < 0.5 -- today's
no-fire gap) get a CHEAP smom-5 smoke test; a smom death ESCALATES to
the scorer-rival rollout which re-verdicts the chosen and gates any
switch (smom false alarms filtered before they can perturb -- monaco s1
control: 1 escalation, scorer said alive, no switch). Replays: zigzag
s4 SAVED at exactly m102 (one escalation, SWITCH SW, 0 crashes);
lemans s4 unchanged (smom miss, expected); hungaroring/coil quiet.
Escalation rate 0-1/race => cost nil.

**R59+R60a GATES vs the round-58 champion: PASSED CLEAN, never worse.**
Probe 3/27 diverge (2 saves + crash-neutral lemans s2/s3 flips). 8car:
769/**1**/64.05, 768/2/64.00, **770/0**/64.01 vs 768/2 x3 => 15-seed
c=3 vs 6 at flat pace -- s1-5 c=1 is the best s1-5 line of the
campaign. h2h: 4.500 c=1 vs 4.500 c=2 and 4.505 c=1 vs 4.495 c=2
(places parity/noise-band, crashes 2 vs 4). 4car 330/0, 1v1 110/0,
slow 28/0: EXACT ties. The three residual crashes are all classified
beyond-rollout classes: lemans s4 (smom-invisible funnel, needs a
future escalation signal), monaco s7 (tunnel squeeze, doomed 4+ rounds
deep), hairpin s10 (strategic, doomed >= 7 rounds deep). PROMOTION-READY
stack (r59 commit 11b2297 + r60a); awaiting the user's word.

## Round 61 (AI1, in gates): rival-conditional trap relief (solo pace)

The lemans-s4 fragility idea died by measurement (smom rollouts end
tier=3 everywhere -- no cheap escalation signal exists; lemans s4 joins
monaco s7 / hairpin s10 as accepted residuals). Pivot to PACE: the
r57-60 reflows created a NEW equilibrium, so the round-47/48 pace
decomposition was re-run (pace_forensic on fresh champion logs +
patch_comp_dump re-applied, comp dump now permanent in source):
- monaco s1 now shows a 26-move ROOMY pool (was negligible), with a
  smoking-gun FIXED POINT: five different cars concede the identical
  1 ttf at (116,46) v(-4,6). The comp dump shows the deep search itself
  PREFERS the faster SW line (cost 65 vs 66) and the TRAP LADDER alone
  (2.0, one-safe-successor thread) overrides the certain gain -- with
  no rival anywhere near. The ladder is rival-blind in its price.
- Secondary leak at the same state: `unc` fires 11.5 for SOME cars
  (predicted-world dependent) on the solo thread -- round-62 candidate
  with the same emptiness certificate. One variable at a time.

R61 BUILD (AI1): waive L1/L2 trap (0-safe keeps 50) when no live rival
is within Chebyshev AI1_TRAP_SOLO_R=16 of the landing -- max per-axis
closure is |v|+1 <= 13/round, so the thread is uncontestable for its
consumption window; the map's reach-certification suffices solo.

**R61 GATES: PASSED -- the first simultaneous pace+crash gain of the
campaign, and the pace gain SCALES WITH SOLITUDE (mechanism-confirming):**
| stage | r59+60+61 (AI1) | champion r58 (AI2) |
|-------|-----------------|--------------------|
| 8car s1-5   | 769/**1**/**63.98** | 768/2/64.04 |
| 8car s6-10  | 768/2/**63.94** | 768/2/64.00 |
| 8car s11-15 | **770/0/63.93** | 768/2/64.00 |
| h2h s1-5    | 4.500 c=**1** | 4.500 c=2 |
| h2h s6-10   | 4.502 c=1 (noise) | 4.498 c=1 |
| 4car        | 330/0/**61.85** | 330/0/61.98 |
| 1v1         | 110/0/**60.62** | 110/0/60.95 |
| slow        | 28/0/104.39 (tie) | 28/0/104.39 |
Probe: 11/27 diverge, ZERO crashes, every divergent race SHORTER
(lemans -3/-3/-4, monaco -2/-3/-5, zandvoort -1 x3); short dense tracks
inert. mv -0.06 uniform on all three 8car sets; 4car -0.13; 1v1 -0.34
(solitude scaling: more solo running = more relief); slow ties (narrow
serpentine queues are never solo within 16). 15-seed crashes 3 vs 6.
The comp dump (-Dai.debug.comp) is now permanent gated instrumentation.

## Round 62 (AI1, gate-clean): certified UNC override -- the unc pool won

62a (descent-scaled range bound on the converging-opponent gate) probed
BYTE-INERT vs r61 and was reverted the same hour. The counterfactual on
the r61 equilibrium still showed `unc` holding the largest pool (monaco
s1: 50 ttf ceiling, deep search agreeing 48/48; lemans 9). 62b takes it
the way rounds 49-53 proved it must be taken -- with a PROOF, not a
predicate: pay the surcharge everywhere EXCEPT where a strictly faster
(raw ttf) candidate wins the unc-free score comparison AND has zero
trap, is not sealable, and SURVIVES the round-59 scorer-rival rollout at
the slow horizon (the proof round 52 lacked; solo flips have empty
scorer sets so their proofs cost nothing). patch_r62_uncover.py,
first-occurrence anchors, AI1 only.

**GATES: the biggest pace gain since the depth-2 search, at the best
crash floor ever, seed-set law satisfied the hard way:**
| stage | r59+60+61+62 (AI1) | champion r58 (AI2) |
|-------|--------------------|--------------------|
| 8car s1-5   | 769/**1**/**63.81** | 768/2/64.04 |
| 8car s6-10  | 769/**1**/**63.78** | 768/2/64.00 |
| 8car s11-15 | **770/0/63.78** | 768/2/64.00 |
| h2h s1-5    | **4.483** c=**1** | 4.517 c=3 |
| h2h s6-10   | **4.481** c=4 | 4.519 c=1 |
| h2h s11-15  | **4.465 c=0** | 4.535 c=1 |
| 4car        | 330/0/**61.84** | 330/0/61.98 |
| 1v1         | 110/0/**60.62** | 110/0/60.95 |
| slow        | 28/0/**104.25** | 28/0/104.39 |
8car 15-seed: crashes **2 vs 6**, mv **-0.22 uniform** on all three
sets. h2h: the s6-10 c=4 (monaco 2 + hungaroring 1, on tracks where
places were WON 4.38) triggered the third-set rule -- s11-15 came back
4.465 **c=0**; 15-seed h2h places won on ALL THREE sets at crash
parity 5-5. 4car/1v1/slow all faster, all crash-free (first slow-set
movement in many rounds, -0.14). Probe: 18/27 diverge, zero crashes,
every long-track race shorter (lemans -18/-9/-4, monaco -17/-11/-8,
hungaroring -17/-11).

## Round 65 (AI1, in gates): pack-gated deep escalation

The hairpin-s10 walk-back CONTINUED past the all-fatal m98: the save
exists at m90 with a 7-ROUND commitment (three candidates FINISH @r6
while the real chosen SE dies @r7 -- the scorer accelerated to v(8,1)
into the pack hairpin). policy_matrix at horizon 8: orivals reproduces
it exactly (chosen DEAD@r7, both survivors alive t=1); smom misses the
death but ends FRAGILE (final tier=1) -- the escalation signal (which
was dead at lemans but lives here). Escalation-rate samples
(esc_sample.py): hairpin 17%, monaco 20% (too hot unedited),
silverstone 0% => PACK GATE: escalate only with >= AI1_DEEP_PACK=3
rivals within Chebyshev AI1_DEEP_PACK_R=10 of the landing (the doom
class lives in packs; monaco's fragile hit was a solo tunnel). Start
grids are slow => wide trigger off => no deep fires there.

BUILD (AI1): simOutcome gains an outFinalTier out-param (overload, no
caller churn). Fast fires with the pack: cheap smom pre-screen at
AI1_DEEP_HORIZON=8; dead-or-fragile => dangerJointSearch with
scorer-rivals at horizon 8 (re-verdict gates any switch). hairpin s10
replay: TWO escalations, m82 correctly kept (scorer alive), m90 DIES ->
SWITCH W simT=0 (the finish-in-sim line), 0 crashes.

**GATES: PASSED, never worse on any stage.** Probe 4/27 diverge, zero
crashes (hairpin +2 / zandvoort +3 move reflows, two same-length
silverstone flips). 8car: s1-5 tie 769/1/63.81; s6-10 **770/0/63.79**
(hairpin saved -- the set is PERFECT); s11-15 tie 770/0/63.79. h2h:
4.502/4.498 c=1/1 parity; 4.499/4.501 c=**0**/1. 4car/1v1/slow: EXACT
ties. **15-seed residual = ONE crash (lemans s4, the provably
invisible funnel).** 2309 finishers of 2310 possible.

## Round 64: the certified-lane instrument is EXHAUSTED (closed negative)

Fresh counterfactual on the round-63 champion (comp_r64_*.err): unc
residual 59/16/23 ttf (monaco/lemans/interlagos), rob GREW to 28 on
monaco (25 flips, search agreeing 24/25), spread ties 13/23/22. Built
the certified ROB override (patch_r64_roblane.py, the exact r62 lane
with the bonus added back on both sides): **byte-INERT on all three
pool tracks** -- every rob-flip's fast candidate is refused by the
proof stack (trap != 0 near rivals / sealable / scorer-rival death).
REVERTED same hour (git checkout, uncommitted).

LAW: after rounds 61-62 took everything the proof stack can certify,
the ENTIRE remaining soft-term pool (unc residual + rob + spread ties,
~100 ttf/seed across the big tracks) is certification-refused = the
round-47 knife-edge frontier, now confirmed at the level of the
strongest proof owned (scorer-rival rollouts). Taking more pace needs a
STRONGER PROOF than the campaign possesses, not another lane. Do not
add lanes; the instrument is done.

Remaining open frontiers (for future rounds): (a) the strategic doom
class (hairpin s10 / lemans s4, commitment 5-7+ rounds) -- would need
horizon-7+ rollouts at some rare affordable trigger; hairpin's
last-save move is UNKNOWN beyond m98 (walk-back stopped at all-fatal);
(b) external-opponent value (h2h vs humans/weaker AIs) -- unmeasurable
in self-play; (c) anything requiring game expansion is excluded by
standing instruction.

- **The residual class is ONE localized pocket: hungaroring (64,115).**
  All three new-equilibrium casualties (s7 p5, s12 p8, s13 p5 -- found by
  r57_hung_forensic.sh replays) die at the SAME cell with the SAME
  approach (59,116)->(62,116)->(64,115) at spd^2 10/9/5, all 9 candidates
  reach-dead at the end (board_at). A slow-speed doom pocket below every
  trigger (wide needs spd^2>=49; trap fires too late). ROUND-58 TARGET:
  oracle cand walk-back on this pocket to find the doom-entry move and a
  trigger shape for the slow class (zandvoort s7's family). The pocket is
  a consistent attractor of the new equilibrium, so it should reproduce
  deterministically for the forensic.
- **Idea D (certified isolation sprint): CLOSED NEGATIVE by measurement**
  (iso_pool.py, champ_logs): pace lost while spatially isolated from every
  rival is ~0.2 ttf/race at Chebyshev >= 20 and ZERO at >= 25 -- in-race
  fields never spread enough; the 1.10% solo-caution headroom exists only
  in literally-solo races. Do not build.

Mechanism (in both AI bodies, helpers shared):
- Per-candidate `trapByDir[d]` records the trap ladder (d2SafeCount-based
  50/2/0.5/0 penalty) during the normal scoring loop.
- After the sealGuard, if the chosen landing has `trapByDir >= 0.5`
  (<= 2 safe successors), `dangerJointSearch` runs: roll the joint game
  `AI1_DJS_ROUNDS = 3` rounds forward on a DETACHED board (`simOutcome`),
  every car greedy min-turnsToFinish (`greedyMoveOverState`), move-order
  aware (first simulated round covers only players after `game.subgamestate`
  — the array index of the mover). Returns my ttf, or -1 if I get boxed.
- **STRICT SURVIVAL-ONLY ASYMMETRY: override the scorer's pick ONLY if it
  dies in-sim AND another candidate survives (pick best sim-final ttf);
  a surviving pick is always kept.** This is why it beat the equilibrium
  law where the rejected 2026-07-14 foresight sim (fs1) netted zero: fs1's
  warning-based re-picks caused equal evasion crashes; survival-only
  switching cannot fire on a line that was actually fine.
- rounds=4 probe: no additional gain (zandvoort s7 is greedy-me model
  error, not horizon). Kept 3.

Full-gate record vs prior champion (all logs in the scratchpad, djs_*.log):
- 8-car 10 seeds: c=7 vs 11 (hungaroring 0 vs 5; coil s6-10 0->1
  relocation); pace composition-only.
- h2h mixed 22 tracks x 5 seeds: place parity 4.502/4.498, crashes 3 vs 7.
- 4-car: s1-5 self-tie; s6-10 c=1 vs 2 (a sparse SAVE). 2-car: tie.
- slow: serpentine2 0->1 relocation; serpentine/spiral/cog +0.0.
- Net -5 crashes across all modes at equal pace.

## The user-approved 5-lever campaign ("Let's do 1-5")

1. **Launch policy — FALSIFIED, closed unbuilt.** Champion has ZERO
   crashes in rounds 1-8 (11 crashes over 10 seeds, earliest round 9);
   pack-density decay does not discriminate crash seeds from clean seeds
   (crash seeds often LESS dense). Tools: start_congestion.py,
   density_compare.py.
2. **Pace headroom — DONE, the strategic number.** Champion 8-car moves =
   exact map optimum + 6.35%: solo caution 1.10% (solo champion EXACTLY
   optimal on 13/22 tracks; residual: monaco 3.6%, zandvoort 2.2%, coil
   1.7%) + **TRAFFIC 5.25%** (sinks: lemans +11.8%, sprint +10.0%,
   triangle +8.6%, hairpin +7.7%, monaco +6.9%). All future racing value
   lives in the traffic gap. Tools: headroom.py + reach_*.bin dumps
   (22 tracks, in scratchpad) via the game's `--dump-reach`.
3. **Gate-threshold joint tune — CLOSED, negative, definitive.** The six
   never-tuned thresholds were refactored into AI1_* constants (b86339b,
   byte-identical proven) and coordinate-descent tuned vs a mixed-field
   proxy on the traffic sinks. Best (MID 0.72 / SPD 3 / VACATE 3.5,
   proxy 4.287 vs 4.500) was REJECTED by the full gate: h2h over all 22
   only 4.484 vs 4.516 (proxy = track-selection overfit), 8-car crashes
   14 vs 11. Constants surface (multipliers AND thresholds) is now
   provably exhausted. LESSON: tuner objectives must span all 22 tracks
   or carry a full-gate-shaped holdout.
4. **Danger joint search — SHIPPED, PROMOTED (this champion).** See above.
5. **Endgame solver — NOT STARTED (next).** Plan: memoized exact minimax
   over joint states when <= 2 rivals remain near the finish, depth 6-10;
   extends the V1 endgame seal (which is 1-ply and proven inert vs equal
   AIs); value is vs humans/weaker AIs, so verify no self-play regression
   + h2h, don't expect bench gains.

## Immediate pending work (in order)

1. **Coil s6 relocation forensic — DONE (2026-07-21+), verdict: ACCEPT,
   pure reflow.** Replay shows the only DJS divergence in the race is p6's
   survival switch at (9,45), other side of the track, 14 p8-turns before
   the death. p8's own kill is the ancestral trigger-too-late class: trap
   ladder 0.0 for 11 turns at speed 6-7, first flagged landing (50,70) ->
   DJS "DIES in-sim, no survivor" (all 9 candidates dead), forced moves to
   the wall. DJS innocent; it even diagnosed the death 5 moves early.
2. **serpentine2 slow relocation forensic — DONE, verdict: ACCEPT (DJS
   collateral, user-endorsed aggression), fold into item 4.** Corrected
   story after testing the pre-DJS champion on the same default grid
   (NO crash): BOTH sim death-verdicts in the DJS race were FALSE
   (greedy-me model error) — p6 "DIES" would have lived on its old line;
   p7 "no survivor" threads through pre-DJS. The false verdict made p6
   switch to (113,114), and that rescue body landed in p7's speed-10
   braking corridor -> p7's real box. A switch safe for the switcher that
   killed a rival = collateral aggression (p6 gained; h2h gate showed
   place parity + halved crashes; round-40 gate priced it at net -5).
   LESSON: DJS false-death verdicts don't self-harm (survival-only
   asymmetry) but DO perturb the equilibrium via unnecessary switches —
   sim fidelity is the shared root with item 4.
3. **Lever 5 (endgame solver) — DONE, SHIPPED (round 43, commit 3895855,
   AI1 only).** 1v1 exact memoized paranoid minimax (trigger: sole live
   rival + both within AI1_EG_ETA=12 of the finish; AI1_EG_DEPTH=10
   rounds; AI1_EG_NODES=50_000 -- 200k ran the 1v1 bench ~2x long on
   UNPROVABLE positions, and real proofs are shallow forcing lines, 50k
   smoke byte-identical). Acts ONLY on guaranteed wins (cross first /
   rival forced to crash); unproven -> normal scorer. Gate: 1v1 duel
   place parity 1.500/1.500 crashes 0v1 (all duels position-decided vs an
   equal AI, as the plan predicted); 8-car self-play bit-inert (f=767 c=3
   rows identical); h2h 4.498/4.502 c 3v4 (unchanged). Smoke: chains
   proven wins when ahead (hairpin 4 forced moves), silent when behind.
   Value target = humans/weaker AIs, unmeasurable in symmetric benching.
   ALSO SHIPPED THIS SESSION (round 42, commit 979084f): the sealable()
   selfByIndex off-by-one fix, AI1 only -- full gate net -5 crashes at
   equal pace (4-car 10-seed c=1 vs 4 both sets confirmed, 2-car 0v1,
   slow 0v1 incl. the serpentine2 DJS-collateral save; 8-car wash, h2h
   parity). AI1 = DJS + sealfix + endgame solver; AI2 = DJS champion
   (sealable bug-compatible via selfByIndex=true). PROMOTION of both into
   AI2 is a pending user decision -- promotion = flip AI2's selfByIndex
   flags to false + add the solver trigger to AI2's method top.
4. Ancestral singles (silverstone s6, zandvoort s7, lemans s4/s10-class,
   chicane s3, zigzag s4, coil s6 above): need better sim fidelity
   (greedy-me != real-me is the known model-error class) or earlier
   triggers + longer horizon. The trigger misses shapes whose trap ladder
   stays 0 until all alternatives are dead (silverstone s6 / coil s6 /
   serpentine2 p7 = speed 7-10 into a corner). DESIGN FACT: the
   survival-only asymmetry makes the DJS trigger a pure COST gate —
   broadening it (even to every move) cannot reintroduce fs1-style
   false-alarm evasions; the frontier is sim fidelity + horizon, not
   trigger safety.

AIDBG instrumentation (turn dump `-Dai.debug.player=N` + DJS-death events
`-Dai.debug.djs`, both bodies, prints-only, off by default) is now IN the
champion source (committed) — run_debug.py uses both; seed 'none' replays
the default grid.

## Traffic-pace frontier DECOMPOSED — round 47 (lever 2 forensic)

Per-move forensic (scratchpad/pace_forensic.py, NO Java/bench: reach_*.bin
dump gives exact velocity-aware ttf; each move should cut ttf by 1; a move
cutting it by <1 lost that fraction). For each lost move it decides whether
the fastest next cell was rival-BLOCKED (irreducible), free-but-KNIFE-EDGE
(<3 open 1-ply escapes -> the pace/crash frontier: taking it converts to
crashes, proven), or free-and-ROOMY (>=3 escapes -> genuine over-caution,
the only safely-recoverable pool). Results (champion, seed 1, finishers):
- lemans (biggest sink, +11.8%): 68 lost = 16 irreducible + 38 knife-edge
  frontier + 14 roomy over-caution.
- sprint (+10.0%): 11 lost = 9 irreducible + 2 roomy + 0 frontier.
- triangle (+8.6%): 11 lost = 11 IRREDUCIBLE, 0 recoverable.
CONCLUSION: ~90% of the 5.25% traffic gap is irreducible (a rival is
genuinely in the fast cell; someone must yield) or knife-edge frontier
(the memory's proven pace->crash conversion). The safely-recoverable
over-caution pool is SMALL (~14 moves/race on the worst track, ~1%
campaign-wide) AND every slice of it is justified: the very-open slice is
START-GRID idling (NONE at tick 1 from standstill -- pileup avoidance,
lemans start boxes are real, state_probe confirmed greedy=64 vs chosen
NONE=65); the rest is room=3-5 mid-race where 1-ply openness exceeds the
champion's 4-ply foresight, which prior rounds PROVED load-bearing
(removing foresight crashes). So the heuristic is near the equilibrium
limit on BOTH axes now (crashes AND traffic pace). The genuine remaining
lever for the traffic gap is the SAME as for the crash floor:
MULTI-AGENT COORDINATION (predict rival yields to cut mutual detours) --
the learned-AI direction (pyrace), where RL previously did not beat
greedy. Tools: pace_forensic.py, state_probe.py (both in scratchpad,
reusable on any track+seed with a reach dump).
- **PROBE RUN & REJECTED (round 47): start-grid anti-idle.** Added an AI1
  override -- from a standstill, if the scorer idles (NONE) while a faster
  advance lands clear of predicted AND live rivals with >=6 open 1-ply
  escapes, take the advance. It NEVER FIRED: all-AI1 races are MOVE-IDENTICAL
  to the champion on all 5 sink tracks (lemans/sprint/triangle/hairpin/
  monaco). Every start-grid NONE has a rival predicted into the advance ->
  the idle is real pileup-avoidance, not gratuitous. Reverted (patch_antiidle.py
  archived). This is the CODE-LEVEL confirmation of the forensic: the
  heuristic has no recoverable traffic pace. BOTH axes (crashes, pace) are
  now at the equilibrium limit; the only lever left is learned multi-agent
  coordination.

## VERDICT on the rounds 48-53 pace campaign (read this first)

The `unc` pace lever is **REJECTED**. It is real (~0.7% faster, consistent
across every seed set) but it is NOT free: a third independent seed set
(11-15) broke the tie decisively against it —

| seed set | round 52 crashes | champion crashes |
|----------|-----------------:|-----------------:|
| 1-5      | 7 | 3 |
| 6-10     | 3 | 5 |
| **11-15**| **10** | **2** |
| **total**| **20** | **10** |

It DOUBLES the crash rate over 15 seeds. The seeds 6-10 result (3 vs 5,
which looked like it beat the champion) was pure luck. **LAW: two seed sets
are NOT enough when they disagree — a 5-seed crash delta of +/-2 is noise,
and a candidate that wins one set and loses another must go to a third set
before any conclusion.** This nearly promoted a crash-doubling regression.

CONSEQUENCE: the `uncertified` surcharge IS load-bearing insurance despite
its genuine coherence defect (it fires on speeds the map certifies). The
counterfactual forensic was RIGHT that it overrides the deep search 51/51 —
but the deep search is OPTIMISTIC about traffic, and this surcharge is
precisely what pays for that optimism. Localising a term as "the thing
costing pace" does NOT mean the term is wrong.

**SURVIVOR: C+2** (certified pace tie-break + exact-self rollout) — the only
candidate of the whole campaign that improves BOTH axes, confirmed on three
independent seed sets:

| seed set | C+2 f/c/mv | champion f/c/mv |
|----------|------------|-----------------|
| 1-5      | 767/**3**/64.04 | 767/3/64.07 |
| 6-10     | 765/**5**/63.98 | 765/5/64.03 |
| 11-15    | 770/**0**/64.01 | 768/2/64.06 |
| total    | **c=8**    | c=10 |

Never worse on any set, faster on all three, and c=0 on the very seed set
where the `unc` lever collapsed (c=10 vs 2). Its safety comes from
COMPOSITION, not from cutting caution — which is why it survives where every
caution-reduction arm (A, B, 52, 53) failed.

**FULL PROMOTION BATTERY: PASSED, CLEAN ON EVERY STAGE** (c2_battery.sh):

| stage | C+2 (AI1) | champion (AI2) |
|-------|-----------|----------------|
| 8-car seeds 1-5   | 767/**3**/64.04 | 767/3/64.07 |
| 8-car seeds 6-10  | 765/**5**/63.98 | 765/5/64.03 |
| 8-car seeds 11-15 | 770/**0**/64.01 | 768/2/64.06 |
| h2h places s1-5   | **4.430** c=**3** | 4.570 c=4 |
| h2h places s6-10  | **4.484** c=**4** | 4.516 c=6 |
| 4-car s1-5        | 329/1/61.97 (exact tie) | 329/1/61.97 |
| 1v1 s1-5          | 110/0/60.95 (exact tie) | 110/0/60.95 |
| slow synthetics   | 28/**0**/104.39 | 28/0/104.46 |

h2h is the decisive stage the 8-car bench cannot see (insurance-premium law:
caution can cede PLACES at equal crashes) — C+2 wins places AND crashes on
BOTH seed sets. 4-car and 1v1 are exact ties: the certified tie-break
correctly never fires in sparse fields, so the seal guard and the 1v1 solver
are untouched.

**PROMOTED round 54 (user-approved 2026-07-25) via `patch_promote_c2.py`:**
mirrored the scoreNSByDir/poTByDir bookkeeping + override block into the AI2
body (second occurrence of each anchor) and flipped AI2's dangerJointSearch
call (false, false) -> (true, true), which also promoted the round-45
finish-vanish fidelity that had been AI1-only. Self-tie: inert_probe 27/27
INERT + 22-track bench-vs-cache tie. Caches re-seeded from the gate's AI1
columns via `extract_baseline.py <log> <json> 1`.

## Rounds 48-51: the traffic gap LOCALISED to two named terms

Round 47 concluded "no recoverable traffic pace". That was WRONG in one
respect and the correction is the most useful result since DJS: the pace
forensic measured the gap per MOVE but never asked WHICH SCORE TERM decided
it. Component-level attribution finds a real, broad, reproducible lever.

### New tooling (scratchpad, reusable on any track+seed — use these FIRST)
- **inert_probe.py** — the cheapest possible go/no-go for ANY AI1-only
  change: races an all-AI1 field and an all-AI2 field on the same
  track+seed and diffs the move logs (normalising the AI-kind field, which
  is embedded in every log line — diffing without that gives a 100% false
  divergence). Identical logs => the change is byte-inert; REVERT, never
  bench. `PROBE_SEEDS=6,7,...` env to pick seeds. Caught rounds 48 and 51
  in ~4 minutes each instead of a 40-minute gate.
- **patch_comp_dump.py** — injects a print-only per-candidate score
  breakdown into AI1 (gated `-Dai.debug.comp`): every scored candidate with
  cost/trap/cap/unc/ce/qb/spread/mom/rob + raw map ttf.
- **comp_forensic.py** — proportional blame per term for conceded pace.
- **comp_counterfactual.py** — THE decisive one. Deletes each term, re-runs
  the argmin, and measures the change in the WINNER's raw map ttf, i.e. the
  honest ceiling of what removing that term could recover. Also splits, for
  each flip, whether the deep search itself AGREED the faster cell was
  cheaper / was exactly TIED / was AGAINST it. Proportional blame
  over-attributes; always prefer the counterfactual.

### The measurement (5 traffic sinks, seed 1, ttf recoverable)
| term | lemans | monaco | sprint | triangle | hairpin | search verdict |
|------|-------:|-------:|-------:|---------:|--------:|----------------|
| unc    | 14 | 40 | – | – | 1 | AGREED 51/51 (overrode it) |
| spread |  8 | 10 | 13 | 9 | 6 | TIED 46/46, AGAINST 0 |
| trap   |  8 | 14 | – | – | – | agreed (load-bearing, leave alone) |

Both have COHERENCE defects, not tuning defects:
- **`spread`** (`opponentSpreadPenalty`, 0.3 within d2<=4 / 0.1 within
  d2<=9, per rival) is documented as a "tiny penalty ... breaks lateral
  ties", but its magnitude EXCEEDS the entire non-spread score spread in
  the decisions it decides (all < 0.3). It is not breaking ties, it is
  dominating them, and it outranks raw pace. Every flip is an exact
  costToFinish tie where it picks the SLOWER line.
- **`uncertified`** is gated on the flat `speed > AI1_BRAKE_SPEED` while its
  sibling `speedCap` respects the per-state certified budget
  (`widthBudget = max(5, certBudget) + d2SafeCount`). A term called
  "uncertified" fires on speeds the map CERTIFIES. Arm B
  (`patch_r49b_unc.py`, gate it on `overSpeed > 0`) is written and staged
  but NOT YET RUN — this is the largest untested lever on the board.

### Results so far
- **Arm A (`AI1_SPREAD_W = 0.0`, delete spread): the lever is REAL but
  uncertified.** 22 tracks x 10 seeds: mv 63.81/63.71 vs champion
  64.07/64.03 (~0.45% faster on nearly EVERY track, both seed sets) but
  crashes 15 vs 8, concentrated on the two most congested circuits
  (hungaroring 1->6, lemans 1->5). Lateral spacing IS load-bearing there.
  REJECT as-is; the constant `AI1_SPREAD_W` is a live tuning surface
  (intermediate weights never tried).
- **Arm C (certified pace tie-break, `patch_r49c_certpace.py`): NEUTRAL.**
  Keeps spread at champion strength but overrides toward a strictly faster
  line only when certified (weakly better on every non-spread term, zero
  trap penalty, not sealable, survives the DJS rollout). c=10 vs 8,
  mv -0.03/-0.05 over 10 seeds. The certification suppressed the pace
  (-0.26 -> -0.04) without buying back the safety.
- **Arm C + round 51 exact-self (the COMPOSITION): CRASH PARITY + pace.**
  22 tracks x 10 seeds: s1-5 f=767 c=3 mv=64.04 vs champion 767/3/64.07;
  s6-10 f=765 c=5 mv=63.98 vs 765/5/64.03. Crashes match the canonical
  champion EXACTLY on both seed sets, pace -0.03/-0.05. The exact-self
  rollout removed arm C's +1 crash on EACH seed set: idea 2 is inert alone
  but LOAD-BEARING in composition, confirming the false-death hypothesis
  (arm C certifies via simOutcome on a far broader state set than DJS's
  narrow trap trigger, so self-fidelity finally matters). Per-track wins at
  equal finishers: interlagos -0.3, hairpin -0.3, monaco/zandvoort/bigoval/
  chicane/slalom -0.1. Gain is small (~0.05%) but it is the FIRST
  crash-neutral pace improvement in many rounds.
- **Arm B (`unc` gated on `overSpeed > 0`): THE BIGGEST PACE LEVER IN THE
  CAMPAIGN, but uncertified.** 22 tracks x 10 seeds: mv 63.60/63.62 vs
  champion 64.07/64.03 = **~0.7% faster**, consistent across both seed sets
  (10x C+2's gain). Crashes disagree between seed sets: s1-5 c=7 vs 3
  (WORSE), s6-10 c=4 vs 5 (BETTER) => +3 over 10 seeds. Fires only on the
  big tracks the forensic predicted (lemans/monaco/interlagos/hungaroring/
  zandvoort), never on the spread-dominated short ones — an independent
  confirmation that the counterfactual attribution is measuring the right
  thing. Better trade than arm A (-0.44 pace for +3 crashes, vs -0.29 for
  +7) but still an uncertified caution cut.
- **Round 52 (`patch_r52_certunc.py`): the synthesis under test** — keep the
  surcharge as insurance and waive it only when certified on BOTH axes
  (speed inside the certified budget AND the landing survives the
  exact-self rollout). WARNING from the inert probe: it produced move
  counts IDENTICAL to arm B on all 7 diverging probe races, i.e. the
  survival check passes almost everywhere it fires, so it may reduce to
  arm B behaviourally. If the gate confirms that, the survival proof is too
  weak (a 3-round greedy-rival rollout rarely kills anything) and the
  certification needs a stronger/adversarial form, or the arm C-style extra
  conditions (trapPenalty == 0 and not sealable).
- **Round 52 RESULT (certified waiver, survival proof only): arm B pace,
  one crash better.** s1-5 f=763 c=7 mv=63.60 (BYTE-IDENTICAL to arm B --
  the survival check certified NOTHING); s6-10 f=767 c=3 mv=63.62, which
  BEATS the champion (765/5/64.03) on crashes AND finishers AND pace.
  10-seed: c=10 vs 8, mv -0.44. LAW: `simOutcome >= 0` is a WEAK proof --
  a 3-round rollout with greedy rivals almost never kills a landing. Use it
  only in conjunction (as C+2 does), never as the sole gate.
- **Round 53 (STRICTER certification: + trapPenalty == 0 + !sealable):
  REJECTED — dominated by round 52 on BOTH axes.** s1-5 f=765 c=5 mv=63.83
  (vs 767/3/64.07); s6-10 f=763 c=7 mv=63.79 (vs 765/5/64.03). 10-seed
  c=12 vs 8 and only -0.23 pace, i.e. MORE crashes AND LESS pace than the
  looser round 52 (c=10, -0.44). **KEY LAW: certification strictness does
  NOT trade monotonically against safety here.** Tightening the gate did not
  move along a pace/crash frontier — it reshuffled WHICH candidates get
  waived and relocated crashes to new sites (hungaroring 2, interlagos 1,
  zandvoort 3). Treat all of these arms as equilibrium RE-RANKINGS whose
  crash outcome is close to chaotic; the only robust result in the whole
  family is C+2's exact parity on BOTH independent seed sets. Do not spend
  more rounds hand-tuning certification predicates.
- **Round 50 (idea 4, predictedOpponentSteps 1->2): NEUTRAL, reverted.**
  Fires on 12/15 probe races (the ply>=1 predicted-cell test is a HARD SKIP,
  not a price, so this adds a ply-2 caution wall) but the gate is flat:
  s1-5 767/3/64.06 vs 767/3/64.07; s6-10 766/4/64.03 vs 765/5/64.03.
  Crashes merely RELOCATE (monaco/interlagos vs lemans/hungaroring).
  WARNING recorded: the probe's lower move counts looked like a pace win but
  are the mv composition artifact — probe move counts include crashed cars,
  mv averages finishers only. Never read the probe as a pace measurement.
- **Round 48 (idea 1, move-order/timing-exact world): CLOSED NEGATIVE,
  STRUCTURALLY.** Right-of-way is ALREADY modelled — `simulateTwoRounds`
  blocks rivals out of my candidate cell (`blocked[playerNum-1]`) and steps
  them in true turn order. The one remaining stale-world site
  (`countBrakeProofs`, a ply-2 question asked against `predicted`) was
  floored with the timed world => byte-inert on 15 races. Instrumentation
  (`patch_r48_debug.py`): the site is reached only **67 times in a 601-move
  lemans race** and returned `pred=2` EVERY time — `predicted` never blocks
  a braking descent, because AI1_VACATE_V already nulls exactly the fast
  rivals that would be near a fast car. Both ply-2 consumers are now
  provably correct. LAW: the speed-brake machinery (speedCap/waiver) is
  nearly DORMANT; do not look for pace there.
- **Round 51 (idea 2, exact-self rollout, `patch_r51_exactself.py`):
  byte-INERT alone.** `simOutcome` rolls MY car as pure greedy min-turns
  though the real me is the scorer (whose trap ladder refuses <=2 safe
  successors), so it reports FALSE DEATHS ("zandvoort s7 is greedy-me model
  error"). Fixed via a `selfMoveOverState` (maximise safe successors capped
  at 3, then min ttf) threaded behind an explicit `exactSelf` flag
  (AI1 true / AI2 false, since DJS is shared post-promotion). Result:
  0/15 divergence on zandvoort (incl. s7) / hungaroring / coil, 1/15 on the
  sinks. REASON (structural): DJS is SURVIVAL-ONLY, so it keeps a surviving
  pick regardless of how survival was computed — the self-policy can only
  matter when greedy-self DIES but trap-aware-self lives. Rare.
  LAW: a fidelity fix behind a narrow trigger cannot pay; check the trigger
  rate BEFORE building the fidelity fix.

## Crash floor REACHED — rounds 45-46 (all neutral, do not re-grind)

The round-44 champion's residual crashes (8-car c=3 s1-5 / c=5 s6-10, the
"ancestral" sites: silverstone s6, zandvoort s7/s8, coil s6/s10, zigzag
s4, lemans s4, hungaroring s1 guard) are at the EQUILIBRIUM FLOOR. Every
DJS refinement tried came back byte-neutral at the ancestral screen:
- R45 arm A (always-on DJS trigger, drop the trap>=0.5 gate): REJECTED —
  6 switches/race, false-DEATH model errors perturbed the field into new
  doom pockets (hungaroring guard 1->5). LAW: the trap gate bounds
  exposure to sim model error; it is not a pure cost gate.
- R45 arm B (finished cars vanish from the sim board): SHIPPED (22af7ad)
  as groundwork — full 7-stage battery PERFECT ties. Neutral because
  gated fires are rare and no gated verdict flipped on benched seeds.
- R46 (trap-aware greedy sim policy, prefer roomy landings): neutral,
  reverted.
- R46c (horizon rounds 3->4): neutral, reverted.
CONCLUSION: DJS is saturated at its trigger; better sim fidelity and
deeper horizon do NOT touch the ancestral floor. Crash reduction via
DJS is EXHAUSTED. The next crash gain (if any) needs a different
mechanism class (the shapes are speed-7-10 corner entries where a body
takes the escape; a real-me sim or a pre-emptive speed brake, not more
DJS). NOT the place to spend hours — see the pace frontier (lever 2).

## Bench speed (IMPORTANT — was the "taking hours" complaint)

Root causes: (1) every bench re-ran the FROZEN champion AI2 column =
~50% pure waste; (2) the 7-stage gate (both seed sets x all field sizes)
is deliberately large (small samples give false wins); (3) the champion
got costlier per move (joint sims + solver); (4) worst of all, full
batteries were spent on candidates in the mined-out crash region that the
equilibrium law already predicted neutral.
FIXES: bench_ai.py now honours BENCH_BASELINE=<json>: runs ONLY the AI1
candidate column and reads AI2 from the cache (first run with no cache
seeds it; delete on promotion). Champion caches seeded in scratchpad
(champ_8car_s1.json / _s6.json from r45bat). => every candidate bench is
~2x faster. PROCESS FIX: use the cheap targeted ancestral screen
(~30 min, crash_harvest on the specific sites) as the go/no-go; run the
full battery ONLY for a candidate that MOVES the screen. Rounds 45-46
never moved the screen and never needed batteries (R45B's battery was the
avoidable waste).

## Methodology laws (hard-won, do not relearn)

- **Forensic-first**: never build before reading the actual crash/decision
  logs. Replays are deterministic — same seed reproduces exactly.
- **Seed-set law**: 5-seed crash deltas are noise (~c7 events); always
  confirm on independent seeds 6-10. n=1 crash deltas are noise.
- **Equilibrium law**: local move re-ranking relocates crashes/pace at the
  traffic equilibrium (proven across pace gates, seal guards, queue guards,
  sim pricing, min() trap counts, threshold tuning). Beaten exactly once —
  by DJS's survival-only asymmetric search. Any new mechanism must explain
  why it isn't a re-rank.
- **mv composition artifact**: mv averages FINISHERS' moves; saving slow
  back-markers RAISES mv without anyone driving slower. Judge equal-speed
  on equal-finisher tracks (per-track diffs), not the TOTAL line.
- **Proxy overfit**: a traffic-sink-only proxy finds wins that evaporate
  over all 22 tracks.
- **Insurance-premium law**: braking/yielding for danger can cede h2h
  places — EXCEPT survival-only switches (DJS h2h: parity places, halved
  crashes).
- The scorer's trap ladder was RIGHT at every forensic kill; auxiliary
  selectors that ignore it (old paceOverride/sealGuard defects) were the
  round-35/36 crash sources. Those fixes (paceGuard v5, trapCount) were
  REVERTED by user choice ("back to last champion") but the -55% result
  was real; recoverable from git history (8268e4f, bf74f44) if wanted —
  note DJS now covers most of the same crashes a different way.

## Bench & tooling (critical operational knowledge)

- Build: `./build_main.sh` (javac via `git ls-files` — NEW files must be
  `git add`ed before compiling; then jar). Never rebuild while races run
  (Windows file lock; also the user's game GUI (javaw) locks the jar —
  check `tasklist` for javaw before rebuilds).
- Bench: `tracks/bench_ai.py` — `--seeds N`, `--h2h` (4v4), `--4p`, `--1v1`,
  `--slow` (serpentine/serpentine2/spiral/cog), `--tag NAME` (isolated
  props+log). Java flags: `--auto --track T --props P --log L --seed N`,
  plus `--dump-reach FILE` and `--query-moves IN OUT`.
- **Session kills background tasks**: client reconnects tear down
  `run_in_background` bash tasks (4 batteries died). Long runs MUST be
  detached OS processes:
  `Start-Process sh full_battery.sh` (PowerShell) writing stage logs +
  a progress file + a DONE marker, polled via ScheduleWakeup.
- **OneDrive hazard**: the repo dir is synced; rapidly-rewritten bench
  files there wedge runs (~25 min in) and can lock the jar. Keep bench
  props/logs on LOCAL disk (the scratchpad) — `bench_iso.py` does this.
- Serialization law: never run two benches/reachability-heavy javas
  concurrently (240s timeouts -> INVALID rows).
- This session's scratchpad (tools + all logs + reach dumps live here,
  persists on disk):
  `C:\Users\carlg\AppData\Local\Temp\claude\E--OneDrive-Coding-Java-theoreticRacing\749c6115-9b8c-4154-9f26-d8f380240d27\scratchpad`
  Key tools: crash_harvest.py (env KIND=AI1|AI2, NP=n; saves per-seed
  logs), run_debug.py (replay one seed with AIDBG dump — needs the debug
  instrumentation in the build), bench_iso.py (isolated chunked bench),
  full_battery.sh (detached 7-stage gate), tune_thresholds.py,
  headroom.py, start_congestion.py, density_compare.py, logdiff.sh,
  patch_djs.py / promote_djs.py (the shipped round-40 patches),
  reach_*.bin (22 dumps), djs_*.log (the promotion gate record).
- AIDBG debug instrumentation (`-Dai.debug.player=N` per-candidate scoring
  dump): NOT in the current champion source (reverted with round 34-38).
  Re-apply from scratchpad/patch_debug.py if forensics need it (it is
  behavior-neutral, both bodies, gated).
- Track gen: `tracks/build_synthetic.py` (serpentine has `pitch_jitter`
  for per-hairpin radii; serpentine2 = 150x130 width 9 lanes=8 pitch=22
  step=5 pitch_jitter=5). ASCII render: `tracks/plot_track.py`.

## Recent git history (all pushed, normal commits)

- 9ad009b Danger joint search: new champion (round 40, promoted into AI2)
- b86339b AI1: name the gate thresholds (round 39 tuning surface)
- e6f2fbc Add serpentine2 to the --slow bench set
- aa77a67 serpentine2: give each hairpin its own radius
- 35a100d Add serpentine2 track (tighter, 8 lanes, ~5.8-cell corridor)
- 2522119 Revert AI1 to champion: drop round 34-38 crash experiments
- bf74f44 / 8268e4f: the reverted crash-reduction line (recoverable)

## User context

- Plays the game via the GUI (javaw); user.properties is THEIR file —
  never commit or clobber it; a killed bench can corrupt nPlayers (bench
  hardens by setting 8 itself).
- The user's other heavy compute (python jobs) shares the machine — don't
  contend; pause benches if they need it.
- Effort: remind the user to run `/effort max` at session start (global
  CLAUDE.md rule).
