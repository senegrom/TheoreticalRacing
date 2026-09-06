"""Insert output-only telemetry into the browser copy, never the source engine.

Erasing the tagged added lines must recover the byte-identical original text.
No expression, branch, loop bound, order, return or AI search is replaced.
"""
TAG = ' // browser-progress'


def instrument(source: str) -> str:
    result = source

    def after(anchor, statement, count=1):
        nonlocal result
        actual = result.count(anchor)
        if actual != count:
            raise RuntimeError(f'Progress hook drift: {anchor!r}: expected {count}, found {actual}')
        indent = anchor.splitlines()[-1].split(anchor.splitlines()[-1].lstrip())[0]
        result = result.replace(anchor, anchor + '\n' + indent + '\ttr.browser.Progress.' + statement + TAG)

    for anchor, label in [
        ('\tvoid computeDistMap() {', 'Mapping track distances'),
        ('\tboolean tryLoadReachabilityCache() {', 'Checking saved track maps'),
        ('\tvoid computeReachability() {', 'Scanning finish approaches'),
        ('\tshort[] buildLegalAliveMask(final int total) {', 'Checking safe continuations'),
        ('\tvoid sweepRoomy(final short[] legalAlive, final BitSet req, final BitSet out) {', 'Building manoeuvring maps'),
        ('\tbyte[] initMinShed(final int total) {', 'Preparing braking maps'),
        ('\tbyte[] relaxMinShed(final byte[] in, final short[] legalAlive, final BitSet roomyReq) {', 'Computing braking maps'),
        ('\tbyte[] sweepCertSq(final short[] legalAlive, final byte[] shed) {', 'Certifying speed maps'),
        ('\tprivate void saveDerived() {', 'Saving computed maps'),
        ('\tvoid computeGateMaps(final java.awt.geom.Line2D[] gates) {', 'Resolving lap checkpoints'),
    ]:
        after(anchor, f'begin("{label}");')
    # Distinct signatures for each real checkpoint pass, including convergence.
    after('\tprivate int[] computeGateMap(final int gate, final java.awt.geom.Line2D line,\n\t\t\tfinal int[] nextMap) {', 'begin("Checkpoint " + gate);')
    after('\t\t\tfinal BitSet nextRobust, final int[] scratch, final byte[] arrivals) {',
          'begin("Checkpoint safety " + gate);')
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
