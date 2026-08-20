#!/usr/bin/env python3
"""Run the Round 162 materializer with a structure-based grow-method splice.

The original experiment matched the PointContainmentCache grow method by its
entire text. That became brittle once adjacent cache work changed formatting.
This wrapper preserves the candidate exactly, but locates the unique method
inside PointContainmentCache by class and class-tail anchors.
"""
from pathlib import Path

original = Path(__file__).with_name("round162_apply.py")
script = original.read_text()
start = script.index('old_grow = """')
end_marker = "source = source.replace(old_grow, new_grow, 1)\n"
end = script.index(end_marker, start) + len(end_marker)
replacement = '''point_class_start = source.index("\\tstatic final class PointContainmentCache {")
grow_start = source.index("\\t\\tprivate void grow() {", point_class_start)
grow_end = source.index("\\n\\t}\\n\\n\\tprivate static long pointHash", grow_start)
new_grow = """\\t\\tprivate boolean grow() {
\\t\\t\\tif (xKeys.length >= maxCapacity)
\\t\\t\\t\\treturn false;
\\t\\t\\tfinal long[] oldX = xKeys;
\\t\\t\\tfinal long[] oldY = yKeys;
\\t\\t\\tfinal byte[] oldStates = states;
\\t\\t\\tallocate(xKeys.length << 1);
\\t\\t\\tsize = 0;
\\t\\t\\tfor (int i = 0; i < oldStates.length; i++) {
\\t\\t\\t\\tif (oldStates[i] == 0)
\\t\\t\\t\\t\\tcontinue;
\\t\\t\\t\\tint slot = (int) pointHash(oldX[i], oldY[i]) & mask;
\\t\\t\\t\\twhile (states[slot] != 0)
\\t\\t\\t\\t\\tslot = slot + 1 & mask;
\\t\\t\\t\\txKeys[slot] = oldX[i];
\\t\\t\\t\\tyKeys[slot] = oldY[i];
\\t\\t\\t\\tstates[slot] = oldStates[i];
\\t\\t\\t\\tsize++;
\\t\\t\\t}
\\t\\t\\treturn true;
\\t\\t}"""
source = source[:grow_start] + new_grow + source[grow_end:]
'''
script = script[:start] + replacement + script[end:]
script = script.replace(
    'assert source.count("pointContainmentCacheShared") == 3',
    'assert source.count("pointContainmentCacheShared") == 4',
)
namespace = {"__name__": "__main__", "__file__": str(original)}
exec(compile(script, str(original), "exec"), namespace)
