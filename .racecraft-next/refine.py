from pathlib import Path

p = Path('src/tr/logic/RacecraftNext.java')
s = p.read_text()
if 'boolean driving(' not in s:
    s = s.replace('    String signature()', '''    boolean driving(final RaceGame game, final int player) {
        return enabled(game, player, Feature.CRASH_RANK) || enabled(game, player, Feature.RANK_TIME)
                || enabled(game, player, Feature.OPENING);
    }

    String signature()''')
p.write_text(s)
p = Path('src/tr/logic/RaceAi.java')
s = p.read_text()
s = s.replace('game.racecraftNext.any(game, playerNum)', 'game.racecraftNext.driving(game, playerNum)')
if 'private boolean researchSurvives' not in s:
    anchor = '    private boolean researchFinishes(final int legacy) {'
    s = s.replace(anchor, '''    private boolean researchSurvives(final int legacy) {
        return !lastResearchRankTime ? legacy >= 0 : lastResearchOutcome != null
                && lastResearchOutcome.known() && !lastResearchOutcome.crashed();
    }

''' + anchor)
    # Only the two existing rescue confirmations, not arbitrary caller pass/fail gates.
    start = s.index('\t\t\t\t\tsurvives = simOutcome(')
    end = s.index('\n\t\t\t\t} finally', start)
    part = s[start:end]
    assert part.count(' >= 0') == 2
    part = part.replace('simOutcome(', 'researchSurvives(simOutcome(').replace(' >= 0', ')')
    s = s[:start] + part + s[end:]
p.write_text(s)
p = Path('tools/racecraft_corpus.py')
s = p.read_text()
anchor = "    trials = answer.get('trials', [])"
if 'counterfactual board identity mismatch' not in s:
    s = s.replace(anchor, "    if answer.get('rootIdentity') != board(case['snapshot'])[0][6]:\n        raise ValueError('counterfactual board identity mismatch')\n" + anchor)
p.write_text(s)
p = Path('tests/test_racecraft_corpus.py')
s = p.read_text()
anchor = '    def test_shortlist_not_forecast_error(self):'
if 'def test_wrong_root' not in s:
    s = s.replace(anchor, '''    def test_wrong_root(self):
        response = self.response(trial('E', 1, 7))
        response['rootIdentity'] = 'another-board'
        with self.assertRaises(ValueError):
            corpus.analyze(case(), response)

''' + anchor)
p.write_text(s)
p = Path('racing-memory.md')
s = p.read_text()
entry = '''## Branch research: outcome ranks, opening plans and counterfactual corpus (2026-09-28)

Owner request: implement review ideas 1, 2, 4 and 6 on a branch; examine 3
critically. Branch `work/racecraft-outcomes-opening-20260928`, pinned base
`955001104bbe315cf9b82a1cd2dfb447beddd211`. No champion promotion. The
independent queued master arms (291/293/294/295) are not silently imported.

Implemented behind `candidateSlots` AND `racecraftNext` feature flags:
`crash-rank` preserves retirement order only when every considered action
forecasts a known crash; unknown is not a crash. `rank-time` carries own
elapsed moves and remaining moves separately, compares confirmed rescue
outcomes by place/time rather than speed, and keeps finish/survival tests
explicit. `opening` searches bounded first/second action pairs in the first
four roster rounds; the observed board is replanned next turn and downstream
pace/guards retain authority. `start-ties` compares at most four solo-equal
cells for the final AI placer, with every other placement already observed;
it does not alter the later driving policy. New driving arms respect the
canonical 20-cell solo gate. Default flags are empty.

Item 3 is an offline, shadow-only interaction diagnostic, not a live subset
selector or extra caution penalty: conservative pre/post-action envelopes,
including possible indirect blockers via two-hop links. No pruning guarantee
or opponent coalition is claimed. See the branch design for why breadth
should remain the measured baseline until subset selection earns its cost.

Item 6: explicit rc3 snapshots (including exact left-grid and classification
ledgers), bounded cf3 complete referee tails for every legal first action,
actual-action replay validation, input hashes and place-regret diagnoses.
Unknown/incomplete tails are never training labels. Human-roster continuation
models and learned policies are not invented. Existing V2 stays unchanged.

The initial JDK 25 build, original Java/Python contracts and new crash-rank,
finish-time, opening-budget, placement-isolation and actual-referee replay
contracts passed in the tested integration d39701b. The first replay test
caught and fixed a last-survivor counter mismatch rather than changing the
expected referee behavior. Expanded CLI/default-identity and corpus checks
are separate; their executed results belong in the experiment validation
record. No new mirrored fleet, lone-candidate place gain or CPU speedup is
claimed. Master, physics, maps, tracks, goldens and user.properties unchanged.

'''
if '## Branch research: outcome ranks, opening plans' not in s:
    lines = s.splitlines(keepends=True)
    s = lines[0] + '\n' + entry + ''.join(lines[1:]).lstrip('\n')
p.write_text(s)
print('Refined explicit outcomes, placement isolation, corpus identity and campaign ledger')
