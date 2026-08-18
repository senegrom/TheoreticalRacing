#!/usr/bin/env python3
"""Materialize the original broad trap-L2 field-acceleration experiment."""
from pathlib import Path

path = Path("src/tr/logic/RaceAi.java")
source = path.read_text()
start = source.index("\tprivate Direction guardedFieldPaceOverride(")
end = source.index("\n\tprivate Direction privatePaceOverride(", start)
method = source[start:end]
old = (
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] != 0.0\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
)
new = (
    "\t\t\tif (d == chosen || d == Direction.NONE || turns == Integer.MAX_VALUE\n"
    "\t\t\t\t\t|| turns + 1 != chosenT || trapByDir[d.ordinal()] > AI1_TRAP_L2\n"
    "\t\t\t\t\t|| uncByDir[d.ordinal()] != 0.0)\n"
)
assert method.count(old) == 1, method.count(old)
method = method.replace(old, new, 1)
source = source[:start] + method + source[end:]
assert source.count("trapByDir[d.ordinal()] > AI1_TRAP_L2") == 1
path.write_text(source)
print("materialized broad trap-L2 field acceleration diagnostic")
