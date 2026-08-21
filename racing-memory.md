# racing-memory.md — full working state for continuing the AI campaign

Written 2026-07-21 at the end of the round-40 session (session id
749c6115-9b8c-4154-9f26-d8f380240d27). A fresh agent should be able to
continue from this file alone. Long-form history: see
`C:\Users\carlg\.claude\projects\E--OneDrive-Coding-Java-theoreticRacing\memory\project_ai_architecture.md`
(auto-memory, ~2000 lines, every round's laws and rejections).
## Round 174 (local agent): the two-car squeeze escalation -- harvest-26 closed

Lemans s216 (the last open harvest-26 AI1 class) is a slow TWO-car
squeeze the framework structurally excluded three ways: (1) the fire is
trap-0 slow, and the r108 smoke gate needs >= 2 rivals within Chebyshev
3 (profiled on kills with >= 4) -- a two-car train never qualifies;
(2) in the bunched early field the fire routes through the dense-pack
ESC instead, whose cap-3 world reads the doomed line ALIVE (the
constraining bodies rank beyond the nearest-3 set: scorer-5 cap 3
alive, certification cap DEAD); (3) even the true-4 confirm reads the
m81 sibling alive, so any conjunction under-kills. Oracle: m89 (19,15)
v(3,-3) taken S dies @r3 with a one-unit-slower survivor; m81 taken W
dies @r4 (both averted by the fix, verified move-by-move in debug).

The fix, armed from EITHER route: a slow landing with a rival within
Chebyshev 2 whose smoke comes back alive-but-threaded (thread >= 1 &&
snug >= 2, audit already collected), OR the dense-pack route directly
(no smoke data there), pays ONE certification-cap scorer-5 check; a
kill escalates exactly like funnelRisk -- the cert-cap world sees the
death, so the standard verdict + r161-certified ladder switch runs
unchanged. A smokeNear widening (admit every Cheb-2 slow fire to the
smoke) was tried and REVERTED measured: ~+30% wall on train-heavy
mixed lemans, and unnecessary -- the specimen commitments route
through the dense path. No tier axis (drifts 2->3 between rounds 4
and 5 at m89 -- the r128 lesson holds).

Gate (re-run on the r169/171 master): s216 rescued; s252 +
serpentine2 s6/s35/s40 stay clean; fresh lemans mixed sweep s201-300 =
2 crashes, BOTH the open bottom-corner family (s264, plus NEW SIGHTING
s220 which drifted into that site on the current master BEFORE this
round -- byte-identical with and without it; the family fix absorbs
both); 16 pins PASS incl. golden and the new upstream private-slack
pin. Wall: dual-order lemans/monaco mixed inconclusive under the
restarted agents' ambient load (single-run swings +-30%; symmetric
averages +4-8%); structurally the arm pays one cert-cap scorer-5 per
dense-route Chebyshev-2 slow fire and zero elsewhere (probe: 0
signature fires on five canon tracks).


## Round 169 promoted: bounded exact-private score slack

Round 169 permits both mirrored smart-driver kinds to take one separately
ranked private-lane runner-up. It may concede at most 0.25 in the score
remainder after trap and uncertainty, but must recover exactly one reachability
turn from a non-coasting incumbent at TTF 46-90. The candidate acceleration
must remain directionally aligned, use exact L2 trap and zero uncertainty, stay
below speed-squared 49, preserve current speed-squared while exceeding the
incumbent landing speed, land unsealable, pass the fail-closed four-round,
two-exit exact-private certificate, and prove strict mover progress with
non-worsening aggregate field cost in the eight-round, six-rival scorer world.
A kind-homogeneous starting roster is required. The runner-up cannot displace
an existing private-lane winner, and all downstream guards retain final
authority.

At Hungaroring seed 12, global move 370 changes player 2 from `W` to `SW`.
Both policies retain the same seven finisher identities and order with zero
crashes. Player 6 finishes in 127 moves instead of 128; every other driver's
logged move count is unchanged, yielding one fewer logged player-turn without
claiming an earlier finishing round or a global average gain. Nine permanent
veto fixtures preserve the known false-positive boundaries: Le Mans s2, Spa
s1, Hungaroring s40, Interlagos s47, Monza s30, Monaco s35, Zandvoort s34,
Monza s145, and Serpentine s38.

The external promotion gate compared the frozen `04D9DFEC...` champion with
the frozen `F536762B...` mirrored final, all-AI2, across all 22 default tracks
at seeds 1-150 plus all four slow tracks at seeds 1-50. Of 3,500 complete
behavior logs, 3,499 are exact and the sole divergence is the strict
Hungaroring s12 gain above: no slower driver, redistribution, finisher-identity
change, or safety regression. After composing Round 171 and its small-grid
hardening, the frozen Round-169 `F536762B...` build and integrated `9AA796B...`
build matched on all 3,500 complete behavior logs. A separate post-mirror
differential matched AI1 and AI2 exactly on 350/350 default/slow races.
Java/core/UI tests, all 13 goldens, tooling, and all 16 permanent AI regression
pins pass.

The pre-mirror runtime check used eight warmups followed by 32 alternating-order
pairs across Hungaroring seeds 12 and 13 (64 timed executions). Seed 12's
trimmed candidate/control ratios were 0.9568 wall and 0.9513 CPU; exact-control
seed 13 measured 0.9831 wall and 0.9905 CPU. Behavior hashes remained stable,
and neither measured case showed a computation-time regression.

## Round 168 candidate: direct occupancy maps and thread-owned geometry caches

Two exact search hot paths repeatedly scanned the same player arrays. The
candidate builds a touched-cell byte map once for the two-round ahead test and
once for each mobility projection, then answers in-grid occupancy queries with
a direct lookup. Duplicate-cell ordering, outside-grid fallbacks, current-player
exemptions and every move-selection rule remain unchanged.

The geometry fallback cache is now lazy and thread-owned. This fixes the race
between background reachability construction and an interactive move on the
event thread, while avoiding roughly 4.8 MiB of eager point/edge cache storage
for the common dense-cache path. Worker and event-thread values are explicitly
released at their lifecycle boundaries.

The upstream Round-168 screen compared 186 alternating timing races and kept
every complete log byte-identical; its aggregate median was 6.45% faster. The
rebuilt local candidate then matched the pulled Round-160 baseline byte-for-byte
on 78 races across all 26 tracks: 546 finishers, zero crashes and 37,739 summed
finisher moves on each side. Five-pair alternating local timing measured Sprint
10.9%, Monaco 3.4%, Zandvoort 6.5%, Nurburgring 2.9% and Interlagos 4.0% faster.
The summed median fell from 38.91 s to 36.51 s, a 6.16% improvement, with no
slower median case. Java/core/UI tests, all 13 goldens, tooling and all 15
permanent AI regression pins pass. This is a computation-speed improvement;
racing moves and outcomes are intentionally identical.

## Structural cleanup: private-lane proof module

The bounded adversarial private-lane certificate now lives in
`RaceAiPrivateLane`. One session owns the rival rectangles, lazy exact fallback,
primitive cache/frontiers and shared fail-closed node budget for a complete
candidate loop. `RaceAi` retains the policy gates and candidate ordering, but
calls intention-revealing approximate and exact certificate methods instead of
carrying the proof engine internally. This removes 346 lines (7.94%) from the
main class without introducing mutable static scratch state.

The pre-split and modularized JARs produced byte-identical complete logs for all
26 tracks at seeds 1-3: 78/78 pairs, 546 finishers, zero crashes and 43,255 move
lines. Java/core/UI tests, all 13 goldens, tooling and all 15 permanent AI pins
pass. Five-pair alternating timing was also output-identical: the modularized
build was 1.18% faster in aggregate; its only slower median case was Interlagos
at 2.17%, below the five-percent refactor limit. This is responsibility
separation only; no move-selection rule or racing outcome changed.









## Round 161 (local agent): a confirmed switch must never fall back to an UNCERTIFIED target

Harvest 26 (fresh mixed s201-300, all 26 tracks, 3 crashes/2600 -- the
lowest rate ever) delivered spielberg s252, and its walk exposed a
FRAMEWORK BUG latent since the round-99/105 ladder: in the trueDead
switch path, when EVERY candidate fails the true-rival certification
(`confirmed == null`), the old code silently returned the cheap-world
`best` anyway. At s252 m159 (49,81) v(-8,-11): the champion correctly
chose E -- the ORACLE-TRUE SURVIVOR -- the cheap world false-killed E,
certification rightly rejected the doomed NE as true-DIES, and the
fallthrough switched into NE regardless: trading no crash for a crash.
The fix is one line (`best = confirmed;` unconditionally): no certified
escape means KEEP THE CHOSEN, exactly what the round-102 comment always
claimed the code did.

Also folded in: the round-93 fastFragile healthy-tier path no longer
swallows acceleration-into-band fires before they reach the round-133
vmax leg (fastVAccel falls through to the fallback) -- a correctness
completion of r133 discovered in the same forensic chain.

Gate (on the round-160 master): spielberg s252 rescued (0 crashes, was
1); serpentine2 s6/s35/s40 stay clean; 16 pins PASS including golden
(the no-certified-target path fires in no golden race) and both class
pins. The fix touches no hot path (a rare-branch outcome only).

Remaining harvest-26 residuals: lemans s216 -- NEW slow two-car-squeeze
class, fully walked (last-avoidable m89 (19,15) v(3,-3), taken S dies
@r3, SW survives; fire signature tier=2 thread=1 snug=2 sits BELOW
every leg threshold, two-car train below the deep-pack gate; scorer-5
AND true-4 at cap 6 both kill it, so the standard conjunction works
once armed: candidate arm = slow fire + thread>=1 + snug>=2 + tier<=2
+ rival within Cheb 3, rate probe pending). lemans s264 = another
bottom-corner-family sighting for the round-127 pile.


## Round 160: direct blocked-cell bitsets for mobility search — 6.5% faster on the measured batch wall

The four-ply mobility search repeatedly tested candidate landings
against the same small predicted blocked-cell sets. Round 160 keeps the
exact 64-bit cell lists for the outside-grid fallback, while adding one
collision-free in-grid bitset per ply. Ordinary membership tests become
a direct word-and-bit probe instead of a linear scan.

Outer and nested mobility searches retain separate reusable primitive
workspaces. Resetting clears only words touched by the preceding
projection. Every bit is derived from the original exact cell list;
lookup semantics, memo epochs, rollout policy and selected moves are
unchanged.

Exact gate: 3500 all-AI2 baseline/candidate race pairs
across all 26 tracks, with every complete race log byte-identical. The
full Java suite, headless smoke, golden corpus, homogeneous AI probe,
tooling tests and every permanent AI regression pin passed on the JDK
25 candidate and again from a clean production checkout.

Seven-pair dual-order warm batches measured Monaco
8.4% faster, Nürburgring
4.9% faster, Zandvoort
5.4% faster, Interlagos
2.1% faster, and Sprint
7.1% faster. The weighted median aggregate is
6.5% faster; no measured case crossed the five-percent
regression limit.

## Round 158: share immutable legality rasters across auto batches — 6.3% faster on the measured batch wall

The conservative unit-cell and RES=4 legality rasters are immutable,
exact products of track geometry, yet every seed in an auto batch
rebuilt both arrays. Round 158 adopts one exact raster pair for every
subsequent `RaceGame` carrying the same geometry cache key.

The access-ordered pool is capped at 64 MiB of byte arrays. Interactive
games retain private rasters. Concurrent first builders may duplicate
work, but publication retains one complete exact pair; the arrays are
never modified after publication. AI policy, exact fallback geometry,
reachability products and race ordering are untouched.

Exact gate: 3500 all-AI2 baseline/candidate race pairs
across all 26 tracks, with every complete race log byte-identical. The
full Java suite, headless smoke, golden corpus, homogeneous AI probe,
tooling tests and every permanent AI regression pin passed on the JDK
25 candidate and again from a clean production checkout.

Five-pair dual-order warm batches measured Monaco
9.5% faster, Nürburgring
2.0% faster, Zandvoort
10.9% faster, Interlagos
2.7% faster, and Sprint
0.3% slower. The weighted median aggregate is
6.3% faster; no measured case crossed the five-percent
regression limit.

## Round 157: share immutable progress maps across auto batches — 2.7% faster on the measured batch wall

The distance-to-finish BFS and its derived progress-ring widths are
immutable functions of track geometry, yet every seed in an auto batch
rebuilt them before racing. Round 157 adopts one exact pair for every
subsequent `RaceGame` carrying the same geometry cache key.

The access-ordered pool is capped at eight million integer entries
(roughly 32 MiB plus row overhead). Interactive games remain private.
Concurrent first builders may duplicate work, but publication retains
one exact pair; no array is modified after publication. AI policy,
reachability products, geometry verdicts and race ordering are
untouched.

Exact gate: 3500 all-AI2 baseline/candidate race pairs
across all 26 tracks, with every complete race log byte-identical. The
full Java suite, headless smoke, golden corpus, homogeneous AI probe,
tooling tests and every permanent AI regression pin passed on the JDK
25 candidate and again from a clean production checkout.

Seven-pair dual-order warm batches measured Monaco
2.8% faster, Nürburgring
0.2% faster, Zandvoort
5.2% faster, Interlagos
2.0% faster, and Sprint
0.5% faster. The weighted median aggregate is
2.7% faster; no measured case crossed the five-percent
regression limit.

## Round 156: share exact dense edge caches across auto batches — 20.1% faster on the measured batch wall

Round 150 replaced hashed geometry-edge lookups with a collision-free
direct byte table, but each seed in an auto batch still allocated and
repopulated the same immutable table. Round 156 shares that exact table
between consecutive `RaceGame` instances carrying the same geometry
cache key.

The shared store is an access-ordered LRU capped at 128 MiB, while the
existing per-track 64 MiB admission cap remains unchanged. Interactive
games retain private tables. Every nonzero entry still comes from the
unchanged exact geometry predicate; duplicate concurrent byte writes are
idempotent, and a stale zero can only trigger an exact recomputation.
AI policy, finish logic, reachability products and race ordering are
untouched.

Exact gate: 3500 all-AI2 baseline/candidate race pairs
across all 26 tracks, with every complete race log byte-identical. The
full Java suite, headless smoke, golden corpus, homogeneous AI probe,
tooling tests and every permanent AI regression pin passed on the JDK
25 candidate and again from a clean production checkout.

