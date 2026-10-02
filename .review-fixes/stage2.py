from pathlib import Path
p=Path('tools/racecraft_corpus.py'); s=p.read_text()
if 'import racecraft_validation as validation' not in s:
    s=s.replace("ROOT = Path(__file__).resolve().parents[1]", "ROOT = Path(__file__).resolve().parents[1]\nsys.path.insert(0, str(Path(__file__).resolve().parent))\nimport racecraft_validation as validation")
    s=s.replace('if len(fields) != 6 or fields[1] not in DIRECTIONS:', 'if len(fields) != 7 or fields[1] not in DIRECTIONS:')
    s=s.replace("shortlist=fields[5].split(',') if fields[5] else [], turn=int(h[1])))", "shortlist=fields[5].split(',') if fields[5] else [], turn=int(h[1]),\n                         legalActions=validation.action_list(fields[6].split(',') if fields[6] else [])))")
    a=s.index('def analyze('); b=s.index('\ndef java_runtime(',a)
    s=s[:a]+'''def analyze(case: dict, answer: dict, *, max_moves: int, original_race: str, roster: dict) -> dict:
    base, complete = validation.validate_response(case, answer, max_moves)
    if base['complete']:
        validation.validate_control(case, base, original_race, roster)
    summary = dict(id=case['id'], actual=case['actual'],
                   influence=influence_diagnostic(case['snapshot']))
    if not complete:
        return dict(summary, labelled=False, excluded='incomplete-counterfactuals',
                    incomplete=[t['action'] for t in answer['trials'] if not t['complete']])
    best = base
    for trial in answer['trials']:
        if (trial['place'], trial['ownMoves']) < (best['place'], best['ownMoves']): best = trial
    if best is base: reason = 'no-observed-regret'
    elif not base['legal']: reason = 'selected-illegal-action'
    elif not case.get('shortlist'): reason = 'pre-chooser-or-unobserved'
    elif best['action'] not in case['shortlist']: reason = 'shortlist-exclusion'
    elif best['action'] == case.get('chooser') and case['actual'] != case.get('chooser'):
        reason = 'downstream-replacement'
    else: reason = 'forecast-horizon-or-ranking'
    return dict(summary, labelled=True, best=best['action'], placeGain=base['place']-best['place'],
                ownMoveGain=base['ownMoves']-best['ownMoves'], baselinePlace=base['place'],
                bestPlace=best['place'], diagnosis=reason)


def tooling_identity() -> dict:
    paths = ('tools/racecraft_corpus.py', 'tools/racecraft_validation.py',
             'tracks/benchmark_io.py', 'tracks/forensics_common.py')
    return {path: digest(ROOT / path) for path in paths}

'''+s[b:]
    s=s.replace('manifest = dict(schema=1, jar=str(jar)', 'manifest = dict(schema=2, jar=str(jar)')
    s=s.replace('toolSha256=digest(Path(__file__)), cases=', 'tooling=tooling_identity(), cases=')
    s=s.replace('    _, update_properties, potential_status = helpers()', '    configured_players, update_properties, potential_status = helpers()')
    s=s.replace("    java, version = java_runtime(args.java, manifest['heap'])", "    if manifest.get('schema') != 2: raise ValueError('old corpus manifest: capture again with cf4')\n    java, version = java_runtime(args.java, manifest['heap'])")
    s=s.replace("or digest(Path(__file__)) != manifest['toolSha256']", "or tooling_identity() != manifest['tooling']")
    s=s.replace('    summaries = []', "    summaries = []\n    original_race = (directory / 'race.log').read_text(encoding='utf-8')\n    roster = configured_players(source)")
    s=s.replace('f"cf3,{args.max_moves},{case[\'actual\']}|{case[\'snapshot\']}\\n"', "validation.query(case, args.max_moves) + '\\n'")
    s=s.replace('summary = analyze(case, response)', 'summary = analyze(case, response, max_moves=args.max_moves, original_race=original_race, roster=roster)')
    p.write_text(s)
# The retained branch CI now compares against the actually integrated master, not September 28.
p=Path('.github/workflows/racecraft-next.yml'); s=p.read_text()
s=s.replace('955001104bbe315cf9b82a1cd2dfb447beddd211','b54e9bb05f91c0011e8d5e82178d1d13f3c1b494'); p.write_text(s)
