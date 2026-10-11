# Creative racecraft experiments

Branch: `work/racecraft-strategies-20261008`.
Champion base: `807d3d24b1d60d004e36c2410c5ef4725bf553e3`.
Earlier strategy implementation: `e137925a94388337dcbfef128ad36f7e18fa17f8`.
Initial Java implementation: `fd190714d4e606602fa7eaab4592445f631bac09`.

These are independent research arms, not promoted policy. No fleet-performance
improvement is claimed. The existing champion, computed-start rule, twenty-cell
solo boundary, maps, tracks and user.properties remain unchanged.

## Configuration

Create a private properties file; do not edit user.properties:

```properties
candidateSlots=1,3,5,7
racecraftNext=pace-feints,ambush,traffic-judo,selfish-search,two-judge
racecraftCreativeNodes=2048
racecraftCreativeTrials=6
racecraftSelfishPlies=6
```

All five driving flags are off by default. A positive creative node and trial
budget and explicit candidate slots are required. Zero of either disables all
five. The earlier strategy node budget remains independent. The sixth idea,
tactics breeding, is an offline tool rather than an additional driving flag.

The shared generation budget is split across enabled generators. Full-policy
queries have a separate small call bound: traffic judo probes at most three
alternative next-rival responses plus its reference; checking performs two fresh
rollouts with at most two full-first-policy queries per rollout. These policy
queries still run the existing bounded champion algorithms. The creative node
budget is not a wall-clock or total instruction cap.

The ordinary discovery/checking horizon is twelve own moves, including the final
rival-response cycle. All generated multi-action prefixes contain at most four
accelerations. An accepted suffix uses existing exact-state, commit-only policy
memory; Undo restores it, and repeated hints neither consume nor install it.
Downstream champion pace overrides and guards keep their authority. If they
replace the planned first action, that pending suffix is invalidated.

## 1. Endpoint-preserving feints

CreativePaths adds the four-step acceleration pulse `[+1,-1,-1,+1]` on each axis
or diagonal to a nominal four-action continuation. The pulse sums to zero both
in velocity and in time-weighted displacement. Every resulting acceleration
must remain in the nine-action domain, every geometric transition must be legal,
and the full endpoint must equal the original: position, velocity, lap, gate,
grid departure and elapsed own moves. Terminal prefixes are not relabelled as
nonterminal feints.

These are equal-endpoint SOLO proposals, not assurances that reacting traffic
will allow the route. All nominated paths receive reactive evaluation.

## 2. Target-first ambushes

AmbushPlans expands the next live rival's minimum-time mapped route graph for up
to three own moves. Only a complete layer can establish that all mapped fastest
continuations share a landing cell. Partial layers and map/physical-grid
mismatches cannot manufacture mandatory cells; a possible finish is never
regarded as blockable ordinary occupancy.

A bounded inverse-kinematic search then attempts to reach that cell on the
matching response cycle. It enumerates reachable endpoint velocities and uses
`x_previous = x - v`, `v_previous = v - acceleration`. Every completed inverse
route is replayed forward through geometry/progress rules and must preserve own
solo pace. At most two routes are offered.

A compulsory cell in this mapped graph is not a proof about all physically
possible human responses, nor a guarantee of a better race place. Reactive
forecasting remains responsible for acceptance.

## 3. Poisoned gaps and traffic judo

TrafficJudo tests pace-neutral alternative first actions against the next rival's
actual bounded full-policy response on the changed board. A mere different
forecast is insufficient to label the tactic: the move must unlock a previously
illegal rival reply or cause the same next third car's cheapest continuation to
become worse. The latter comparison follows real cyclic move order.

No opponent delay or crash earns a score bonus. These effects nominate actions;
only the deciding car's place and own time determine which result is preferred.
No car is commanded to cooperate or replay an action from a different board.

## 4. Self-interested terminal search