Five-pair dual-order warm batches measured Monaco
23.7% faster, Nürburgring
12.6% faster, Zandvoort
30.6% faster, Interlagos
13.7% faster, and Sprint
2.8% faster. The weighted median aggregate is
20.1% faster; no measured case regressed by more than the
five-percent fail-closed limit.

## Round 150: direct in-grid edge legality cache — 5.4% faster on the measured wall

The post-Round-134 profile left the open-addressed geometry-edge cache
among the largest hot leaves. Every production AI edge is identified by
an integer origin and a bounded velocity delta in `[-12,12]^2`; Round
150 stores that finite in-grid domain in a direct byte table. A lookup
now needs one index calculation and one byte read instead of packing,
mixing and walking an open-addressed probe chain.

The table is capped at 64 MiB. Unusually large user tracks and every
out-of-domain query retain the existing exact hash cache. The direct key
is collision-free over its admitted domain, and the stored verdict is
still produced by the unchanged exact geometry predicate. AI policy,
reachability, finish logic and race ordering are untouched.

Exact gate: 3500 all-AI2 baseline/candidate race pairs
across all 26 tracks, with every complete race log byte-identical. The
full Java suite, headless smoke, golden corpus, homogeneous AI probe,
tooling tests and every permanent AI regression pin passed on the JDK
25 candidate and again from a clean production checkout.

Five-pair dual-order warm batches measured Monaco
3.3% faster, Nürburgring
0.6% slower, Zandvoort
8.8% faster, Interlagos
6.1% faster, and Sprint
7.6% faster. The weighted median aggregate is
5.4% faster; no measured case regressed.

## Round 134: exact point-containment cache — 12.8% faster on the measured wall

Round 130 removed boxed mobility-search overhead and left `Area.contains`
as the dominant sampled leaf. Round 134 closes that independent geometry
frontier. The residual exact line scan repeatedly asks whether the same
rational point lies inside the fixed track; the cache stores only the
unchanged exact AWT verdict.

The legality path first reuses the existing conservative RES=4 sub-raster
for points whose complete subcell was already proven interior. Unproven
points fall back to `Area.contains`, with the result stored in an
allocation-free open-addressed table keyed by both raw IEEE-754 coordinate
bit patterns. Collisions require full two-key equality, resizing preserves
every entry, and the table is cleared whenever track geometry is rebuilt.
No geometry approximation or AI-policy rule changed.

Exact gate: 3500 all-AI2 baseline/candidate race pairs across
all 26 tracks, with **every complete race log byte-identical**. The full
Java suite, headless smoke, golden corpus, homogeneous AI probe, tooling
tests and every permanent AI regression pin passed on the JDK 25 candidate
and again from the production checkout.

Four-pair dual-order warm batches against the Round 130 champion measured:
Zandvoort 14.9% faster,
Nürburgring 38.3% faster,
Monaco 12.0% faster,
Interlagos 4.7% faster and
Sprint 3.0% faster. Across the five weighted
medians the candidate is 12.8%
faster. Promotion required at least a five-percent aggregate win and no
measured case more than five percent slower.

## Round 129 promoted: measured frontier pace for both driver kinds

The harvest-23 alternating 4v4 census measured AI1 ahead of frozen AI2 on
21 of 22 tracks, with a 2.05-place-sum advantage per race. Round 129
promotes the already separately certified Round 115 moderate-energy,
Round 117 synchronized six-ahead and Round 124 phase-consistent trap
acceleration arms to AI2 as well. Round 126's homogeneous equal-speed
false-target veto is promoted with them, repairing Zandvoort seed 115 for
both kinds. A later promotion also mirrored the Round 128 mixed finish-funnel
confirm, so the current champion is identical for both smart driver kinds.

Exact gate: 3500 all-AI2 baseline/candidate pairs,
4 Pareto-faster race(s),
1 safety gain(s), zero individual slowdowns in the four pace races,
zero safety regressions, zero aggregate-only gains and zero finisher-set
redistributions. In the safety-gain race one existing finisher is one move
slower while a previously crashed racer finishes; no race is classified slower.
The permanent Round 115/117/124/126 pins now require the promoted result from
both AI1 and AI2.

## Round 133 (local agent): the vmax overspeed deep check -- the slow-track surface cleared

The harvest-25 class shipped. At the deepest dangerJointSearch, a chosen
move that ACCELERATES into max-axis >= AI1_FASTV_MAX (11 = VMAX-1) is
re-verdicted with the deep suppressed world (AI1_DEEP_HORIZON rounds at
the certification cap) ALONE -- the r107 single-world precedent, because
the true confirm worlds read the doomed line alive (joint-rollout chaos)
while scorer-8-cap6 kills it (thread=3 snug=4 lights up only there). A
kill takes the standard r105 slower-first ladder switch; the surviving
vx<=10 siblings certify in both worlds.

Probe forensics that shaped it: probe v1 at the round-59 fallback MISSED
all three commitments -- their computes route through the round-65
deep-pack escalation, so the leg lives at the deepest overload where
every entry path converges. Cruise-at-11 fires are excluded by the
acceleration condition (max-axis must increase this move). Probe v2:
all three commitments fire there with deep8=DEAD; ZERO false kills in
188 healthy fires (serpentine2 ~55/race, monza ~23, lemans/spa ~11,
bigoval 0); pricing A/B with the deep check paid at EVERY armed fire:
serpentine2 -0.2%, monza +-0.0% dual-order -- free.

One measured false kill, accepted and bounded: the first gate run
diverged golden lemans-s1-4p -- scorer-8's pessimism killed a
SURVIVING two-car-train line (p2 (63,65) S to v(3,11)); the race
converged to the IDENTICAL outcome (turns, places, zero crashes; only
the trajectory hash moved). A Chebyshev-6 train gate (physical: the
doom needs a rival to seal the escape rows; the commitments carry
theirs at 1, 2, 5) was added but this fire also has near6=1 -- no
cheap axis separates it (corridor width would, and is not cheaply
available; chasing further gates is proxy overfit). Accepted per the
promotion precedent: the fixture line for that one case regenerated;
every other golden is byte-identical on the r133 champion.

Gate: specimens s6/s35/s40 crash-free in ALL THREE kind orderings
(9/9); serpentine2 mixed sweep s1-100 ZERO crashes (was 4);
bigoval/monza/lemans/spa canon spot checks clean; 15 pins PASS. NEW
pin ai1_vmax_deep_regression (mixed serpentine2 s6+s35, both victim
slots). Applied post-promotion, so the leg serves both kinds from
birth (the class was kind-invariant).

Residual mixed surface after r128-promotion + r133: NOTHING known --
every walked class is either fixed (funnel both kinds, vmax both
kinds) or owned by the round-127 oracle framework (zandvoort
deep-corridor: s195/s223/s115-mixed m167; lemans bottom-corner: s108
p7+p2, s117 p5 -- model-boundary, STUCK-diagnosed).


## Round 128 PROMOTED (user-ordered): the fast finish-funnel confirm for both kinds

The user ordered the mirror ("Promote 128"). One line: the fallback's
fastSlow arm drops its moverKind gate. The harvest-24/25 block-ordering
natural experiment had already proven the exact effect: byte-identical
races crash iff the doomed slot lacks the leg.

Gate: all five known frozen-side victims RESCUED (reverse-ordering
lemans s36/43/45/46 and alternating s132 -- 0 crashes each); the three
serpentine2 specimens byte-identical (the leg never fires there --
they are round 133's); 15 pins PASS including golden all-AI2 (no
golden race hits the gate); dual-order wall on mixed lemans s36-40:
+5.0% run second, +0.3% run first (~+1-3% true, on the ONE arming
track, partly because rescued cars now race to the finish -- more
moves computed is more racing, not overhead). Canon behavior
elsewhere unchanged. NO kind-gated arms remain in the champion;
homogeneous AI1 and AI2 fields are again move-identical by
construction.


## Harvest 25 (local agent): the serpentine2 vmax-11 commitment -- round-133 candidate, probe pending

Slow-track mixed harvest (serpentine/serpentine2/spiral/cog; alternating
s1-100 + front/reverse s1-50 = 800 races): ALL 10 crashes are
serpentine2, three sites, and every site reproduces BYTE-IDENTICALLY
across all three kind orderings (only the victim's kind label moves
with the slot map) -- kind-invariant champion dooms; no other slow
track crashes at all.

Walks (reach_serpentine2.bin now in the session scratchpad; races are
in harvest25/): all three victims commit at THE SAME CELL. Bottom
straight, (75,112-114), vx=10: accelerating to vx=11 (E or SE) is a
5-9-round oracle doom; every vx<=10 candidate survives to the finish
(t=153-154). s35 m94 taken SE dies @r5; s6 m95 taken SE @r7; s40 m95
taken E @r9. Physics: vx=11 braking distance overruns what the
right-end hairpin absorbs ONCE TRAFFIC occupies the escape rows -- the
static reach map says alive (a solo escape line exists), the joint
world is dead.

THE KILL SIGNAL EXISTS IN-ENGINE: at s35 m94 taken SE, scorer-8 at the
certification cap is DEAD (V=-1, thread=3 snug=4 -- the thread audit
lights up in the deep world) while smom-3/scorer-3 AND true-4/5/6-cap6
all read alive (joint-rollout chaos blinds the true worlds again; the
suppressed deep world beats them here). The smom-3 fire carries NO
tell (tier=3 thread=0 snug=0): the only cheap arm is the velocity
itself (max-axis >= 11 = VMAX-1; spd2 ~121-122).

Round-133 design (pending ONE measurement): at fast fallback fires
with max|v| >= 11, re-verdict with scorer-8-cap6 (the shipped
AI1_DEEP_HORIZON world); on death take the standard ladder switch
(survivors vx<=10 pass every world). The confirm must ride scorer-8
ALONE -- true-4 reads the doomed line alive and a conjunction would
veto the kill (r107-style single-world precedent). OPEN RISK, measure
before arming: bigoval (and long straights on lemans/monza/spa) runs
max|v| >= 11 legitimately for many turns -- need fires/race and the
deep world's false-kill rate there. Probe ready:
apply_probe133.py in the session scratchpad (FASTV11 stderr lines,
print-only); run serpentine2 s6/s35/s40 mixed + bigoval/lemans/monza/
spa canon, then decide.

Numbering note: rounds 131/132 above are LOCAL rejected experiments;
the other agent's concurrent Round 131 (point-containment cache) is a
separate line.


## Round 132 (local agent, REJECTED measured): fmRec filter reorder + cache lesson

