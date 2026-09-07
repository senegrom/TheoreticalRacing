"""Browser host scheduling only: distance maps join the existing preparation job.

Geometry/start-zone setup and the independent exact-potential launch stay on
the command path. All map algorithms are unchanged; only the distance BFS joins
the reachability worker, so exact-potential preparation can overlap the whole
map job in browsers too. The inverse is checked so source drift cannot silently
broaden this adapter.
"""
RULES = {
    'RaceGame.java': (
        '\t\treach.computeDistMap();\n\t\tstartOptimalPotentialCompute();\n\t\treach.startReachabilityCompute();',
        '\t\tstartOptimalPotentialCompute();\n\t\treach.startReachabilityCompute();'),
    'Reachability.java': (
        '\t\tfinal Thread t = new Thread(() -> {\n\t\t\ttry {',
        '\t\tfinal Thread t = new Thread(() -> {\n\t\t\ttry {\n\t\t\t\tcomputeDistMap();'),
}



def adapt(name: str, source: str, *, reverse: bool = False) -> str:
    if name not in RULES:
        return source
    old, new = RULES[name]
    if reverse:
        old, new = new, old
    if source.count(old) != 1:
        raise RuntimeError(f'Startup scheduling drift in {name}: expected one {old!r}')
    return source.replace(old, new)
