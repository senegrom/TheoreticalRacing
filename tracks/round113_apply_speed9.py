#!/usr/bin/env python3
"""Lower only the strict field-acceleration speed-squared threshold 16 -> 9."""
from pathlib import Path
import re

path = Path('src/tr/logic/RaceAi.java')
source = path.read_text()
pattern = re.compile(
    r'^(\s*private final static int\s+AI1_FIELD_ACCEL_MIN_SPEED2_GAIN\s*=\s*)16(;.*)$',
    re.MULTILINE,
)
source, count = pattern.subn(r'\g<1>9\2', source, count=1)
assert count == 1, count
path.write_text(source)
print('materialized diagnostic speed-nine threshold')