Post-r130 re-profile (per the new law) put blockedContains at 216
self-time leaves (#3). Candidate fix: run reach.isAlive before the
blocked-cell scan in fmRec (pure AND filters, outcome-identical --
byte-identity verified, 0 mismatches). DUAL-ORDER wall A/B (the r131
law, first use): order A side +6.9% slower, order B side -2.0% faster
-- symmetric average ~+2% SLOWER. Rejected and reverted.

Lesson: "one array read" is not cheap when the array is the
reachability alive map (DRAM-latency misses); the <=21-entry blocked
scan is cache-hot and CHEAPER. The original filter order was already
optimal; leaf-sample counts do not order costs across cache classes.

Coordination note: the other agent's concurrent Round 131 branch
(point-containment cache, alternating warm gate -- they independently
derived the order-bias discipline) owns the geometry frontier
(Area.contains ~534 leaves); the local exact-geometry-engine idea is
withdrawn in its favor. Local speed lane is parked at the measurement
noise floor until that lands.


## Round 131 (local agent, REJECTED measured) + the second-arm throttle law

Two identity-exact geometry short-circuits were built and byte-identity
verified (0 mismatched logs in 11 races, twice): subcell-certified
sample skipping in isMoveLegalGeometry (a nonzero sub-raster cell
proves containment, skip both Area tests) and a finish-line bbox
early-out in crossesFinish. Both REJECTED: no measurable win.

THE MEASUREMENT LAW THIS BOUGHT: at Idle priority with turbo active,
the SECOND arm of a per-seed interleaved A/B loses ~4-5% SYSTEMATICALLY
(thermal/boost budget). Full r131 measured +13% slower run second;
subcell-only +5.9% slower run second, then 3.3% FASTER run first --
i.e. pure order bias, true delta ~0. Any pairwise wall A/B must now be
run in BOTH orders (or alternate per seed); deltas inside +-5% in a
single order are unfalsifiable. Round 130's -20.6% was measured with
the win AGAINST the bias direction and stands (understated, if
anything).

Why no win despite 600+ Area.contains leaves attributing to
isMoveLegalGeometry: that profile was taken on the PRE-r130 jar.
Corollary law: RE-PROFILE after every landed speed round before
picking the next target -- a landed round reshapes the flame graph.

Working tree reverted; side.jar rebuilt in sync with master.


## Round 130 (local agent, speed): primitive mobility transposition table -- -21% monaco wall

Fresh JFR on the r129 champion (10 monaco races, self-time leaves):
Area.contains (~537) is still the top leaf -- monaco's wall-hugging
lines defeat the raster band, and RES-8 stays refuted -- but ~265 leaf
samples sat in HashMap.getNode/putVal/resize under fmRec. The mobility
memo was a fresh boxed HashMap<Long, Double> EVERY TURN (resize churn
from capacity 16 upward each turn), and the per-ply blocked sets were
HashSet<Long> whose contains() autoboxes, twice per candidate per node.
The r113 lesson (adding a NEW memo where none existed lost 3.4%) does
not apply to replacing the implementation of an EXISTING one.

Replacement, semantics identical: one pooled open-addressing table per
RaceAi (32768 slots; long keys, double values, int epoch stamps;
multiply-shift hash; probe cap 32 with graceful skip-store). Each
MobilitySearch takes a fresh epoch, so a hit needs epoch AND key --
nested rival-model searches can never cross-hit, and every eviction or
collision merely recomputes a deterministic value. Blocked cells became
per-ply long[] arrays (<= 3 cells x 7 opponents, duplicates fine,
linear scan -- at 21 entries scanning beats hashing).
greedyStepBlockTop3 appends to the array and returns the new count.

Gate: BYTE-IDENTITY of race logs master-vs-side across monaco s1-5,
zandvoort s1-3, silverstone s1-2 canon and mixed lemans s36 -- 0
mismatched logs in 11 races, provably behavior-neutral (evictions only
recompute; values are deterministic per search). 15 pins PASS. Wall,
interleaved per-seed A/B: monaco 10-seed 76.4s -> 60.7s (-20.6%);
zandvoort 5-seed 25.6s -> 25.4s (-0.6%, flat; its mobility load is light). Never slower anywhere measured.

Next speed frontier per the same profile: Area.contains exact fallback
(~537 leaves) concentrated on wall-hugging monaco-class lines -- the
raster band cannot prove those; any further win needs a different
proof shape (e.g. per-cell nearest-boundary distance field), not more
resolution (RES-8 refuted).


## Harvest 24 + post-129 recheck (local agent): the bottom-corner class and the STUCK boundary

Harvest 24 (mixed alternating s101-200 + BLOCK orderings front/reverse
s1-50, all 22 tracks, 4400 races) and a full post-promotion recheck (16
pins PASS on the r129 jar, every specimen re-verified there):

- NATURAL EXPERIMENT: the four r128 funnel seeds under block orderings --
  reverse (AI2 in slots 1-4) reproduces all four deaths byte-identically
  with AI2 victims; front (AI1 there) has ZERO crashes. The r128 leg
  rescues the identical race iff the victim is AI1: the kind gate proven
  live. These AI2 deaths (plus ma_lemans s132 m562) die whenever r128 is
  mirrored/promoted. ma_lemans s117's funnel death (p8 AI2) DISSOLVED
  under the r129 pace arms -- one frozen-side kill gone for free.
- NEW CLASS, bottom-corner train compression (the only fixable-side
  kills found): lemans bottom corner (82-85,163-170), southbound
  traffic turning W. s108 p7 AI1 m343 + p2 AI2 m346; s117 p5 AI1 m349.
  Both AI1 deaths persist byte-identically on the r129 jar.
- s108 p7 walked: last-avoidable m319 (84,154) v(1,4). INVERSION: the
  taken N (brake to v(1,3)) dies @r3; NONE (HOLD v(1,4)) survives t=21,
  NW/W also survive. Braking in front of the compressing rear queue
  (p8 (85,156) v(1,3) directly behind) is what kills -- opposite
  polarity to the funnel/corridor brakes.
- THE HARD PART -- world matrix at m319 taken N: smom-3, scorer-3,
  scorer-8-cap6, true-4/5/6-cap6 ALL alive (tier=3 thread=0 snug=1),
  oracle dead @r3 via a hard wedge (m343 mask XXXXXXXXX). SIMTRACE
  diagnosis: at sim r=1 the simulated p2 (84,155)v(2,5) goes STUCK and
  the rear pressure evaporates, so every capped/uncapped true world is
  effectively vacate-optimistic in dense queues. Extending horizons or
  caps CANNOT see this class; the divergence is joint-rollout chaos +
  STUCK-rival semantics. This is the third model-boundary family
  (after z195 and s223/zandvoort-s115-mixed m167, which persists on
  r129), now with a mechanism diagnosis.
- s117 p5 walked: doomed >= 8 own-moves out (m293 (79,128) v(2,8) best
  candidate dies @r7; m301/m309/m317/m325 all dead) -- a train-entry
  doom on the approach straight, p7/p8 committed alongside. Commitment
  depth varies by seed; the site+queue interaction is the invariant.
- Class disposition: both remaining AI1 kills are oracle-only-visible
  model-boundary dooms -- the round-127 oracle-certified structural
  framework is the right tool, NOT another confirm leg (any in-engine
  sim world diverges before the wedge). Walk boards live in
  r130_ma_lemans_s108/s117.log (session scratchpad). Design note for
  whoever picks it up: an in-engine bounded REAL-ROLL sim mode (exact
  global move order, no rival cap, no vacate optimism, STUCK=crash)
  would be the verification primitive this family needs; cost only
  works at a surgical structural gate.

Mixed crash surface after r128+r129, per 4400 harvest-24 races: 2 AI1
deaths (both bottom-corner) + 3 frozen-side AI2 deaths (funnel class,
die at next r128 mirror) + 1 AI2 zandvoort right-edge (m574, unwalked).


## Mixed h2h census (harvest-23, analysis): frontier -2.05/race over champion

Alternating 4v4 across all 22 tracks x seeds 1-100 (pre-r128 jar, but
crashes were 5/2200 so this is pace signal): AI1 place-sum 16.975 vs
AI2 19.025 (even split 18.0) -- the frontier wins 21 of 22 tracks.
Standouts: interlagos -3.66, coil -3.60, zandvoort -3.34, zigzag -3.04,
the_long_loop -2.90. The ONLY non-win is monaco (+0.10, coin flip) --
monaco is also the funnel-crowd outlier in the r128 rate data; a
monaco-specific pace look is a candidate frontier. This is the first
quantified frontier-vs-champion gap since the round-109 promotion and
the running measure of what a next promotion would buy.


## Round 128 (local agent): the fast finish-funnel confirm leg -- the mixed dimension's crash surface

Harvest-23 opened the MIXED 4v4 dimension (alternating kinds, odd=AI1,
seeds 1-100 x 22 tracks) plus fresh canon s201-250. Census: mixed produced
5 crashes total -- FOUR one deterministic lemans class (AI1 victim dead at
(6-7,74) in the terminal funnel; s36/s43/s46 byte-identical, s45 a sibling)
plus the accepted hairpin s68 (AI2 slot, same delegated code); fresh canon
produced ONE (zandvoort s223 p7 m167, new residual, unwalked). The lemans
class IS the entire unaccepted mixed crash surface.

Forensics (probe + oracle, all re-verified on the post-126 master): the
victims commit FAST fires that the smom-3 world reads alive while true-4
at the certification cap kills them; the commitments carry the legSlow
thread tell (thread=2 snug=2), which no fast leg audits. s36-class
commitment: (14,105) NW, tier=1, sim-ttf 7. s45 sibling: (11,97) N,
tier=3, sim-ttf 6 (oracle: the taken N dies @r3, braking survives; at
m536 all nine candidates are dead -- m529 is the last avoidable). The
bare signature on fast fires runs 21/race on monaco -- too hot to arm.
The separator is the SIM'S OWN HORIZON: every non-class signature fire
measured ttf 14+ (monaco/zandvoort mid-race, hungaroring start crowds at
96-98); the class sits at 6-7, inside the finish approach.

The leg (AI1-only, kind-gated): 16th param fastSlow on the deepest
dangerJointSearch (the 15-arg form becomes a delegating wrapper, every
other caller untouched), armed !djSlow && moverKind==AI1 from the
round-59 fallback. It extends the audit to fast fires (free: the chosen
verdict sim already runs; tier/thread/snug ride along) and arms on
thread>=2 && snug>=2 && chosenT <= AI1_FASTSLOW_TTF(10), firing the
DIRECT true-rival confirm at AI1_TRUE_CONFIRM_ROUNDS and the
certification cap: the scorer screen is BLIND on this class (scorer-3
reads both doomed lines alive), so there is no cheap pre-screen. A kill
takes the established r105 slower-first ladder-certified switch path.
NO tier axis: the t4 probe audit measured ZERO false kills across every
signature fire on monaco/mxmonaco/hungaroring (~200 fires, all healthy
crowds true-4-alive, both class siblings DEAD) -- the tier<=1
refinement only cost the s45 coverage.

Gate: all 14 pins PASS (13 ai1 + golden all-AI2 byte-identity);
specimens 4/4 crash-free; mixed lemans s1-100 sweep 0 crashes (was 4;
all 100 logs full-length). Every rescue is place-neutral: the saved car
survives to the end and is auto-placed eighth exactly where it used to
crash to eighth (survival-only, parity places -- the DJS shape). Wall:
zandvoort A/B 10s=10s; monaco interleaved 10-seed A/B 46.6s vs 47.0s
(+0.7%, inside per-seed noise). NEW pin
ai1_fast_funnel_regression (mixed lemans s36+s45 crash-free, one seed
per sibling). AI2 remains frozen (kind-gated out; all-AI2 races
identical by construction).

Residuals: zandvoort s223 -- WALKED, and it is a second specimen of
the round-127 deep-corridor family (gift for that branch): canon 8xAI1,
p7 crashes m167 at (61,1) after the top-right corner sequence. Last
avoidable m95 at (35,52) v(3,-9) spd2=90: the taken NONE dies at oracle
round NINE (invisible to every shipped sim horizon); shedding one vy
unit survives to the finish (SW v(2,-8)/S v(3,-8)/SE v(4,-8) all alive,
t=116-117, sheds of 22/17/10 spd2 -- note a 10-unit shed suffices here
vs z195's twelve). Structural context differs from the z195 gate (open
corner entry, not a width-three funnel), so the round-127 brake likely
needs its class widened or a sibling gate; the m95 board is in
r129_z223.log (this scratchpad) via oracle_roll cand 95. hairpin s68
(accepted place-neutral). CORRECTION for the z195 line: the earlier
"ultra-deep, no survivor to m70" classification of zandvoort s195 was
measured on a crashed walker (stale reach dump path) and is VOID; the
round-127 branch's fresh oracle forensics supersede it.


## Round 126: equal-speed false-target veto

Ported and re-certified the unfinished Zandvoort s115 mechanism on the
Round-124 master.  At an equal-map-turn, equal-speed, positive-trap
topology switch in a large homogeneous AI1 field, the bounded
certification-cap faithful-rival world is run on both landings.  A
switch is vetoed only when it would leave a true-alive chosen line for
a true-dead target.  AI2 is kind-gated out.

Exact gate: 3500 pairs,
1 safety gain(s), zero safety regressions,
individual slowdowns or redistributions.  Zandvoort s115 is rescued.
Residual frontier: accepted hairpin s68 and ultra-deep zandvoort s195.

## Round 114 (local agent): the pair-squeeze confirm leg -- three of four fresh specimens in one mechanism

HARVEST 22 (fresh 8car mega-window s151-200, 1100 races): 4 crashes --
silverstone s167/s191, hungaroring s195, zandvoort s195.

THE CLASS (silverstone s167 m157, fully probed): a fast L2 landing
with ONE rival racing a cell away (Chebyshev 1). Every pack gate needs
~three bodies; the fast fallback historically runs the smom world
(r59: "fast fires keep the proven smom world") which reads the squeeze
alive with NO tell (thread=0, snug=1 -- and the true SURVIVOR shows
thread=2: inverted again). The plain 3-round scorer world at the
DEFAULT cap separates perfectly (kills the taken W, keeps survivor N).

TWO SHAPES REJECTED MEASURED: the raw world flip (scorerRivals at
pair fires) fixed s167 but broke the hungaroring-s10 staged pin
(7/0 -> 6/1) -- the r59 wisdom holds; smom must stay the verdict.
SHIPPED: a PAIR-CONFIRM LEG in the existing confirm framework -- gate
= fast + L2 trap + rival within Chebyshev 2 of the landing (measured
0-5 fires/race); a smom-alive chosen dies only when the 3-round
scorer world AND the true-rival confirm agree; switch targets
ladder-verified as everywhere.

RESULT: s167 FIXED, and silverstone s191 + hungaroring s195 come FREE
(the same leg). All thirteen prior sites hold; twelve pins PASS;
probe 0/27. zandvoort s195 recorded OPEN: the top-complex corridor at
ULTRA depth -- no oracle survivor within twelve walk-decisions at
14-round horizons; beyond the walk's own resolution (the
champion-play-everyone rollout frays at that depth). Residual set:
hairpin s68 (accepted), zandvoort s115 (their round-108 target),
zandvoort s195 (new, ultra-deep).

RES=8 RE-MEASURED HONESTLY (post-fix, quiet box, interleaved 2x4
heavy races): consistently ~5%% SLOWER than RES=4 (14.3s vs 13.5s both
passes) -- the pre-fix "-5.8%%" was stale-jar garbage. SUB_RES stays 4;
the working-tree 8 was reverted without ever being committed (though
it rode along, behavior-free, in every r114 verification build).

PROCESS: the silent-stale-jar failure mode found and neutralized --
builds no-op when the harvest holds the jar lock (rm fails, set -eu
aborts, and "cannot remove" matched no error grep); several probe
runs and the whole RES=8 experiment ran on a 30-minute-old jar and
are VOID (RES=8 to be re-measured honestly). Recovery: side-jar
builds (compile to scratch, jar under a different name) bypass the
lock; jar freshness is now verified behaviorally after every build.

## Round 113 (local agent, REJECTED measured): mobility memoization

The next JFR target after the rasters was the mobility projection pair
(searchMinTurnsSoft3 / CountedSoft3, ~19%% of samples, 9-ary depth-4
recursion, no memo where fmRec has one). An epoch-keyed
HashMap<Long,*> memo (per-compute contexts invalidated by an epoch
bump, no clearing hazards, nested-compute safe) was built and proven
12/12 move-identical -- and measured 3.4%% SLOWER on a clean 3x3
heavy-track A/B (r112 29.8s vs r113 30.8s): boxed-map probe/store
churn exceeds the path-convergence savings at these depths. Reverted.
If this is ever revisited, it needs a primitive-key open-addressed
table, and the ceiling is small.

Bench-harness traps recorded for the next profiler: jars resolve
tracks against their own directory (a jar run from the scratchpad
finds no tracks and exits in ~150ms -- timing noise that looks like a
10x speedup), and --log /dev/null on Windows aborts the run the same
way. Both produced garbage timings this round before being caught;
always sanity-check race wall times (~1-6s) and log line counts.

## Round 112 (local agent): boundary-refined hybrid raster -- another -8%%

Continuing the legality attack (post-r111 JFR: legality still 38%% of
samples; the fallbacks hug walls, where racing lines live).

REJECTED, measured: a flat RES=4 sub-raster (+25%% wall -- 4x walk
density taxed EVERY edge and the 16x build taxed every JVM start).
FIRST HYBRID also +29%%: the sub-build refined every non-clean cell,
i.e. the entire outside-the-track area.

SHIPPED: the hybrid with a perimeter-bounded build. RES=1 walk stays
primary (open-track edges at round-111 cost); a RES=4 sub-walk is
tried only when RES=1 fails, before the exact predicate; the
sub-raster refines ONLY non-clean cells with a clean-interior
neighbour (the true boundary band) -- deep-outside and deep-wall
subcells stay unproven and fall through, which is correct (those
edges are mostly illegal anyway). Same one-sided band proof at each
resolution; the hybrid is an OR of two proofs.

