# Performance and memory invariants

The optimizations in this document are intended to be decision-invisible: they
remove repeated work and bound retained/search memory without shortening an AI
search, changing a score, or changing referee rules.

## Checkpoint map construction

Lap/checkpoint seed discovery evaluates each resulting movement segment once,
then distributes the seed to all predecessor velocities that can produce that
segment. The previous nested predecessor-velocity/acceleration loops re-ran the
same geometry and landing tests up to nine times.

A completed lap-map product (gate distances, robust sets, coherent alive set and
all derived driving certificates) is memoized as one immutable bundle. Reuse is
all-or-nothing; restoring only the finish map without its coherent lap products
is forbidden. The in-process memo is byte bounded and LRU-evicted.

`-Dtr.reachMemoBytes=N` can reduce the reach/lap memo allowance for diagnostics.
Zero disables retention. The normal limit is adaptive to the JVM maximum heap
and capped at 384 MiB.

## Exact full-race potential

The exact reverse BFS now uses a circular FIFO. Processed states no longer stay
in a grow-only array until the search ends. FIFO order is unchanged.

The historical 1.5-GiB retained-distance eligibility is preserved. Construction
also gets a separate bounded FIFO allowance, while a deterministic reserve based
on the configured maximum heap protects the rest of the game. GC timing is never
used to decide whether an exact map exists, because that would change AI choices
between identical races. If the total cannot fit under that deterministic limit,
the existing over-budget behavior applies instead of risking the whole JVM.

`-Dtr.optimalBuildBytes=N` overrides the build budget for diagnostics.
`-Dtr.optimalMemoBytes=N` controls the byte-bounded LRU memo of completed exact
potentials; zero disables retention.

## Parallel exact/start preparation

When informed starts need the exact full-race potential, that potential is now
launched independently of reachability after the immutable track geometry is
frozen. The browser startup adapter keeps the same overlap while moving only the
distance BFS into the reachability worker. A conservative max-heap estimate
allows concurrency only when the exact distance map, bounded FIFO, reach/lap
products and a fixed reserve fit together. The decision never depends on current
heap occupancy or GC timing, so identical races cannot change policy because of
thread scheduling or collection timing. If the estimate is too large, the old
sequential preparation path is retained.

On local JDK 21 cold-cache Circle runs with eight AI1 cars, three laps and
informed starts, three paired runs averaged 3.88 s before and 3.12 s after
parallel preparation (about 20% lower elapsed time), with byte-identical race
logs. Lobe2 was effectively neutral in a small two-run sample because the two
heavy jobs contend for the same cores/cache there; the gate is therefore a
correctness/memory gate rather than a claim that every track will speed up.

## Finish-edge memoization

Integer race moves cache the pure forward finish-line intersection verdict by
the existing dense edge index. The finish table is a separate lazily allocated
two-bit array, so the hot legality table remains at two bits per edge and keeps
its previous cache footprint. Concurrent stale writes have the same benign
semantics as legality caching: they may erase a cached verdict and cause
recomputation, but cannot manufacture a different result. Non-lattice double
geometry callers retain the uncached predicate.

A 20-seed Hairpin AI1 batch on local JDK 21 retained byte-identical logs and
changed elapsed time from 9.01 s to 8.94 s in that run. This is deliberately a
small optimization; its main value is removing repeated Line2D intersection
work inside deeper AI rollouts.

## Browser snapshots

The first engine state and explicit resynchronizations are full snapshots.
Subsequent action replies carry a revisioned delta:

* geometry is sent only when its revision changes;
* unchanged players are omitted;
* history normally appends only new points;
* Undo or any non-prefix history change sends a replacement history;
* a base-revision mismatch fails closed so the caller can request a full state.

`Engine` reconstructs a complete immutable state for the existing UI, so this is
only a Java-to-JavaScript transport optimization. It does not move game logic
into JavaScript.

## Bounded measurements

On a warmed JDK 25 run with two eight-car, three-lap seeds and a 2 GiB heap,
the combined checkpoint deduplication plus complete-lap reuse reduced elapsed
runtime from 11.44 s to 3.99 s on Circle and from 14.80 s to 10.31 s on Lobe2.
The complete logs were byte-identical in all four paired races. These are local
native measurements, not mobile-browser timing claims.

For a 978-move three-lap Circle browser-adapter race, serialized action replies
fell from 11,639,574 bytes to 464,089 bytes (96.0% less), while the Java game log
remained byte-identical. This measures transport payload, not wall-clock speed.

The earlier queue profile on the same Circle geometry processed about 3.53M
states while only about 40k were pending at once, motivating the bounded FIFO.

Performance changes must continue to pass the map-hash/race-log equivalence
checks, core solver tests, golden/champion regressions and browser parity gates.
