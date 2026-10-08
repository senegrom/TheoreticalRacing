#!/usr/bin/env python3
"""Combined traffic/adaptive controls and strict full-suffix corpus replay.

This exercises the same control matrix as racecraft_next_cli, but includes all
six traffic opportunity flags. It is functional evidence, not a fleet screen.
Caller-owned profiles and tracks are never modified.
"""
from __future__ import annotations

import racecraft_next_cli as base
import racecraft_traffic_cli as traffic


def main() -> None:
    original = base.FLAGS
    base.FLAGS = ','.join(dict.fromkeys(original.split(',') + traffic.FLAGS.split(',')))
    try:
        base.main()
    finally:
        base.FLAGS = original


if __name__ == '__main__':
    main()