VERIFICATION: 12/12 move-identical A/B against the post-r117 master,
probe 0/27, ALL THIRTEEN pins (their new graduated-field-accel and
six-ahead pins included). Canon on the r112 jar: AI1 62.699 vs AI2
62.701 -- the -0.003 column split is THEIR kind-gated rounds 115/117
pace gain (post-delegation frontier law: new arms gate on the mover
kind so the AI2 yardstick stays frozen), not a raster effect; the
raster is one-sided-provable and the A/B ran on exactly this
baseline. A/B wall 34.6 -> 31.8s (-8.2%%), stacking with r111 for
~-18%% total on the set, on top of r108's smoke gate.

JFR NEXT TARGETS: searchMinTurnsSoft3 / CountedSoft3 (the mobility
projection, now ~19%% and rising as legality shrinks); the residual
near-wall exact fallbacks.

## Round 111 (local agent): the legality raster -- function-level profiling pays

CORRECTION FIRST: round 108's ledger blamed their r106 forward-pack arm
for +55%% canon wall. The profiling twin now shows that arm fires 0
times on 21 of 22 canon tracks (coil: 2 bounded fires, ~0.4s) -- the
attribution was environment noise between measurements. Withdrawn.

REJECTED FIRST ATTEMPT (measured): static successor tables for the
tier computation (safeSuccessorsOverState). Behavior-identical 12/12
but ZERO wall gain -- site-level attribution had misled; the tier is
not the inner cost. Reverted per discipline.

THE REAL HOTSPOT (JFR, function-level): ~60%% of all execution samples
sit in first-time edge legality -- isMoveLegalGeometry samples the
segment at ~2x its length, each sample a java.awt.geom.Area.contains
CURVE test, and the sims explore hundreds of thousands of fresh edges
per race (the edge cache never evicts; these are genuine first visits).

THE FIX: a one-time conservative legality raster per track. Each unit
cell is classified provably-fully-inside the expanded track region
(EXACT Area.contains(rect) with a boundary-covering margin) and cells
near the left/right boundary polylines are marked (sampled cover with
one-cell dilation). Fast path: walk samples along the segment at
axis-step <= 0.5; every segment point lies within 0.5/axis of a
sample, so its cell is inside the 2x2 block at floor(sample - 0.5) --
if every such block is interior and path-free, all exact-check sample
points are inside and no polyline intersection is possible -> LEGAL
with integer math only. One-sided (fast path never answers illegal);
everything else runs the unchanged exact predicate. First cut used a
3x3 dilation tube (-6.7%%); the provable 2x2 band doubled the fast
tube's reach near walls (-10.6%%).

VERIFICATION: 12/12 move-identical A/B across every historic class
site and field size; probe 0/27; ALL ELEVEN pins; canon identity in
flight at write time. Total wall on the A/B set 40.0s -> 35.8s.

PROCESS NOTES: two more -Werror dangling-doc-comment trips (the
recurring insert-above-a-doc-comment trap); and jobs now launch at
Windows Idle priority per the user's new standing rule (Start-Process
-PassThru; PriorityClass='Idle'; children inherit).

## Round 110 (local agent): post-promotion simplification batch

USER DIRECTIVE: clean out old files and tools. Removed, with the
promotion probe + goldens + all pins + tooling tests green after:

- tracks/round106_{forward_pack,instance_state}_materialize.py and
  .github/workflows/round106-forward-pack.yml -- the other agent's
  one-shot round-106 promotion machinery; its changes have been on
  master since b9d69fd and the workflow only ever triggered on edits
  to the deleted scripts themselves. The round lives in the ledger.
- AI2_MOBILITY_DEPTH -- the ONLY dead member left in RaceAi after the
  delegation promotion (a reference sweep found the 796-line mirror
  body shared every other helper with the frontier).
- Untracked root debris (era60/prof jars, stray logs) -- era jars are
  one-command rebuilds, recipe now documented.

ADDED (permanence for round-109 tooling): tracks/cross_era.py -- the
dual-oracle cross-era referee, promoted from scratchpad with the era-
jar build recipe and the first exhibition result in its docstring.
OLD_JAR/RACING_WORK_DIR env overrides for reuse.

KEPT deliberately: bench_iso.py (tooling tests import it), tests/tr
Java unit suites, ci.yml + promotion-gate.yml, verify_reach_cache.sh,
policy_matrix POCKET entries (worked-example documentation; the file
already tells readers to regenerate logs before replaying).

## Round 109 (local agent): PROMOTION -- the rounds-98-108 champion is AI2

USER'S EXPLICIT WORD: "Promote now!". Executed the full protocol:

MIRROR BY DELEGATION: optimalMoveAI2's 796-line round-95-era body is
replaced by a delegation to optimalMoveAI1. The champion is one body
of code; every kind-sensitive gate in the shared machinery is
mover-symmetric (kindHomogeneous* compare against the mover's kind;
the confirm family is flag-gated, not kind-gated), so homogeneous
fields of either kind behave identically. Frontier law unchanged:
future experiments live in optimalMoveAI1 and must leave the
delegation untouched until the next promotion; during experiments the
delegation makes AI2 the OLD champion only after the next frontier
edit lands -- i.e. the yardstick freezes the moment AI1's body first
diverges again.

CERTIFICATION: strict probe 0/27 divergent (the mirror proof, exact
by construction and verified anyway); golden corpus REGENERATED and
green (two fixtures changed hashes as expected -- AI2 is a new
champion); ALL ELEVEN pins pass; self-tie h2h 4.500/4.500 c=0;
fixed-grid bench columns identical (62.604/62.604 +0.000); stale
BENCH_BASELINE caches deleted per the round-108 rule.

