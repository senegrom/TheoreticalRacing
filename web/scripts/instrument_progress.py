"""Insert output-only telemetry into the browser copy, never the source engine.

Erasing the tagged added lines must recover the byte-identical original text.
No expression, branch, loop bound, order, return or AI search is replaced.
"""
TAG = ' // browser-progress'


def instrument(source: str) -> str:
    result = source

    def after(anchor, statement, count=1, *, expression=False):
        nonlocal result
        actual = result.count(anchor)
        if actual != count:
            raise RuntimeError(f'Progress hook drift: {anchor!r}: expected {count}, found {actual}')
        indent = anchor.splitlines()[-1].split(anchor.splitlines()[-1].lstrip())[0]
        code = statement if expression else 'tr.browser.Progress.' + statement
        result = result.replace(anchor, anchor + '\n' + indent + '\t' + code + TAG)

    for anchor, label, stage in [
        ('\tvoid computeDistMap() {', 'Mapping track distances', 2),
        ('\tboolean tryLoadReachabilityCache() {', 'Checking saved track maps', 3),
        ('\tvoid computeReachability() {', 'Scanning finish approaches', 4),
        ('\tshort[] buildLegalAliveMask(final int total) {', 'Checking safe continuations', 5),
        ('\tvoid sweepRoomy(final short[] legalAlive, final BitSet req, final BitSet out) {', 'Building manoeuvring maps', 5),
        ('\tbyte[] initMinShed(final int total) {', 'Preparing braking maps', 5),
        ('\tbyte[] relaxMinShed(final byte[] in, final short[] legalAlive, final BitSet roomyReq) {', 'Computing braking maps', 5),
        ('\tbyte[] sweepCertSq(final short[] legalAlive, final byte[] shed) {', 'Certifying speed maps', 5),
        ('\tprivate void saveDerived() {', 'Saving computed maps', 5),
        ('\tvoid computeGateMaps(final java.awt.geom.Line2D[] gates) {', 'Resolving lap checkpoints', 6),
    ]:
        after(anchor, f'begin("{label}", {stage});')
    after('\tprivate boolean tryLoadDerived() {', 'begin("Loading saved driving maps", 5);')
    after('\t\taliveStates = alive;', 'reused();')
    after('\t\tcertSq = (byte[]) m[10];', 'reused();')
    after('\t\t\t\tgame.clearPointContainmentCacheForCurrentThread();',
          'if (reachabilityFailure == null) tr.browser.Progress.complete();', expression=True)
    # Distinct signatures for each real checkpoint pass, including convergence.
    after('\tprivate int[] computeGateMap(final int gate, final java.awt.geom.Line2D line,\n\t\t\tfinal int[] nextMap) {', 'begin(gate == 0 ? "Lap route to finish" : "Lap route to checkpoint " + gate);')
    after('\t\t\tfinal BitSet nextRobust, final int[] scratch, final byte[] arrivals) {',
          'begin(gate == 0 ? "Lap safety at finish" : "Lap safety at checkpoint " + gate, 7);')
    after('\t\tfor (int x = 0; x < aliveW; x++) {', 'scan(x, aliveW);', 3)
    after('\t\tfor (int idx = aliveStates.nextSetBit(0); idx >= 0; idx = aliveStates.nextSetBit(idx + 1)) {',
          'scan(idx, turnsArr.length);', 5)
    # Unknown-length BFS: show explored states and an indeterminate bar.
    anchor = '\t\twhile (!queue.isEmpty()) {'
    if result.count(anchor) != 4:
        raise RuntimeError('Progress hook drift: BFS count changed')
    result = result.replace(anchor, '\t\ttr.browser.Progress.searching();' + TAG + '\n\t\tint browserProgressCount = 0;' + TAG + '\n' + anchor)
    after(anchor, 'explored(browserProgressCount);', 4)
    result = result.replace('tr.browser.Progress.explored(browserProgressCount);' + TAG,
                            'if ((++browserProgressCount & 2047) == 0) tr.browser.Progress.explored(browserProgressCount);' + TAG)
    result = result.replace('tr.browser.Progress.scan(idx, turnsArr.length);' + TAG,
                            'if ((idx & 1023) == 0) tr.browser.Progress.scan(idx, turnsArr.length);' + TAG)
    if strip(result) != source:
        raise RuntimeError('Progress instrumentation changed engine code')
    return result


def strip(source: str) -> str:
    return ''.join(line for line in source.splitlines(keepends=True) if not line.rstrip('\n').endswith(TAG))


def instrument_game(source: str) -> str:
    result = source
    for anchor, statement in [
        ('\tprivate void buildTrackGeometry() {', 'geometry();'),
        ('\t\tcomputeLapGates();', 'plan(lapGates != null, needsInformedStartMaps());'),
    ]:
        if result.count(anchor) != 1:
            raise RuntimeError(f'Geometry progress hook drift: {anchor!r}')
        result = result.replace(anchor, anchor + '\n\t\ttr.browser.Progress.' + statement + TAG)
    if strip(result) != source:
        raise RuntimeError('Geometry progress instrumentation changed engine code')
    return result


def instrument_optimal(source: str) -> str:
    """Output-only counters for the previously invisible full-race potential."""
    result = source
    hooks = [
        ('\t\tfinal Line2D sf = game.lapGates[0];',
         '\t\ttr.browser.Progress.begin("Exact full-race map — scanning finish approaches", 9);'),
        ('\t\tfor (int read = 0; read < frontier.size; read++) {',
         '\t\t\tif ((read & 2047) == 0) tr.browser.Progress.explored(read);'),
    ]
    for anchor, code in hooks:
        if result.count(anchor) != 1:
            raise RuntimeError(f'Optimal-map progress hook drift: {anchor!r}')
        result = result.replace(anchor, anchor + '\n' + code + TAG)
    if strip(result) != source:
        raise RuntimeError('Optimal-map instrumentation changed engine code')
    return result


def instrument_placement(source: str) -> str:
    """The shared candidate scan is the last finite preparation stage."""
    result = source
    hooks = [
        ('    static Analysis prepare(final RaceGame game) {',
         '        tr.browser.Progress.alternatives();'),
        ('        for (int x = xMin; x <= xMax; x++) {',
         '            tr.browser.Progress.scan(x - xMin, xMax - xMin + 1);'),
    ]
    for anchor, code in hooks:
        if result.count(anchor) != 1:
            raise RuntimeError(f'Starting-alternatives progress hook drift: {anchor!r}')
        result = result.replace(anchor, anchor + '\n' + code + TAG)
    if strip(result) != source:
        raise RuntimeError('Starting-alternatives instrumentation changed engine code')
    return result
