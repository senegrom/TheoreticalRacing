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