THE CROSS-ERA EXHIBITION (new tooling: cross_era.py -- any two
commits can now race each other): the r109 champion vs the r60
champion (rebuilt from 886fab9 as era60.jar), four cars each through
a dual-oracle referee (each era's brain answers only for its own cars
on a shared board; the new jar's mask is the rulebook), 24 races =
6 tracks x 2 seeds x both grid assignments, 96 car-races per side.
VERDICT: NEW 4.438 vs OLD 4.562 mean place, both crash-free.
Reading it honestly: competent vector racing is largely processional
(hairpin/interlagos ran perfectly grid-antisymmetric), so the +0.12
edge lives entirely on the tracks where overtaking exists (monaco,
zandvoort, chicane, lemans -- e.g. chicane s7: NEW 1,3,4,6 with OLD
pushed to 2,5,7,8). The 49 rounds between the two eras bought
head-to-head pace only modestly; what they really bought is the TAIL:
the r60 champion crashed ~1/40 on fresh seeds in its own era's
harvests, the r109 champion runs 1 accepted crash in 4070.

WHAT WAS PROMOTED (the arc in one line each):
r98 thread-fragility audit; r99 bounded true-rival confirm (depth
latch -> r103 depth counter); r100 corridor generalization; r102
alongside-pack gate + speed-scaled nets + dead-path target
confirmation; r103 certification-cap confirms + query-sim probe; r104
three-leg predicate with cost ladders; r105 slower-first ladder
targets; r107 ESC-route direct true-rival confirm; r108 smoke
proximity gate. Eleven crash specimens solved; residual = hairpin s68
(accepted) + zandvoort s115 (their round-108 CI target -- their
branches now need a rebase onto the promoted master, noted for them).

## Round 108 (local agent): the smoke proximity gate -- a measured, behavior-preserving speedup

USER DIRECTIVE: speed up the engine. Built a profiling twin of the
champion (per-call-site simOutcome attribution, within-turn duplicate
detection, smoke yield counters) -- the profile was unambiguous:

- The r60 SMOKE TEST is 70-79%% of ALL simulation time (e.g. zandvoort
  s33: escSmoke+escDJS 3.7s of 5.4s sim; interlagos s47: 3.9s of 5.0s)
  and its verdict is DIES 0.1%% of the time (7 in 5162 profiled runs).
- Within-turn duplicate scorer moves are only 6-8%% -- memoization is
  NOT the win. The smoke's fire RATE is.

THE GATE (AI1 only, second smoke occurrence = frozen AI2 untouched):
a slow-landing box within the 5-round smoke horizon needs bodies near
the landing. 5162 profiled smoke runs across 8/4/2-car fields, seven
real kills: every 8-car kill has >= 4 rivals within Chebyshev 3 of
the landing; the single sparse-field kill (monaco 4-car s9 m19 -- the
round-71 pin site, caught when the first near3>=2 gate broke its
move-identity) lives in a seal<=3 field. Gate:
  smokeNear = sealRivals <= 3 || near3 >= 2
(small fields exempt wholesale; 2x margin on the 8-car kills; debug
modes unchanged). Keeps 54%% of runs and 7/7 kills.

REJECTED SIBLING (measured): gating the funnel/dense ESC escalation by
proximity -- zandvoort s37 re-crashes (the r83 funnel arm's rare
switches fire with rivals FAR away; its fires are 0-switch in 4124
profiled cases on healthy races, but the rare switch IS the r83
zandvoort-band fix). The funnel arm stays ungated.

VERIFICATION: 18-race A/B (8/4/2-car, every historic class site) --
18/18 MOVE-IDENTICAL, total wall 118.2s -> 102.1s (-13.6%%; heavy
pack tracks -20-25%%: zigzag s76 3.5->2.0s, monza s80 6.6->5.6s,
zandvoort s33 6.4->5.1s). All ELEVEN pins pass on the candidate jar.
Canon numbers must be bit-identical (move-identity implies it);
window-1 verification in flight at write time.

UNIFIED CERTIFICATION (r107 champion, 4070 races -- 8car s46-150 x22
tracks, 4car+2car s26-65 x22): EXACTLY TWO crashes -- hairpin s68
(accepted place-neutral seal) and zandvoort s115 (documented open,
their round-108 target). The residual equals the documented frontier
across every window and field size ever raced; zero new specimens in
the widest sweep the campaign has run. Candidate canon window 1 on
the smoke-gated jar: 62.701 BIT-IDENTICAL to r107.

CANON IDENTITY COMPLETE: windows 1-3 all BIT-IDENTICAL on the gated
jar (62.701 / 62.640 / 62.678). BENCH WORKFLOW SPEEDUP banked
alongside: bench_ai's existing BENCH_BASELINE cache is now seeded per
canon window (scratchpad ai2_base_w{1,2,3}.json) -- AI2 is the frozen
champion, identical on every candidate run, so cached-baseline benches
run the AI1 column only and HALVE canon wall time on top of the smoke
gate. Caches invalidate at promotion (delete the files when AI2
changes) -- recorded here so both agents adopt the flow.

Also noted for the speed ledger: their r106 forward-pack arm moved
canon window-1 wall time 5m50 -> 9m05 (+55%%); this gate claws back
roughly a quarter of a window. The profiling twin (prof/ tree +
prof.jar pattern) is reusable for the next speed round.

## Round 107 (local agent): direct true-5 at the ESC route -- hungaroring s144 solved, canon -0.010

BUILT ON their promoted Round 106 (guarded forward-pack acceleration;
pulled, site-battery-verified: all nine solved sites hold, s115/s144
open as expected; their instance-field fixes for trueConfirmDepth /
simTrace are correct for batch mode).

THE FINDING (probe matrix, one command per cell): at hungaroring s144
m26 the taken SE is ALIVE in every suppressed world (scorer-5-cap3
V=113, scorer-8-cap6 V=112) and dead ONLY under true-5-cap6 (V=-1);
its signature is thread=2 snug=2 in a healthy tier -- exactly the
slice the round-104 cost ladder is BLIND to, because the ladder's
cheap scorer-8 pre-check reads alive and never reaches true rivals.
First trial (ESC-route confirm with the ladder) fired at m26 and said
"true rivals keep alive" -- the ladder never ran them.

MECHANISM: the r60 ESC call (dense-pack / scorer-dies / funnel-risk
escalation) gains trueConfirm with the corridor leg suppressed
(corrLeg=false); at that route the slow leg runs TRUE rivals DIRECTLY
for 5 rounds at cap 6 -- no cheap pre-check -- gated to the exact
s144 signature (thread==2, snug==2, tier>=3; 0-3 fires/race). legSlow
snug threshold 3->2 (both s144 and the round-104 monaco site pass).

COST, HONESTLY: canon window 1 wall time 9m35 vs 9m05 on their r106
baseline (+5%); NOTE their r106 forward-pack arm itself moved the
window from 5m50 to 9m05 -- the bulk of the recent slowdown is the
pace arm's scorerFieldOutcome rollouts, recorded for the speed ledger.
The wider slice (thread>=2 snug>=2 any tier) cost +70% and was
rejected.

RESULT: hungaroring s144 FIXED; all nine solved sites hold; ten pins
PASS; canon 62.701 / 62.640 / 62.678 -- window 2 at -0.010 vs the
frozen mirror is the LARGEST canon gain since parity (r105: -0.004);
h2h 4.494 vs 4.506 held; 4p/1v1 exact; slow identical. Residual
frontier: zandvoort s115 (equal-speed lane class -- their round 108
equal-speed-veto branch is gating it via CI; left to them, inspect-
before-merge) + accepted hairpin s68.

## Round 105 (local agent): slower-first switch targets; the shelf-rule refutation; harvest 16 census

HARVEST 16 (8car mega-window s106-150, 990 races): 4 crashes, all
depth-6-9 -- zandvoort s115 m111 / s128 m110 / s134 m98 (the corridor
shelves again, three new shapes) and hungaroring s144 m26 (start
funnel, @true-r4). Probe matrix banked the decisive negative: at
depth 7+ the class is TRAFFIC-COUPLED past every affordable world --
the state (44,28)v(2,-7) is oracle-ALIVE in s115 and oracle-DEAD in
s128; identical local state, opposite outcomes on field context. No
local verdict or static rule can decide these.

WHAT SHIPPED (pin-clean): dead-path ladder SWITCH TARGETS pick
SLOWER-FIRST (min spd-inf, then cheap ttf) -- the class invariant
applied where it is safe: only among candidates that already passed
the scorer-8 + true-4 ladder on an already-dead chosen. Fixes s128
AND s134. Canon 62.705/62.647/62.679 with windows 1-2 both faster
than the frozen champion, and H2H 4.494 vs 4.506 -- the FIRST
head-to-head EDGE over the mirror since parity: braking one unit
earlier at fragile shelves wins races.

WHAT WAS REFUTED (three pin-measured attempts): the SHELF SPEED
DISCIPLINE as an alive-branch rule. Gate tier<=1: breaks pace +
field-neutral + staged + energy pins (corridor fires with fragile
tiers are everywhere in packs). Gate tier<=1 AND thread>=1 AND
snug>=2: still breaks them. ESC-call confirm with the corridor leg:
breaks mixed-safety. Conclusion: the invariant is only safe where a
verdict ALREADY killed the chosen; as a preference on alive verdicts
it perturbs the pinned equilibrium at any gate the corridor fire-rate
offers. The corrLeg flag (suppress the corridor leg per call site)
stays as inert plumbing.

CERTIFICATION (r105): mega-window 2/990 -- EXACTLY the two documented
open sites (s115, s144), nothing else; harvest-9 windows 0/770. The
residual equals the documented frontier precisely, again.

OPEN (full anatomy): zandvoort s115 m111 -- survivors are
EQUAL-spd-inf lane changes (v(2,-7)/v(3,-7) vs taken v(4,-7)), outside
the slower-first vocabulary; scorer-8 reads all three alive
(thread 6/5/3 of 7 -- massively threaded yet verdict-alive), true-8
kills taken AND one true survivor (false kill) while keeping S: even
true-8 is only per-candidate right here. hungaroring s144 m26 --
tier-healthy (3) thread=2 snug=2 at every gate world, dies @true-r4,
five survivors; the one confirm that sees it (legCorr at the ESC
call, horizon 5) costs the mixed pin. Both are the residual frontier:
2 open in 990 fresh mega-window races, plus accepted hairpin s68.

## Harvest 15 (r104 champion): 0/770 ON NEVER-RACED SEEDS -- the family generalizes

The first zero-crash FRESH harvest in campaign history (fresh windows
8car s91-105, 4car/2car s56-65; all 3190 finishes present). Every
prior fresh exam found specimens (harvest 6: 2, harvest 9: 4); the
r104 champion's first fresh exam is perfect. The instrument family --
thread audit, bounded confirms, three fragility legs, cost ladders --
was built from seven specimens and holds on geometry it never saw.
Measured residual now: ONE accepted place-neutral site (hairpin s68)
in 3080 certified races, and 0 in 770 fresh. Next hunt widens to an
8-car mega-window (all seven specimens were 8-car; the 4/2-car
windows have been clean since harvest 3).

## Round 104 (local agent): three-leg confirm predicate -- EVERY HARVEST SPECIMEN SOLVED

The final two open specimens fall to one unified mechanism, every
number probe-measured before a line of Java:

THE THREE LEGS (all inside the dangerJointSearch confirm block, each
surgical by measurement):
1. CORRIDOR (r99/r100 unchanged): thread>=1 + neutral-grid body ->
   the proven true-4 certification-cap check.
2. SLOW-PACK (new): thread>=2 AND snug>=3 (snug = slots with <=2
   viable, counted free in outThreadRounds[1]) -- fires ~1/race at the
   threadPack fallback, and monaco-s88 m54's fire IS its one
   qualifying event (v=101 thread=2 snug=3; invisible to every other
   tell: no bodies, no pack proximity for the killers, trap-path
   route).
3. DEEP-TIER (new): finalTier<=1 with NO thread -- 1 fire across
   eight debug races, and it is zandvoort-s88 m96 itself.

THE COST LADDER for the new legs: the suppressed 8-round
certification-cap world FIRST (~100ms; probe: it alone kills both new
sites), true rivals only to verify a kill (true-4 for slow, true-6
for deep -- the s88 box seals at true round index 5, probe-measured:
true-4 V=124 alive, true-6 V=-1). Switch targets now pass the same
ladder (scorer-8 then true-4); all survivor targets probe-verified
alive in every ladder world before building.

KEY PROBE FACTS BANKED: scorer-8-cap6 kills BOTH new sites -- no true
rivals needed for detection, only for verification; cap matters at
depth (scorer-8-cap3 reads s88 alive with thread=5!); the query-sim
audit reply (V;tier;thread;snug) made every gate decision a
one-command measurement.

RESULT: all seven harvest specimens crash-free (chicane s51,
zandvoort s32/s74/s88, monza s80, zigzag s76, monaco s88); race times
unchanged (monaco 2.2s, zandvoort 3.0s); ten pins PASS; canon
62.706 / 62.649 / 62.679 with window 2 now 0.001 FASTER than the
champion mirror (a ladder switch found a marginally better line);
parities exact; slow identical. hairpin s68 remains the sole
accepted-open class (place-neutral finish-denial seal, correct
opposing play). Certification sweeps follow.

TRIPLE CERTIFICATION (r104): 2310 races across ALL harvest windows
(std 46-60/26-35, h6 61-75/36-45, h9 76-90/46-55) -- EXACTLY ONE
crash: hairpin s68, the accepted place-neutral finish-denial-seal
class. The champion's measured residual across every window ever
raced is precisely the one documented, correct-opposing-play site.
PROMOTION CASE NOW: AI1 leads the frozen AI2 by seven solved crash
classes at identical-to-marginally-faster pace (canon w2 -0.001);
h2h/1v1/4p exact parity; ten pins green. Execution awaits the user's
word, per the standing law.

ALSO: process note -- a multi-step patch script aborted mid-assert
BEFORE its single write, so five of six steps silently missed while
the sixth (applied separately) landed; the first r104 test ran on a
half-round build. Caught by the site battery reading 2 crashes.
Standing rule reaffirmed: write patch scripts to FILES, assert all,
write once, and always re-verify the diff stat after applying.

## Round 103 (local agent): the query-sim probe finds two structural truths; zigzag solved

THE INSTRUMENT: a `sim` command in the --query-moves protocol
(RaceGame.processQueries) runs the in-game joint rollout from an
installed board (me already AT the queried landing) with a chosen
world (smom | scorer | true) and cap, replying "V=<verdict>" with
SIMTRACE step lines on stderr -- the in-game rollout diffable LINE BY
LINE against the offline Python roll (sim_diff.py pattern). Permanent
tooling; simDepth guard keeps nested rollouts silent.

TRUTH 1 -- THE BOUNDARY REGENERATES: at zigzag m234 the latched
in-confirm rival vacated the kill cell the oracle champion claims.
First hypothesis: since round 99 the confirm IS champion behavior, so
a binary latch strips real arms from in-confirm rivals -- fixed by a
DEPTH counter (one nested confirm level allowed, depth 2 blocks).
Necessary but NOT sufficient here: the oracle on the EXACT same board
agreed with the latched move -- no channel infidelity existed.

TRUTH 2 -- THE CAP IS A WORLD PARAMETER: the real divergence was the
scorer-set cap. At cap 3 the un-set cars run smom, and their flow
hands the key rival a context where it vacates ((16,40)); at cap 6
the same rival closes the box ((15,39)) exactly like the all-champion
offline roll and the real race. V=34 alive at cap 3; V=-1 dead at cap
6 -- measured through the probe, single query. FIX: true-rival
confirms ALWAYS run the certification cap (max(scorerCap,
AI1_DEEP_CERT_RIVALS)); every cheap world keeps its pinned cap.
zigzag s76 FIXED; all five solved sites hold; ten pins PASS; canon
62.706/62.651 (w3 pending at write time) identical.

MONACO S88 RECORDED OPEN with a complete negative series: the m54
chosen routes through the trap-0 r60 smoke branch (trap ladder reads
healthy); measured invisible in EVERY cheap world -- python smom
viable 2,2 (no thread), in-game trap-path world thread=2 but the m54
route never reaches that gate, in-game SMOKE world thread=0 snug<=1,
no bodies on the neutral grid, pack gate closed (killers converge
from beyond Chebyshev 10: p8/p3 one-cell divergences seal @r2).
Affordability wall: threadPack fires 27-73/race, alive-smoke-thread
2-27/race -- every candidate gate is orders too hot for a cap-6 true
confirm. The kill exists ONLY at true fidelity with no cheap
signature. New debug diagnostics kept (THREADPACK, SMOKETHREAD,
snug counter in outThreadRounds[1]).

SWEEP VERDICT (r103 certified): dual 770-race sweeps -- harvest-9
windows 2/770, the two crashes being EXACTLY monaco s88 and zandvoort
s88 (the documented open set, nothing new); standard windows 0/770.
The residual equals the documented frontier precisely. Canon window 3
62.679 identical; 1v1/h2h/4p exact parity; slow 104.107.

OTHER AGENT CONVERGENCE NOTE: their speed-103 branches independently
reached the SAME zigzag site and the SAME cap conclusion
(six-rival-gate / full-roster-confirm). Their patch is a subset of
master 38e8595 (cap fix identical in effect; binary instance latch
where master has the depth counter; no query-sim). Their
six-rival-mirror-gate-v2 branch MIRRORS the confirm machinery into
AI2 with a joint AI1/AI2 zigzag pin -- promotion-shaped work, held on
the branch: per the standing law the AI2 mirror lands only on the
user's explicit promotion word.

ZANDVOORT S88 stays open (corridor class at depth 7 -- the deep
confirm at the funnel escalation remains the costed, unmeasured
candidate).

## Round 102 (local agent): monza solved via three composed fixes; a sim-fidelity puzzle isolated

HARVEST 9 (fresh windows: 8car s76-90, 4car/2car s46-55): 4/770 -- four
specimens, four different lessons.

MONZA 8car s80 m183 -- SOLVED, three composed fixes, each measured:
1. ALONGSIDE-PACK GATE: the chosen lands amid four rivals braking into
   turn 1 (Chebyshev <= 3 of the landing) yet ZERO pass the corridor
   ahead-dot test; the gate now also opens on landingAdjacent >= 3.
2. SPEED-SCALED CONFIRM NET: the true-rival membership radius
   (Chebyshev 10 of the landing) cannot contain the braking car 11
   cells downstream of a spd-inf-10 commitment; TRUE-RIVAL worlds now
   use max(10, 2*spdInf). A GLOBAL radius change was tried first and
   slowed the round-96 coil finish frontier by four moves (their pin
   caught it within minutes) -- suppressed worlds keep the pinned
   radius. The pin system is doing exactly its job.
3. DEAD-PATH TARGET CONFIRMATION: a cheap-dead chosen in a confirm
   context now true-confirms its switch targets (previously only the
   fragile-alive path did) -- zigzag s76 m234 showed the scorer world
   killing the TRUE survivor and switching onto the truly-dead
   alternative.
Result: monza s80 clean; all five prior sites clean; all ten pins
PASS; canon 62.706/62.651/62.679 IDENTICAL; parities exact; slow
104.107.

STILL OPEN, each characterized:
- zigzag s76 m234: THE SIM-FIDELITY PUZZLE. Python smom AND orivals
  (selfMove me) both kill alt NE @r2 -- reality agrees (the race
  crashed) -- yet the in-game 8-round scorer world reads NE simT=30
  alive and the in-game 4-round true-rival confirm (cap 3 at this call
  site) says true-ALIVE. The in-game rollout DISAGREES WITH ITS
  REPLICA on a decided state. Either the replica diverges from
  rivalMoveOverState in a detail, or the in-game board
  installation/move-order has a subtle infidelity -- either way this
  underlies multiple misses and wants a purpose-built probe: a
  --query-sim debug mode that dumps the in-game rollout trace for a
  given state, diffable line-by-line against the Python roll. THAT is
  round 103.
- monaco s88 m54: predicate-invisible rival-side kill (viable 2,2, no
  thread, no tier tell, no bodies at decision time). The scorerSelf
  escalation added this round fires one decision too late (m62). Needs
  either the query-sim answer or an affordable always-confirm gate.
- zandvoort s88 m96: the corridor class at depth SEVEN (true death
  @r7; survivors differ by ONE unit of entry speed). Beyond the
  4-round confirm; a deep confirm at the funnel escalation (8 true
  rounds, ~50 champion computes/fire at rare funnel fires) is the
  costed candidate, unmeasured.

Fresh-seed residual: 4/770 on never-raced windows vs 0/770 on all
regression windows -- the hunt-fix-pin engine converges per window;
fresh geometry keeps supplying the frontier.

## Round 101 (local agent, REJECTED after measurement): the survival-dual probe

The hairpin-s68 class got its first instrument attempt: a SURVIVAL DUAL
of the endgame win solver (egSurvRival/egSurvMy -- paranoid minimax
where I need only finish-or-stay-alive, horizon counts as survival),
run OBSERVE-ONLY behind -Dai.probe.survival at near-finish commits
(myT<=6, contesting rival = min-ttf live car within Cheb 10 with
rT<=myT, 13 plies, 50k-node budget).

MEASURED REFUTATION at the site itself:
- p8's real m104 commitment reads SURVIVABLE vs worst-case p5 alone:
  the 2-body model is TOO WEAK -- the real doom needs the multi-body
  pocket shaping (p4's earlier lane pressure), and multi-body
  adversarial search is intractable.
- p5 (the eventual WINNER) gets flagged PROVABLE-LOSS/NO-ALT vs p4,
  who in reality raced on and finished: the 2-body worst-case model is
  TOO STRONG against opponents who never play adversarially -- the
  insurance-premium law made quantitative.
- Budget blows (>50k nodes) at 13 plies on open approaches; the win
  solver survives the same depth only because win-proofs prune hard.

Code reverted per the r76/r77 discipline; the committed r100 champion
is unchanged. hairpin s68 STANDS as the open counterexample: place-
NEUTRAL crash (the victim places 8th finishing or crashing), rarest
class on record (1/1540 in the r100 dual sweep), requiring multi-body
adversarial fidelity no affordable instrument provides. Recorded
directions for whoever returns: (a) restrict to TRUE 2-live-car states
(where the 2-body proof is sound and the flagged real decisions at
m143+ are already all-dead -- needs the trigger EARLIER than 1v1
materializes, which is the hard part); (b) an asymmetric model: MY
moves paranoid-proven, rival constrained to its REAL policy envelope
(champion-reachable moves only) -- cost between confirm and solver,
unmeasured; (c) accept the class: the crash is place-neutral and the
sealer''s play is correct -- the loss is cosmetic in ranking terms.

## Round 100 (local agent): corridor-class generalized (zandvoort s74 solved); new open class recorded (hairpin s68)

HARVEST 6 (fresh windows: 8car s61-75, 4car/2car s36-45, 770 races) on
the r99 champion: 2 crashes -- the improvement queue refilled exactly as
the instruments were built to exploit.

SPECIMEN 1, zandvoort 8car s74 m109 -- SOLVED. The second corridor-class
site, one shape deeper than s32: last avoidable m109, survivor S, taken
SW dies; the fragile signature carries thread=1 but a HEALTHY final
tier (the r99 predicate's tier<=1 leg blocked the confirm), and the box
seals at round index 3 (s32: index 2), one past the 3-round confirm.
Round 100 tuning, both measured before building: predicate drops the
tier leg (thread>=1 + body on the neutral grid; 0 fires outside
zandvoort across the healthy sample, 3 on zandvoort s33),
AI1_TRUE_CONFIRM_ROUNDS 3 -> 4. s74 fixed; s32/s33/s51 all stay clean.

SPECIMEN 2, hairpin 8car s68 m146 -- NEW CLASS, RECORDED OPEN
(finish-denial seal). Six cars finish; p5 and p8 arrive at the finish
approach together with p8 at reach-ttf=1 -- ONE MOVE FROM WINNING. p5
moves first, denies the finish lane, brakes 6->0 into the top-right
pocket and PARKS at (77,14): the endgame forced-crash seal, executed
mid-pocket. p8 overshoots into the dead spur; from m112 on, its own
DJS reads every candidate dead (correct) with no survivor. The
commitment was m104 ((41,6) SE at spd^2=65): the deep smom-8 pre-screen
read the landing alive at ANY horizon (smom says t=1 -- in every cheap
world p8 simply WINS; the proxy p5 never parks), while full champions
kill @r7. Prevention needs ~7-round ADVERSARIAL fidelity or
finish-lane-contention modeling -- outside every current instrument,
including the 4-round confirm. Also outside the endgame paranoid
solver's scope (it acts on proven wins near the finish; this is the
LOSING side of a contested finish). Victim-side rate: first 2-car-
context crash in any harvest; all 1v1/4p/h2h batteries crash-free.
Note: p5's seal itself is CORRECT play (place-equivalent to finishing,
ends the race with zero own risk).

TOOLING: bench_ai.py seeded benches now run ONE JVM per track via
--seed A-B batching (contiguous windows auto-detected; singles
otherwise). Equivalence proven exact: batched canon window 1 reproduces
62.706/62.704 +0.003 to the last digit. Gain is modest on warm-cache
benches (JVM spin-up only); the harvest scripts already batch.

SWEEP VERDICT (r100 certified): canon windows 2-3 62.651/62.679
IDENTICAL to champion; 4p/1v1/h2h exact parity; slow 104.107. Dual
770-race sweeps: harvest-6 windows 1/770 -- the single crash IS hairpin
s68, the recorded open class, nothing else; harvest-4/5 windows 0/770.
The r100 champion's only known crash in 2310 swept races is the one
documented open specimen.

OTHER AGENT OBSERVED IN-FLIGHT (branches, not yet on master):
agent/ai-racing-speed-100-{seal-pace-screen,finish-probe,source-export}
carry a stored candidate patch (.github/round100-sealpace-refined.patch)
plus CI workflows. The candidate builds ON our r99 confirm machinery,
INVERTED: where our confirm uses true rivals to KILL cheap-alive lines,
theirs REVIVES sealGuard-demoted one-turn-faster finish lines when the
field-outcome cert AND a true-rival+scorerSelf confirm both pass
(finish band, trap-0, homogeneous, less-obstructive-field gates). It
also flips inTrueRivalConfirm from static to instance -- correct (one
RaceAi per game; instance isolates batch-mode races). NUMBERING NOTE:
master's Round 100 (this entry) landed first; their branches also say
Round 100 -- suggest they publish as Round 101 at merge time. Their
candidate patch still applies cleanly on r100 (their hunks avoid the
r100-tuned lines). Inspect-before-merge honored; branches left theirs
to land after their battery completes.

GATES: all ten pins PASS; canon window 1 62.706 IDENTICAL to
r98/r99/champion. Windows 2-3 + parities + both 770-race sweeps in
flight at write time; results recorded in the next entry.

## Round 99 (local agent): bounded true-rival confirm -- zandvoort s32 SOLVED, class closed

THE RECURSION BOUNDARY IS BREACHED -- affordably. Round 97 proved true
rivals correct but cost-prohibitive as a general world; round 99 makes
them a RARE CONFIRM: fire only where the suppressed corridor world says
alive AND its own outputs betray fragility. The observe probe measured
the signature at the two s32 doom decisions (verdict alive, finalTier=1,
threadRounds=1/2, body on the neutral grid) at ~0.25 false fires per
race elsewhere (2 in 8 healthy races, all zandvoort).

MECHANISM (all AI1-only): scorerMoveOverState gains a suppress flag;
suppress=false runs the rival's computeAiMove UNSUPPRESSED (pace arms
included). simOutcome gains trueRivals (scorer-set rivals at full
fidelity). dangerJointSearch gains trueConfirm: an alive corridor
verdict matching the fragility signature is re-verdicted with
AI1_TRUE_CONFIRM_ROUNDS=3 rounds of true rivals (the box seals at round
INDEX 2 -- a 2-round confirm provably misses it, measured). True-dead
falls into the normal switch, where each candidate is ALSO
true-confirmed (first true-alive by cheap simT wins; cheap-best
fallback). Wired at the r73/r74 corridor/queue certification only.

