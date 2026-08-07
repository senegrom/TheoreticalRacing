# AI development and promotion

`RaceAi` intentionally keeps two complete move-selection bodies:

- **AI1** is the experimental frontier.
- **AI2** is the frozen champion and the independent comparison standard.

Shared geometry, reachability and simulation helpers may be cleaned up, but the two top-level scorers stay separate so an experiment cannot silently change its own benchmark.

## Fast development loop

```bash
sh ./run_tests.sh
sh ./run_golden_tests.sh
python3 tracks/ai_probe.py --allow-divergence --seeds 3 sprint hairpin lemans hungaroring
python3 tracks/bench_ai.py --seeds 5 lemans monaco hungaroring zandvoort
python3 tracks/bench_ai.py --h2h --seeds 5
```

The golden corpus always drives **AI2**. It is deliberately small and deterministic; changing a fixture is a champion-promotion action, not routine test maintenance.

`ai_probe.py` compares normalized AI1 and AI2 move logs and prints the first changed decision. It is the cheapest way to reject an inert experiment or localize an unexpected divergence before launching the expensive battery.

## Full promotion battery

Run the **AI promotion battery** workflow from GitHub Actions. It executes these jobs independently and retains each textual report as an artifact:

- 8-car self-play on seeds 1–5, 6–10 and 11–15
- 4v4 mixed AI1/AI2 on the same three seed sets
- 2v2 on seeds 1–5
- 1v1 on seeds 1–5
- the slow synthetic suite on seeds 1–5

A completed workflow proves that every race executed and produced valid logs. Promotion still requires reading the reports because aggregate average moves can be misleading when a candidate saves a slow back-marker, and a five-seed crash difference can be noise. The hard-won interpretation rules in `racing-memory.md` still apply.

## Current AI1 frontier: dense slow-pack escape proof

AI1 currently contains an experimental trigger for the last canonical round-66 failure, Le Mans seed 4. The doomed car entered a moving eight-car funnel while the cheap opponent model still judged the chosen line safe. The new trigger is deliberately narrow:

- eight-car field with all seven live rivals within Chebyshev distance 10;
- landing speed squared at least 16, so start-grid pileups do not trigger it;
- a near-equal alternative exists with a low trap penalty;
- then, and only then, the expensive real-scorer-rival rollout arbitrates the move.

On the known counterexample AI1 changes move 55 from `SE` to `SW` and converts the result from **6 finishes / 1 crash** to **7 finishes / 0 crashes**. AI2 remains unchanged. This is an experimental frontier until the complete promotion battery is reviewed.

## Highest-value next AI directions

### 1. Bottleneck-aware rollout triggers

The dense-pack rule is a measured fix for one funnel. A more general trigger should precompute local corridor width or cut-set information and identify states where two or three future cells control every route through a bottleneck. Expensive scorer rollouts could then fire on topological danger rather than a track-specific traffic shape.

### 2. Per-turn transposition caches

Candidate rollouts repeatedly visit nearly identical detached boards. Memoizing `simOutcome` by board state, mover, remaining horizon and policy flags would let AI1 evaluate more alternatives or longer horizons at roughly the current cost. Cache lifetime should be one real turn so memory remains bounded and no stale live state leaks between decisions.

### 3. Small opponent-policy beams

A single predicted opponent move is brittle in queues. For the nearest one or two rivals, retain their best two plausible scorer moves and evaluate a bounded pessimistic beam. This targets model uncertainty directly without branching every car or replacing the deterministic controller.

### 4. Event-driven horizons

Fixed three-, five- and eight-round horizons spend work after danger has passed and stop early in long funnels. Roll forward until the car exits the bottleneck, the local pack disperses, it finishes, or a strict node budget is reached. The stopping event is more meaningful than an arbitrary round count.

### 5. Learned risk trigger, deterministic controller

Use the existing move-query oracle and race logs to train a small classifier that predicts whether the chosen move needs expensive verification. The model should only trigger the existing proof-oriented rollout; it should not choose the move itself. That preserves deterministic rules and makes false positives a performance cost rather than a safety regression.

### 6. Three-car endgame search

The exact 1v1 solver can be extended to three live cars near the finish using a bounded paranoid or MaxN search. Trigger it only when all three have small exact empty-track ETA and a low branching factor.

### 7. Better progress coordinates

`distAt` is useful but can confuse nearby portions of a folded track. A centerline/arclength progress map would improve “ahead”, convergence and queue ordering tests, especially at hairpins and parallel straights.

### 8. Counterexample search

Automate adversarial start-grid search and track mutation, then minimize any found crash to the shortest reproducible move prefix. This should produce better AI ideas than tuning global weights against averages.
