"""Browser host scheduling only: distance maps join the existing preparation job.

Geometry/start-zone setup stays on the command path. All map algorithms and
order are unchanged; only the command thread no longer waits for distance BFS.
The inverse is checked so source drift cannot silently broaden this adapter.
"""
RULES = {
    'RaceGame.java': (
        '\t\treach.computeDistMap();\n\t\treach.startReachabilityCompute();',
        '\t\treach.startReachabilityCompute();'),
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