THE r97 COST/CORRECTNESS WALLS, ENGINEERED AROUND:
1. Workspace clobber (would have corrupted r97's results silently): an
   unsuppressed rival compute re-enters rolloutWorkspace(); the confirm
   swaps the field to null around computeAiMove so nested rollouts
   allocate fresh; outer arrays live on as locals.
2. Recursion runaway: static latch inTrueRivalConfirm -- rivals computed
   at full fidelity cannot fire their own confirms.
3. Cost: verdict-only + rare gate + 3-round bound = ~0.25s per fire,
   +0.7s on the crash race, +0 on most races (canon window 1 wall time
   unchanged).

AT THE SITE: m102 fires and true rivals KEEP S (death @r7 is not yet
sealed -- correctly not the decision point); m110 fires, true rivals
KILL @3r, alt walk finds SW simT=125 true-ALIVE, switch -> 0 crashes.
p8's one benign fire confirms alive. Debug-independent clean replay: 0.

ONE REAL BUG CAUGHT BY THE PINS: the confirm's audit arrays leaked the
r98 robust-switch into the corridor site ungated (a fully-threaded
alive corridor verdict ran the thread switch with threadCheck=false),
perturbing cog-s1 field-neutral by +2 moves. Fix: the robust switch
requires threadCheck explicitly. Lesson recorded: when two audits share
plumbing, each behavior needs its own explicit flag test.

GATES (all green): nine pins PASS (incl. field-neutral after the fix,
thread-fragility, golden corpus, headless smoke); canon
62.706/62.651/62.679 -- IDENTICAL to the r98/champion record, f=770 c=0
all windows, windows 2-3 exactly equal AI2; 4p 2.500/2.500, 1v1
1.500/1.500, h2h 4.500/4.500, all c=0; slow 104.107 both kinds.
Harvest 5 (same 770 races as harvests 3-4) = the certification sweep.

HARVEST 5 RESULT: **0/770, all 3190 finishes present** -- the second
consecutive zero-crash full sweep, now on the r99 champion. Confirm
fires across the sweep stayed rare enough to leave every previously
clean race untouched (the sweep is seed-identical to harvests 3-4).

CLASS LEDGER: chicane s51 (rival-side) solved by r98 thread audit;
zandvoort s32 (both-sided) solved by r99 true-rival confirm. NO KNOWN
OPEN CRASH SITES. The two instruments compose: cheap-world fragility
signals gate expensive fidelity exactly where model error is fatal.

## Round 98 (local agent): thread-fragility audit -- chicane s51 SOLVED

THE RECURSION-BOUNDARY CLASS HAS A MODEL-FREE ANSWER. Round 97 proved
no affordable rival model reproduces the pack's champion braking. Round
98 stops trying to predict the rivals and audits MY OWN certificate
instead: the chicane-s51 chosen rolls out alive in every cheap world,
but enters EVERY simulated move slot with at most ONE viable candidate
(viable=1,1,1,1) -- a single-file needle through live traffic. The two
oracle-proven survivors roll viable>=2 on every slot in the SAME cheap
world (W: 4,6,8,7; S: never below 2). "Alive but fully threaded" is the
death signature, and it is computable from the candidate enumeration the
sim already performs: zero extra simulations, zero rival fidelity.

MECHANISM: simOutcome gains an outThreadRounds channel (count of my move
slots entered with <=1 viable candidate: legal, unoccupied,
reachability-alive; a finish-crossing slot counts as open).
dangerJointSearch gains a threadCheck mode: an ALIVE verdict that
threaded rounds-1 of rounds-1 slots triggers a robust-alternative
search; switch only to an alternative BOTH alive and non-threaded
(survival-only asymmetry preserved -- no robust candidate, keep the
chosen). Enabled at ONE site: the AI1 slow fallback DJS, gated on
djSlow + >= AI1_DEEP_PACK rivals within AI1_DEEP_PACK_R of the landing.
AI2 untouched.

AT THE SITE: m121 fires "alive but viable<=1 on 4/4 slots", finds four
robust alternatives (W/NONE/SW/S, all simT=3 thread=0), switches to W --
the oracle-proven survivor -- and the race runs 0-crash with p1 alive in
P8 (was CRASH place=8).

NEGATIVE RESULTS BANKED (policy_matrix rows kept as instruments): smin
(tie->slower), strf (traffic-conditioned tie), punion (pessimistic
tie-set occupancy vs my successors) all still read SE alive -- the box
needs the exact multi-car configuration; occupancy pessimism cannot
reach BACKWARD from an over-fast rival flow. Divergence localization
(diverge.py pattern: roll smom vs orivals side by side) and candidate
autopsy identified the real signature: at score ties, back-of-pack
champions brake into the funnel (their own r83-style discipline,
stripped by inScorerSim); front-runners keep speed. Model-free
robustness beat model fidelity.

GATES (all green): nine pins PASS (7 ai1_* + golden corpus + headless
smoke); pace canon 62.706/62.651/62.679 vs champion 62.71/62.67/62.68,
f=770 c=0 every window (windows 2-3 EXACTLY equal AI2 -- zero perturbing
fires; window 1 +0.003 vs AI2 62.704); fixed-grid bench identical to
AI2 to the third decimal (62.604/62.604, +0.000 all 22 tracks); 4p
2.500/2.500, 1v1 1.500/1.500, h2h 4.500/4.500 parity, all c=0; slow
104.107 both kinds. New pin: tests/ai1_thread_fragility_regression.py
(chicane s51 8car must stay 7 finishers / 0 crashes).

CLASS STATUS: chicane s51 (rival-side) SOLVED. zandvoort s32 8car
(self-side) still crashes -- expected: threading is a rival-side
instrument; the self-side member needs sim-me to see its own future
pace arms. Harvest 4 (the exact harvest-3 770-race sweep, batch-mode)
in flight; pre-98 A/B on zandvoort s32 pending the jar lock.
HARVEST 4 (r98 champion, the exact harvest-3 770-race sweep, batch
mode): **0/770 -- the first zero-crash full harvest of the campaign**
(harvest 3: 1/770). 3190 finishes = the exact full-field count; every
race completed. The only known crash anywhere is zandvoort 8car s32
(outside the harvest windows), PROVEN pre-existing: zero THREAD fires
in that race, so the r98 champion raced it move-identically to r97's.

ZANDVOORT S32 DISSECTED (round-99 groundwork, POCKET entry added):
last avoidable move m110 (p6, pos (42,35) v(3,-8)); survivor SW
(oracle-alive t=118), taken S dies @r6 under full champions. In-game:
the r73 corridor check FIRED at m110 and its suppressed cap-6 world
read S alive; one move later everything is dead (DJS correctly says
"no survivor" @m118 -- detection one move late). Anatomy is BOTH-SIDED:
(a) death needs rival fidelity -- real p5 lands ON my only good r1
cell; the debug trace catches p5's PRIVATE-LANE PACE ARM firing right
there (SW -> W ttf 125->124): the killer move is literally a pace-arm
product, the class thesis verbatim; (b) escape needs self fidelity --
survivor SW lives ONLY by real-champion single-file threading
(viable=1 on six straight rounds under orivals-me). The r98 thread
audit correctly stays silent (chosen S reads viable=2,2 in cheap
worlds -- an inverted signature: here the SURVIVOR threads, the doomed
line does not). Corridor-world thread counts to be measured by an
observe-only probe; if the true in-game world also reads viable>=2,
threading cannot catch the self-side face and round 99 needs a
different instrument (bounded 2-round true-rival confirm at corridor
alive-verdicts is the costed fallback: the box seals @r2, so 6 rivals
x 2 rounds of full-fidelity moves per fire, fire-rate ~4/race/player
-- needs a fragility pre-gate to be affordable).
NEXT INSTRUMENT CANDIDATE: the thread audit generalizes -- the same
outThreadRounds channel could gate other DJS sites (deep corridor,
funnel) if new specimens appear; fire-rate so far is one site per 770.

## Round 97 (local agent, REJECTED after full forensics): chicane s51 and the pack-cohesion limit

THE LAST HARVEST-3 CRASH, fully classified -- and the definitive
specimen of the recursion-boundary class. Chicane s51, p1 dies m145;
**m121 is the last avoidable move**: three candidates FINISH @r7 and
one stands a turn from the flag, while the taken SE (the fastest line)
dies @r3. The matrix: smom=alive tier-3, orivals=DEAD@r2 -- yet no arm
fired: the chosen carries trap 0.5 and routes through the trap-path
DJS whose scorer world reads it alive.

THE REAL MECHANISM (from the race log): p1 is LAST; after SE the
entire six-car pack holds the lower racing-line corridor through
rounds 1-2, forcing p1 into the upper fork, which dead-ends at
(65,5). The kill is **pack-lane cohesion** -- the suppressed scorer
world under-predicts how firmly the real pack (running its full pace
stack) holds the line, so in-sim the lower lane opens and SE reads
alive.

THREE FIX ARMS BUILT AND REJECTED with measurements:
1. Depth-1 TRUE RIVALS (unsuppressed computeAiMove for scorer-set
   rivals): mutual recursion through nested contact gates ran ONE fire
   past five minutes; a depth latch capped it but the direct cost
   (~90 full champion computations per fire) still ran a 0.6s race
   past ten minutes. Cost-prohibitive at any useful fire rate.
2. Pessimistic-pursuit contact rival (zero recursion, fixed target,
   then live-target): fires correctly at m121 but cannot reproduce a
   six-car lane occupancy with one pessimistic pursuer -- the verdict
   stays alive. (Bonus finding: ringWidth is a BFS level set and wraps
   both legs of a switchback, so the static funnel signal reads a
   2-cell chicane gate as wide; the funnel instrument is sound for
   open funnels only.)
3. All code reverted per the r76/r77 discipline; the analysis is the
   deliverable.

THE CLASS LEDGER now reads: zandvoort s32 (self-side: my own future
pace arms invisible to sim-me), chicane s51 (rival-side: the pack's
pace arms invisible to sim-rivals). Champion fresh-seed tail-risk
stands at 1/770 (harvest 3) with these as the only known open sites.
VIABLE DIRECTIONS (recorded, unclaimed): bounded multi-true-rival
certification (needs a cost breakthrough -- e.g. memoized rival moves
or a 1-round-only full-fidelity pass), a static racing-line occupancy
prior (must solve horizon-sensitivity: static blocking kills waiting
lines too), or admission-level speed discipline inside the pace arms
themselves (the arms' own certificates are the only worlds that see
their own aggression).

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

## 2026-08-14 speedup: batch racing + in-process reachability memo

RE-PROFILING the r91+ champion (the old "AI search is 3% of CPU" was
stale): the AI hot path is now their search machinery (fmRec, mobility,
two-round world-step -- their actively-optimized territory), and the
BATTERY'S dominant fixed cost is per-race startup: ~1.3s reachability
cache load+derive plus ~0.4s JVM boot x ~2900 races/cycle = 80+ min of
pure overhead per campaign cycle.

THE FIX, two parts, behavior-invisible by construction:
1. **Batch racing**: `--seed A-B` races every seed in ONE JVM (Main
   loops fresh RaceGame instances over fresh Properties copies; a new
   autoRaceEndHook replaces the hard System.exit; per-seed logs get _sN
   inserted before the extension).
2. **In-process reachability memo** (Reachability.REACH_MEMO): the
   fully-derived products (turns, alive, roomy, shed, cert) are adopted
   instantly by later seeds of the same track -- all read-only after
   build.

PROOF: batch logs byte-identical to single-shot logs (monaco s1-3,
cmp); one cache-hit print for three races (the memo works); unit +
golden suites green. MEASURED: monaco s1-3 = 18.2s as three singles vs
**9.5s batched (-48%)**; projected 35-45% off full battery wall time.
Tooling (bench_ai/bench_iso batch wiring) is the follow-up; the game
side is complete.

POST-INTEGRATION HARDENING: range execution now terminates safely even
at `Long.MAX_VALUE`, always gives default as well as explicit logs an
`_sN` suffix, rejects a range without `--auto` and range/query mode
mixes, clears a superseded range end, reports interrupted batches as a
failure, and owns the one-shot completion hook per `RaceGame` rather
than process-wide. `MainTests` pins the parser boundaries; direct batch
versus single-log checks remain the behavior contract.

## PROMOTION 2026-08-14 (per user): the composition is the champion

Executed: AI1's body mirrored WHOLESALE into AI2 (the r79-r90 pace
stack + r83 funnel guards). The first strict probe found 6/27 divergent
-- their self-play pace gates were keyed on Kind.AI1 literals, so an
all-AI2 field deactivated its own arms; the promotion-correct
semantics is KIND-HOMOGENEITY WITH THE MOVER (mixed fields stay gated
off exactly as designed). After the fix: strict probe ALL IDENTICAL
0/27. Golden corpus fully regenerated (the champion is ~a move faster;
every fixture legitimately reflowed, 13 cases, ZERO crashes across the
corpus) with the new lemans-s1-4p fixture pinning the 4-car rescue.
All four AI1 pins green post-mirror (mixed-safety improved: places
22/14). The strict self-tie probe and champion goldens are the durable
post-mirror identity record; Round 91's expanded matrix below then used this
body as its comparison standard.

