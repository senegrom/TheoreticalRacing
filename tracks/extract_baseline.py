"""Retired: printed benchmark summaries cannot establish a baseline's provenance.

The old command accepted BENCH_LOG OUT_JSON [COLUMN]. It is retained only to
explain the migration and exits nonzero without creating or overwriting files.
Create a validated baseline directly with BENCH_BASELINE and bench_ai.py.
"""
import argparse
import sys


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('legacy_arguments', nargs='*', metavar='LEGACY_ARGUMENT')
    parser.parse_args(argv)
    print(
        'extract_baseline: text-to-cache export is retired. Printed rows do not '
        'contain the exact seeds, properties, tracks, runtime or champion identity. '
        'No output was written. Create a fresh validated cache by running '
        'bench_ai.py with BENCH_BASELINE=/path/to/new-cache.json; set '
        'BENCH_CHAMPION_JAR=/path/to/frozen.jar to preserve a separate champion. '
        'Supply the original track list and --seeds/--seed-start explicitly.',
        file=sys.stderr,
    )
    return 2


if __name__ == '__main__':
    raise SystemExit(main())