SelfishSearch uses a bounded max-n tree with exactly three live AI cars, initially
only when the deciding car's mapped finish distance is at most ten. Each actor
chooses its own absolute place first and its own time second. Ties retain fixed
action order and never use the focal car's preference as a hidden tie breaker.
An unresolved child invalidates that subgame; it is not called irrational or
dominated. Previous classifications and progress-based timeout ordering remain
in the state.

The search is a model of incentives, not a universal certificate or a claim that
the production AI behaves optimally. Its candidate enters the ordinary reactive
comparison. It cannot delete any physical response from the existing safety
proofs. Completed root results do not establish that unexplored roots are worse.

## 5. Separate discovery and acceptance

With two-judge, cheap scorer rollouts select one challenger. The challenger and
the incumbent are then freshly evaluated with the SAME stronger model, fixed
rival target and horizon. That model upgrades the next live rival's first action
and the mover's first unforced future action to their full top-level policy;
all calls beneath them are suppressed, and creative experiments cannot recurse.
It is a bounded checker inspired by the successful first-response experiments,
not a claim to reproduce round 303's precise most-interacting-rival selector.

Both results must be known and the challenger must strictly improve own place,
or equal place with fewer own moves. A rejection does not cause another proposal
to be tried against the checking model. Old chooser and pace decisions outside
this experiment are not placed under a new global veto. When two-judge is enabled
alone, the existing manoeuvre generator supplies proposals instead of silently
enabling all four new generators.

## 6. Offline tactics breeder

Build the JAR, capture a complete race using a private profile, then run:

```sh
python3 tools/racecraft_corpus.py capture \
  --jar theoreticRacing.jar --props /path/to/research.properties \
  --track hairpin --seed 3 --limit 20 --every 7 \
  --out /new/path/capture --heap=-Xmx8g

python3 tools/racecraft_breeder.py \
  --capture /new/path/capture --out /new/path/breeding \
  --cases 1 --offset 1 --trials 32 --depth 4 --seed 1
```

The breeder binds the executable, Java runtime, profile, track, map preparation,
original log and complete decision snapshot. Its empty-prefix control must match
the original race's entire remaining trace and classification. Every trial uses
the `breed1` query to apply up to four actual own accelerations while rivals make
fresh production decisions. The query returns full traces and the exact board
and legal actions at the prefix endpoint. Python verifies request identity,
classification/transition structure, forced actions and endpoint continuity;
geometric legality is supplied by the pinned Java referee.

Pulse and ambush families seed the search. Further prefixes are grown only from
legal actions at actually reached endpoints, alternating seeded depth-biased and
broad exploration. A diversity archive retains strictly improving completed
tails by live-field size, gate, speed band, move-order position, prefix length,
steering direction and changed rival responses. It is a bounded discovery
archive, not an exhaustive solver or a trained general policy.

All requests and responses are retained. Positive cells carry the root snapshot,
control reference and full legal prefix, so their ancestry is reproducible.
Invalid or incomplete tails are excluded from positive labels. RUN_COMPLETE
means the bounded discovery run finished, not that all attempted tails completed
or that any performance claim cleared. Nothing is automatically installed,
trained, merged or promoted. No coordinate mutation, frozen-opponent replay,
track-name action lookup, fleet-track rewrite or hidden background job is used.

## Validation and promotion

CreativeRacecraftTests contains arithmetic and physical pulse witnesses,
complete-layer/incomplete-layer ambush tests, inverse-route witnesses, released
gaps, selfish terminal preferences, matched checking-model tests, model-call
bounds, query restoration and full-policy breeder parity. Python protocol tests
reject mismatched requests, invented prefix endpoints, invalid continuations and
truncated labels. racecraft_creative_cli.py runs independent/combined driving
arms, disabled and audit-identity controls, full counterfactual tails and two
small breeder exercises.

See validation.json and the linked CI run for what has actually completed.
Correctness witnesses do not demonstrate a fleet gain. Before any promotion,
measure independent arms and then combinations in mirrored candidate/champion
fields, random/computed/scattered starts, held-out seeds and the lone-entrant
comparison. Report own finishing place first, own time second, and compute cost;
field crash counts and opponents' delays are descriptive, not vetoes.