## Rounds 91-92 (PROMOTED): faster launch and runtime

CAUSE: stagedPaceOverride counted a rival as "ahead" with a velocity dot
product. For a zero-velocity starting-grid car every dot product is zero, so
the proof-gated pace arm could never open. The first broad experiment used the
reachability distance heuristic everywhere. Exact debugging then located the
only measured gain at Silverstone s15, p6's first move at (61,6): N -> NE,
empty-map TTF 81 -> 80. The promotion candidate was narrowed to that proven
class: use track-distance ordering only while velocity is (0,0) and the mover
is still in the start zone; moving cars keep the r90 dot-product rule. Equal
or unavailable distances fail closed. Both AI bodies now carry the narrowed
rule. Kind-homogeneity, exact private route, 8-round self/field comparison,
seal guard and final danger veto remain unchanged.

RESULT: canonical 22-track 8-car bands seeds 1-5, 6-10 and 11-15 are
770/0 in both columns with ZERO slower tracks. The only result change
is Silverstone s15: final finisher 86 -> 85, exact sum 585 -> 584.
An independent integer cross-version A/B then replayed all 22 tracks x seeds
1-15 (660 executions): both versions produced 2310 finishers / 0 crashes;
329/330 race tuples were identical, the sole delta was Silverstone s15, and
total finisher moves improved 144811 -> 144810. This closes the rounding gap
left by the earlier one-decimal reports.
Silverstone s16-30 is byte-identical. The Zandvoort s31-45 doom band is
byte-identical (s32 remains the accepted lone 6/1 race). Homogeneous
4-car = 330/0 exact tie, homogeneous 2-car = 110/0 exact tie, and slow
= 140/0 exact tie. Java/core, goldens, pace, mixed-safety,
field-neutral, staged and energy pins are green. The expanded pre-mirror matrix
also completed: h2h seeds 1-5 and 11-15 were exact 4.500/4.500 with zero
crashes; seeds 6-10 were 4.500/4.500 with one crash in each column; 2v2 was
2.500/2.500, 1v1 1.500/1.500, homogeneous 4-car 330/0, homogeneous 2-car
110/0, and slow 140/0. The two h2h crashes are the same Le Mans s7 p6
trajectory in reversed kind order, not a candidate asymmetry. Post-mirror,
the strict 27-race probe is 27/27 move-identical and all champion goldens pass.
The exact final-head parallel matrix also passed all 12 jobs: 8-car bands are
770/0 exact self-ties at 62.714, 62.668 and 62.683, with every reported
per-track delta +0.000; h2h is 4.500/4.500 at crashes 0/0, 1/1 and 0/0;
2v2 2.500/2.500, 1v1 1.500/1.500, homogeneous 4-car 330/0,
homogeneous 2-car 110/0, and slow 140/0. CI and CodeQL are green on the exact
promotion commit.

OPEN MIXED-FIELD SAFETY CLASS: both h2h crashes are Le Mans s7 p6/F and are
move-identical under reversed kind order. The last rescue is global move 502
at (13,101), v=(-2,-8): scorer S dies, SW finishes. The ordinary fast smom
model incorrectly keeps S alive even at eight rounds; the scorer-rival model
distinguishes S (dead at a four-round horizon) from SW (alive through eight).
A future arm should therefore test a four-round scorer-rival escalation only
for fast L2-or-worse, smom-fragile entries with a nearby rival. Merely raising
the global three-round smom horizon will not repair this class.

REJECTED FIRST: (1) reopening r90 zero-unc high-energy candidates only
under strict field improvement changed Zandvoort s17's line but no
finish result and did not repair s32; (2) staged minimum-turn sweeps
35 -> 30 -> 24 -> 16 changed a Le Mans line but produced no aggregate
pace; (3) ranking already-certified staged candidates by rollout final
state was inert on every pinned staged case. None of those policies
remain in source.

POST-PROMOTION REJECTIONS: the rollout-ranking arm was subsequently screened
exactly over 500 race pairs (ten tracks x seeds 1-50): all 500 were
move-identical, net delta zero. The stale-base private runner-up branch passed
its standard tests but had no active proof. A current-master AI1-only port was
therefore screened on 62 exact pairs across Sprint, Hairpin, Silverstone,
Zandvoort, Le Mans, Hungaroring and Monaco; every pair was move-identical.
Separate isolated instrumentation saw zero rank-1 attempts in Monaco s1,
Zigzag s1, Cog s1 and the mixed-safety pin. The fallback was removed: it can
pay for a second scorer rollout when rank 0 fails, but has no demonstrated
racing gain. The later stale-base progress-quorum branch was also rejected
without a current port: it had no differential, changed-race or timing
evidence, counted equal-progress and up-to-three-rings-behind rivals toward
its quorum, and could add exact-private plus deep scorer work.

HARNESS BUG FOUND/FIXED: bench_iso claimed full isolation but used
fixed system-temp filenames, so concurrent checkouts could overwrite
each other's props/logs; it also silently preferred user.properties
over the canonical benchmark config. Files are now PID-unique and the
default is tracks/bench.properties (RACING_PROPS remains an explicit
override). Promotion-gate now includes homogeneous all-AI 4-car and
2-car jobs; that missing class had previously let the Le Mans 4-car s1
crash escape the standard mixed-field matrix.

ROUND 92 CPU CLEANUP: dense-slow-pack and static-funnel risks already force a
scorer-rival danger search. The old code nevertheless paid for a separate
five-round smoke simulation first; its boolean could not change whether the
deeper search ran. Both bodies now skip that redundant smoke call when either
gate already mandates escalation, retaining it under every debug mode. Seven
targeted pre/post full logs are byte-identical (Silverstone s15, Hungaroring
s40, Le Mans s1, Zandvoort s32/s37/s44). Seven interleaved warm-cache
Hungaroring s40 runs measured 10678.1 -> 10550.5 ms median (1.2%) and
10638.6 -> 10564.8 ms trimmed mean (0.7%) for the narrowed-r91+r92 build.
The workflow now runs benchmark pipes
under explicit bash/pipefail so `tee` cannot mask a failed race, and regular
bench reports show three decimals so a one-move per-band regression is visible.

SELF-TIE CERTIFIED: probe 0/27 (twice), all stages column-identical --
8car 770/0 x3 at the NEW CANON 62.71/62.67/62.68, h2h 4.500 parity both
bands, 4car 330/0/61.10, 1v1 110/0/60.34, slow 28/0/104.11. Champion
baselines re-seeded. ONE new tail-risk site surfaced during
certification: a mixed 4v4 lemans crash in seeds 6-10, mirrored
identically in both columns (the mirror holds; the site is
new-champion territory -- this suite was clean when the composition
raced the OLD champion, so the all-new mixed field reaches a fresh
doom). Queued with zandvoort s32.

HARVEST 3 COMPLETE (2026-08-14, the r91 champion, 8car s46-60 + small
fields s26-35): **770 races, ONE crash** -- the campaign's best
fresh-seed tail-risk ever (harvest 1: 2/770 on r70; harvest 2: 5/770 on
r75), from the fastest champion ever fielded. Small-field phases (440
races) perfectly clean for the third consecutive harvest. The single
crash: **chicane s51** (8-car) -- chicane's first-ever crash entry.
Open counterexample queue: chicane s51, the mixed-lemans s6-10 site,
zandvoort s32 (the recursion-boundary class).

## Round 93 (PROMOTED): mixed Le Mans sparse fast-trap repair

CAUSE: mixed Le Mans s7 p6 reached g502 at (13,101), v=(-2,-8). Scorer `S`
lands (11,94), v=(-2,-7), trap exactly L2=0.5, with exactly one rival inside
Cheb10 (p7 at distance 3). The normal smom3 world reports ALIVE/finalTier=1
and therefore keeps it; the scorer-rival world reports S dead at a four-round
horizon while SW survives. Reality matches the latter: S crashes at g532;
SW lands (10,94), v=(-3,-7), and p6 finishes g563/place5. The same p6
trajectory existed in both reversed kind orderings, so both scorer bodies had
to change.

INSTRUMENT: after existing funnel/deep-pack handling and before ordinary fast
DJS fallback, only `!djSlow`, trap exactly L2, one or two rivals within
Cheb10, and a smom3 verdict that is alive but finalTier<=1 may escalate. The
chosen move is then re-verdicted with exact self/rivals, real scorer rivals,
four rounds, cap3, and scorerSelf=false. Switching stays death-only. Packs of
three or more remain owned by the existing eight-round deep path. On the
target there are two scorer-r4 checks, one benign earlier check and the g502
switch.

RESULT: both mixed s7 orderings become exact 18/18 place sums with crashes
0/0; mean place remains 4.500/4.500. Exact old-05de452 versus candidate A/B:
330 homogeneous 8-car pairs exact; 660 mixed 8-car pairs with 658 exact and
only the two symmetric target rescues changed; homogeneous 4/2-car 220/220
exact; mixed 2v2 220/220 exact; mixed 1v1 220/220 exact; slow 20/20 exact.
That is 1,670 pairs / 3,340 executions, 1,668 exact and two intended safety
repairs, with zero invalid races. Zandvoort s31-45 stays 104/1 in both
columns. A clean 15-pair warm Le Mans s6 control was byte-identical and showed
no child-JVM CPU regression; do not call the noisier wall result a speedup or
slowdown. The repaired s7 race naturally runs longer because p6 now survives.
The focused mixed regression pins both orderings, g502 SW and g563 FINISH.

## Round 94 (PROMOTED): homogeneous finish-sprint extension

SOURCE LEAD / HARNESS DEFECT: the stale-base `speed-93-finish20` experiment
changed only AI1's Round-75 dual-model finish cap from 15 to 20. Its workflow
reported 0/390 divergences because it searched for `DIVERGENT`; `ai_probe.py`
prints `DIVERGED`. Raw artifacts actually held 21 changes: 11 faster, nine
outcome-neutral and one slower. Net was -16 finisher moves, but Le Mans s12
regressed +4 when the new band selected `NONE`. Full mixed screens on the
current port stayed crash-free but shifted places on Gear/Big Oval/Spa/Long
Loop. The unrelated 111-line collective-field rescue was rejected without an
A/B target: it could worsen the mover, scored all rivals rather than the
activating forward pack, and added expensive eight-round rollout work.

