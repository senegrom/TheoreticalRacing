#!/usr/bin/env python3
"""Independent arm and zero-budget controls; no place-performance conclusions."""
from __future__ import annotations
import argparse
import json
from pathlib import Path
import re
import tempfile
from racecraft_next_cli import ROOT, race

ARMS = ('adaptive-escape', 'opening,followup', 'recovery', 'tactical-extension')


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--out', type=Path)
    args = parser.parse_args()
    jar = (ROOT / 'theoreticRacing.jar').resolve()
    if not jar.is_file(): raise SystemExit('build the branch JAR first')
    temporary = None
    if args.out:
        output = args.out.resolve(); output.mkdir(parents=True, exist_ok=False)
    else:
        temporary = tempfile.TemporaryDirectory(prefix='adaptive-arms-'); output = Path(temporary.name)
    records = []
    try:
        for index, (track, players, mode) in enumerate((('hairpin', 2, 'legacy'), ('circle', 4, 'informed'))):
            slots = ','.join(str(i) for i in range(1, players + 1))
            baseline = race(output, f'{index}-base', jar, track, players, mode, 3, {})
            for arm_index, flag in enumerate(ARMS):
                prefix = f'{index}-{arm_index}'
                settings = dict(candidateSlots=slots, racecraftNext=flag)
                plain = race(output, prefix + '-plain', jar, track, players, mode, 3, settings)
                audited = race(output, prefix + '-audit', jar, track, players, mode, 3,
                               dict(settings, racecraftCapture='true', racecraftCaptureLimit='10000'))
                if plain != audited: raise AssertionError(f'{track}/{flag}: audit changed the policy')
                text = (output / (prefix + '-audit.process')).read_text(encoding='utf-8')
                record = dict(track=track, arm=flag, changedFromControl=plain != baseline,
                              pendingPlanCaptures=text.count('RACECRAFT_STATE rc4,'),
                              inheritedAdmissions=text.count('inherited=true'),
                              recoveryExpansions=text.count('recovery=true'),
                              tacticalExtensions=len(re.findall(r'extension=[12](?: |$)', text)),
                              auditIdentity=True)
                records.append(record)
                print(json.dumps(record, sort_keys=True), flush=True)
            zeros = dict(candidateSlots=slots, racecraftNext=','.join(ARMS), racecraftOpeningTrials='0',
                         racecraftAdaptiveNodes='0', racecraftRecoveryTrials='0', racecraftTacticalExtraRounds='0')
            if race(output, f'{index}-zero-budgets', jar, track, players, mode, 3, zeros) != baseline:
                raise AssertionError(f'{track}: zero-budget controls changed the race')
        (output / 'validation.json').write_text(json.dumps(dict(races=20, records=records,
                functionalOnly=True, performanceScreen=False, promoted=False), indent=2) + '\n', encoding='utf-8')
        print('Adaptive arm controls: 20 complete races; independent audit identity and combined zero-budget identity OK', flush=True)
    finally:
        if temporary is not None: temporary.cleanup()


if __name__ == '__main__':
    main()
