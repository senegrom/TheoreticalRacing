#!/usr/bin/env python3
"""Run Round 164 with separate soft/counting signature anchors."""
from pathlib import Path

original = Path(__file__).with_name("round164_apply.py")
script = original.read_text()
old = '''old_sig = "final int[][] occupancy2, final int myDist)"
new_sig = "final byte[] aheadOccupancy)"
assert source.count(old_sig) == 2, source.count(old_sig)
source = source.replace(old_sig, new_sig)
'''
new = '''old_soft_sig = "final int[][] occupancy, final int[][] occupancy2,\\n\\t\\t\\tfinal int myDist)"
new_soft_sig = "final int[][] occupancy, final byte[] aheadOccupancy)"
assert source.count(old_soft_sig) == 1, source.count(old_soft_sig)
source = source.replace(old_soft_sig, new_soft_sig, 1)

old_counted_sig = "final int[][] occupancy,\\n\\t\\t\\tfinal int[][] occupancy2, final int myDist)"
new_counted_sig = "final int[][] occupancy,\\n\\t\\t\\tfinal byte[] aheadOccupancy)"
assert source.count(old_counted_sig) == 1, source.count(old_counted_sig)
source = source.replace(old_counted_sig, new_counted_sig, 1)
'''
assert script.count(old) == 1, script.count(old)
script = script.replace(old, new, 1)
namespace = {"__name__": "__main__", "__file__": str(original)}
exec(compile(script, str(original), "exec"), namespace)