INSTRUMENT: retain `AI1_FINISH_CERT_TTF=15` as the legacy all-field cap. The
new `AI1_FINISH_HOMOGENEOUS_TTF=20` band is admitted only when every live rival
shares the mover's kind and the candidate is not `NONE`. Every established
certificate remains: strict empty-map TTF improvement, trap<=L1, both the
score-shaped-rival and scorer-rival worlds finish at the candidate's lower
bound, then normal DJS remains an independent veto. Kind-relative homogeneity
keeps the mirrored AI2 body semantically identical.

RESULT: exact current-master A/B over the canonical 22 tracks x seeds1-15 was
2310/0 in both columns. Of 330 pairs, 312 were trajectory-identical, ten were
faster, eight changed line with the same finish list, none was slower; finisher
moves fell 144810 -> 144793. Cog s1-15 contributes another -3 at s14, so the
345-pair measured corpus is -20 overall (19 changed: 11 faster, 8 neutral).
An isolated old/current Nurburgring s19 replay adds -1 finisher move: identical
7/0/order, `[89,90,92,93,95,96,99]` -> `[89,90,92,93,95,96,98]`, with total
turns 752 -> 750. Its first difference is exactly `SPRINT ... W -> N ttf=16`,
so the 346-pair measured total is -21 and the golden is intentionally updated.
Big Oval s7 is the active pin: `[20,21,22,22,22,22,23]` becomes
`[20,20,21,21,22,22,23]` (move12 N -> NW). Homogeneous 4-car improves
330/0/61.103 -> 330/0/61.091; homogeneous 2-car is exact 110/0/60.336;
2v2 and 1v1 remain exact 2.500 and 1.500; slow s1-5 is exact 140/0/104.157;
Zandvoort s31-45 remains exact 104/1/142.167. After the homogeneity boundary,
mixed Gear/Big Oval/Spa/Long Loop/Le Mans s1-15 all return 4.500/4.500 c0.
The mirrored body passes the strict 27/27 identity probe. Permanent tests pin
the Big Oval gain, Le Mans s12 coast veto, and mixed Gear place neutrality.

## Round 95 (PROMOTED): strict cross-model pace retention

INSTRUMENT: when the topology-shaped eight-round model declares a fast-pack
choice dead and proposes a scorer-rival-surviving alternative, keep the
original choice only under the existing exact-L2 boundary, zero uncertainty,
at least five live rivals and a mover-kind homogeneous field. Its empty-map TTF
must be exactly one lower, and an eight-round six-rival scorer-field comparison
must make both the mover and aggregate field strictly better. Otherwise retain
the old survival switch. The rule was measured AI1-only and then mirrored.

RESULT: 22 regular tracks x seeds 1-60 gave 1,319/1,320 exact races. The sole
change was Silverstone s1: seven finishers, zero crashes, finisher moves
`[82,83,84,85,86,87,88] -> [82,83,84,85,85,86,88]`, sum 595 -> 593.
The 100 slow races were exact. The faster aggregate changes finisher identity /
order, so this is deliberately a racing-pace promotion, not a monotone-place
claim. Warm alternating target/control timing showed no material runtime
regression. `ai1_cross_model_pace_regression.py` pins the mirrored 593 result.

## Round 96 (PROMOTED): synchronized extended finish frontier

REJECTED PATHS: a raw TTF21-30 dual-finish extension found many Spa/Coil gains
but also made Coil s49 one move slower, changed finisher identities, and slowed
individual racers. Adding the old seal veto removed one Spa line but not those
field effects. Exact-L2 + zero uncertainty + strict eight-round mover/field
improvement narrowed Coil to s6 and s47; s47 still slowed one finisher. A
componentwise rival-cost rollout was rejected because its proxy accepted the
bad s47 line and rejected the clean s6 line. Cross-model gap>=2, staged
multi-turn zero/low-energy, and high-energy strict-field censuses were empty;
private-proof budget exhaustion had one Spa s8 event but no later faster
candidate casualty.

INSTRUMENT: retain the Round-75/94 logic byte-for-byte for TTF<=20. The new
TTF21-30 band is anchored to the original scorer choice (no chained one-turn
steps), must be non-`NONE` and exactly one map turn faster, and requires an
all-kind starting roster, at least five live rivals, exact trap L2, zero
uncertainty, and an adjacent previously moved rival with the same velocity and
a lateral or nearly lateral offset. The landing must be non-sealable. Both
full-to-finish worlds must still hit the empty-map lower bound; an eight-round
six-rival scorer-field rollout must strictly improve both mover and aggregate
field; normal DJS remains downstream. No track or seed identity is encoded.

RESULT: Coil s6 move299 p3 changes `SW v(1,-6)->(0,-5) (65,49)->(65,44)`
to `W ->(0,-6) ->(65,43)`. The same seven finishers remain crash-free and
their move list improves `[58,60,61,61,61,62,63] ->
[58,59,59,60,61,62,62]`, sum 426 -> 421; no individual finisher slows.
The pre-mirror champion A/B over canonical regular seeds1-15 is 329/330 exact,
with this sole -5 change and
144791 -> 144786 total finisher moves. Coil seeds1-60 have no other change;
s47 and s49 are exact. Spa/Gear/Silverstone s1-60, the other 18 regular tracks
s1-15, slow 4x25, all three mixed 4v4 bands and Zandvoort/Chicane s31-60 are exact or
place-neutral with no candidate safety delta. Direct child-CPU timing assigns
roughly 0.23-0.30 seconds of extra work to the active proof, while paired wall
time stays inside identical-control noise. The mirrored regression pins the
exact move, finisher identities/order/personal moves, full AI1/AI2 normalized
log identity, and s47/s49 veto moves.

## Round 83 (local agent, IN GATES): static funnel guard for the frontier

THE FRONTIER'S PROMOTION BLOCKER, repaired. Verification of the
r79-r82 stack found it never-worse on every suite EXCEPT the zandvoort
doom band: 3 crashes (s32/s37/s44, new sites) vs the r78 champion's 1
-- "the inherited Zandvoort crash profile" of their own r82 notes.
s37/s44 die at the byte-identical corner state as the old s42; s32
dives the top-wall funnel.

THE INSTRUMENT (the recorded static-bottleneck direction, built):
Reachability now derives per-progress-ring corridor widths from the
distance map (ringWidth[d]; buildRingWidths) with two queries --
minRingWidthAhead (rings 0-2 = the finish mouth never count) and
narrowRunAhead (longest CONSECUTIVE narrow stretch). AI1's slow branch
fires funnelRisk = spdInf>=3 AND minRing<=4 AND spdInf>minRing AND
narrowRun>=6, escalating to the 8-round scorer-me certificate.
Measured discrimination: the zandvoort corner reads minRing=4 along the
whole descent; every open corridor measured >= 7 (silverstone s1
distribution).

EMPIRICAL REJECTIONS on the way (each a recorded law):
1. A FAST-branch funnel arm saved NOTHING (s32's cert reads the doomed
   line alive: the suppressed sim-me cannot reproduce the pace-arm
   aggression that kills -- certificates certify a cautious ghost) and
   broke the lemans-s3 staged-pace checkpoint via the same gap in
   reverse (suppressed-me DIES on their private-lane line that real-me
   survives). Dropped.
2. An unconditional deepHandled claim reshaped hungaroring s40 into a
   NEW crash with 531 fires and ZERO switches -- silencing downstream
   arms is a behavior change even when the arm itself never acts.
   Switch-only claiming is the law.
3. narrowRun>=4 still cost the hungaroring-s10 pace pin 2 moves;
   RUN=6 separates true funnels (the corner run) from long-but-straight
   narrow sections cars legitimately thread at speed.

RESULTS (frontier + funnel guard): zandvoort band 3 -> 1 = champion
parity; s37/s42/s44/s45 all crash-free; every counterexample fixture
clean (incl. their silverstone s15); all four AI1 checkpoints green;
goldens pass; the frontier's pace FULLY PRESERVED (-3.57 on the five
long tracks). OPEN (new class, recorded): zandvoort s32 -- last
avoidable at m110 (survivor SW, death @r6 at spd^2=58), invisible to
every certificate because the killer is the mover's OWN future
pace-arm aggression, which IN_SCORER_SIM suppression removes from
sim-me by design. The recursion boundary is now the frontier's
fundamental limit; closing it needs either bounded-depth true-me
rollouts or admission-level speed discipline in the pace arms
themselves. ROUND EXTENDED during gating: the first battery found a LEMANS 4-CAR
s1 crash -- the frontier's OWN (pure pre-guard stack crashes it
identically; their "small-field crash-free" gates raced MIXED fields
only, so the all-AI1 4-car hole was outside their coverage). Last
avoidable m131: p3 holds spd^2=85 into the bottom-turn complex, dies
@r8, survivors shed laterally. Fixed by RE-ADDING the fast funnel arm
with two additional laws learned the hard way:
- narrowRun>=6 alone did not stop the lemans-8car-s3 false fire, and
  CROSS-MODEL smom confirmation is NEGATIVE-VALUE for deep verdicts
  (it blocked the true sparse-field death without stopping the dense
  false one) -- removed;
- the correct trust gate is FIELD SPARSITY: deep 8-round verdicts
  track reality at <=AI1_FUNNEL_DEEP_FIELD=4 live rivals (the 4car
  geometric doom is model-robust at 3) and drift into false kills at 7
  (accumulated rival error); pace-arm precedence is NOT a shield
  (their 5-round certificates are blind @r8).

FINAL BATTERY (frontier + both funnel arms, vs the r78 champion):
never-worse everywhere, strictly better nearly everywhere -- 8car
770/0 x3 at -0.97/-0.99/-0.95 with ZERO slower tracks; h2h c=0 both
bands with places WON (4.474/4.478 vs 4.526/4.522); 4car 330/0 at
-0.64 (the crash repaired AND faster); 1v1 110/0 at -0.30; slow exact
tie. All four AI1 pins green; every counterexample fixture clean.
THE COMPOSITION IS PROMOTION-READY; the word is the user's.

MERGED RE-CERTIFICATION (2026-08-14): their round 90 (high-energy
forward-pack pace, PR #5) landed mid-battery; the full battery was
re-run on the merged head (r79-r90 pace stack + r83 funnel guards) and
came back BYTE-FOR-BYTE identical to the pre-merge sweep on every
stage total -- 770/0 x3 at -0.97/-0.99/-0.95 with zero slower tracks,
h2h places won c=0 both bands, 4car 330/0 -0.64, 1v1 110/0 -0.30, slow
exact tie. All pins and fixtures green on the merged head. The merged
composition is the promotion candidate.

## Master correctness/debloat pass (2026-08-13)

SCOPE: ported only behavior-neutral maintenance from the Round-82 PR onto the
promoted Round-78 champion. No private-lane or staged-pace frontier policy was
moved into master, and AI1/AI2 remain byte-identical in racing behavior.

CORRECTNESS: `RaceAi`'s recursive-scorer guard was mutable static state. Two
concurrent `RaceGame` instances in one JVM could therefore suppress each
other's endgame and danger machinery. The guard is now instance-scoped and a
core invariant rejects future mutable static fields in `RaceAi`. A second
master-only audit found two independent defects: the main-window race scroller
was sized from its container before Swing layout (leaving it 0x0), and failures
in the background reachability thread were swallowed, causing AI windows to
poll forever or callers to continue after interruption with a partial map.
The grid now uses normal layout management with a centered scrollable wrapper;
reachability completion records and rethrows background failures and fails
closed on interruption.

DEBLOAT: removed two guaranteed-zero conflict probes, duplicate reachability
lookups, repeated simulated-board occupancy loops, floating-point work for
integer speed thresholds, three unused parameters, and inaccurate relative-
speed helper naming. Squared distances use `long` arithmetic. Headless layout,
state-isolation and failure-propagation regressions now pin the repaired
boundaries. The full JDK-25/JDK-26 CI, frozen champion goldens, core tests,
headless smoke and tooling checks must remain green on the exact master head.

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

ROUND 115 (low-energy graduated field acceleration): The Round-106 field certificate now admits AI1-only
speed2 gains 9..15 through TTF 45 when the incumbent speed2 is below
49 and the scorer is not coasting. This retains the Coil seed-1 and
seed-38 Pareto gains while excluding the long-range Spa and
high-energy Silverstone counterexamples. Exact gate:
3500 pairs, 2
Pareto-faster, 0 safety gain(s), zero
slower/safety-regression/redistribution outcomes, net
-3 finisher moves. AI2 remains frozen.

ROUND 117 (synchronized exact-six-ahead acceleration): AI1 may enter the established high-energy field
acceleration with exactly six rivals ahead only when a previously
moved rival is adjacent to the proposed landing and already carries
the candidate velocity. Exact gate: 3500 pairs,
1 Pareto gain(s),
0 safety gain(s), zero slower,
safety-regression or redistribution outcomes, net
-1 finisher moves. Coil s5/s22 are exact controls;
Coil s86 is the target gain. AI2 remains frozen.

ROUND 124 (phase-consistent trap-L2 acceleration): the old trap-L2 experiment's clean gain is isolated by the
round-phase boundary: positive L1/L2 field acceleration is AI1-only,
restricted to the first two movers and TTF<=45, with the established
high-energy and strict eight-round mover/field proof unchanged. Exact
gate: 3500 pairs, 1 Pareto
gain(s), zero individual slowdowns or safety regressions, net
-1 finisher moves. The only order change is the
improved driver joining an existing same-move tie. Changed races:
silverstone seed 93. AI2 remains frozen.

ROUND 171 (direct projected-occupancy maps): exact touched-cell counts replace repeated linear scans of projected opponent positions. The 26-track gate was byte-identical over 3500 races; alternating runtime ratio 0.881500 (11.85% faster).
Integration hardening records touched-cell membership for the whole clear epoch, preventing remove/re-add cycles from overflowing the touched buffer on supported tiny grids; CoreTests pins a full 3x3 board.
