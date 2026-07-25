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

## Current champion (round 44, commit b0f64c5, pushed)

**DJS + sealfix + 1v1 endgame solver, promoted into AI2 per user
2026-07-22, self-tie verified (8-car AND 4-car identical columns).**
Canonical numbers: **8-car seeds 1-5 f=767 c=3 mv=64.07; 4-car seeds 1-5
f=329 c=1 mv=61.97.** vs the round-40 DJS champion: sparse 10-seed
crashes 4->1, 2-car 1->0, slow 1->0 (serpentine2 cleaned), 1v1 crash
edge 0v1, all at equal pace; packed 8-car unchanged (wash relocations).
Both AI bodies identical again; AI1 is free to diverge as the frontier.

(Superseded: round-40 DJS-only champion was 9ad009b, canonical
f=767 c=3 mv=64.06.)

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
are untouched. RECOMMENDED FOR PROMOTION (mirror the two AI1 mechanisms into
AI2; delete the champ_8car_*.json caches on promotion).

Mechanisms to mirror on promotion (both AI1-only today):
1. `patch_r49c_certpace.py` — certified pace tie-break: scoreNSByDir/poTByDir
   bookkeeping + the override block before `Direction chosen = ...`.
2. `patch_r51_exactself.py` — `selfMoveOverState` + `safeSuccessorsOverState`
   + the `exactSelf` flag threaded through simOutcome/dangerJointSearch
   (flip the AI2 call sites to `true, true` when promoting).

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
