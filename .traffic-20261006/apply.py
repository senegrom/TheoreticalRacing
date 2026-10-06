#!/usr/bin/env python3
"""One-shot assembly on the explicitly pinned research branch; no force pushes."""
from pathlib import Path
import difflib
import subprocess

MASTER = '82d259a217c23991cec7adc164c81f48e575c88c'
BASE = 'b54e9bb05f91c0011e8d5e82178d1d13f3c1b494'
STAGE = Path('.traffic-20261006')
AI = Path('src/tr/logic/RaceAi.java')

def show(ref, path):
    return subprocess.check_output(['git', 'show', f'{ref}:{path}'], text=True)

def bounds(text, marker):
    start = text.index(marker)
    brace = text.index('{', start)
    depth = 1
    for i in range(brace + 1, len(text)):
        if text[i] == '{': depth += 1
        elif text[i] == '}': depth -= 1
        if depth == 0: return start, i + 1
    raise AssertionError('unterminated method ' + marker)

def replace_method(text, marker, replacement):
    a, b = bounds(text, marker)
    return text[:a] + replacement.rstrip() + text[b:]

def one(text, old, new):
    if text.count(old) != 1:
        raise AssertionError(f'expected one anchor ({text.count(old)}): {old[:160]!r}')
    return text.replace(old, new, 1)

def import_delta(ours, base, theirs):
    """Apply only exact, uniquely anchored master edits outside the chooser.
    Refuse overlap/ambiguity rather than silently selecting one conflict side."""
    a, b = base.splitlines(keepends=True), theirs.splitlines(keepends=True)
    edits = []
    for tag, i, j, k, l in difflib.SequenceMatcher(None, a, b, autojunk=False).get_opcodes():
        if tag == 'equal': continue
        old, new = ''.join(a[i:j]), ''.join(b[k:l])
        before, after = ''.join(a[max(0, i-30):i]), ''.join(a[j:j+30])
        if old:
            positions, start = [], 0
            while (pos := ours.find(old, start)) >= 0:
                positions.append(pos); start = pos + 1
            if not positions: raise AssertionError('master edit overlaps branch outside chooser: ' + old[:180])
            if len(positions) > 1:
                def score(pos):
                    left = next((n for n in range(min(len(before),pos),-1,-1) if ours[pos-n:pos] == before[len(before)-n:]),0)
                    end = pos + len(old)
                    right = next((n for n in range(min(len(after),len(ours)-end),-1,-1) if ours[end:end+n] == after[:n]),0)
                    return left + right
                scored = sorted(((score(p), p) for p in positions), reverse=True)
                if scored[0][0] < 12 or scored[0][0] == scored[1][0]: raise AssertionError('ambiguous master edit')
                pos = scored[0][1]
            else: pos = positions[0]
        else:
            pos = None
            for n in range(len(before), 11, -1):
                anchor = before[-n:]
                if ours.count(anchor) == 1: pos = ours.index(anchor) + len(anchor); break
            if pos is None:
                for n in range(len(after), 11, -1):
                    anchor = after[:n]
                    if ours.count(anchor) == 1: pos = ours.index(anchor); break
            if pos is None: raise AssertionError('unanchored master insertion: ' + new[:180])
        edits.append((pos, pos + len(old), new))
    ordered = sorted(edits)
    if any(x[1] > y[0] for x,y in zip(ordered, ordered[1:])): raise AssertionError('overlapping integration edits')
    for start, end, new in reversed(ordered): ours = ours[:start] + new + ours[end:]
    return ours

ours = AI.read_text()
base, master = show(BASE, str(AI)), show(MASTER, str(AI))
marker = '\tprivate Direction jointChooser('
masked = [replace_method(t, marker, '/* TRAFFIC_CHOOSER_SLOT */') for t in (ours, base, master)]
integrated = import_delta(*masked)
assert 'allScorerRolloutDepth' in integrated and 'chooserJudgedPace' in integrated and 'Round 300a' in integrated
subprocess.run(['git','merge','--no-commit','--no-ff',MASTER], check=False)
conflicts = subprocess.check_output(['git','diff','--name-only','--diff-filter=U'],text=True).splitlines()
if set(conflicts) - {str(AI), 'racing-memory.md'}: raise AssertionError('unreviewed merge conflict: '+repr(conflicts))
branch_memory, master_memory = show('HEAD','racing-memory.md'), show(MASTER,'racing-memory.md')
heading = "## The owner's computed-start rule (2026-10-02)"
branch_notes = branch_memory[branch_memory.index('\n\n')+2:branch_memory.index(heading)]
header_end = master_memory.index('\n\n') + 2
Path('racing-memory.md').write_text(master_memory[:header_end] + branch_notes + master_memory[header_end:])
s = one(integrated, '/* TRAFFIC_CHOOSER_SLOT */', (STAGE/'chooser.txt').read_text())

# Scoped, independently enabled policy arms.
p = Path('src/tr/logic/RacecraftNext.java'); t=p.read_text()
t=one(t,'TACTICAL_EXTENSION("tactical-extension");','TACTICAL_EXTENSION("tactical-extension"), DENIAL("denial"), MANOEUVRE("manoeuvre"),\n        CHECKPOINT_TRAFFIC("checkpoint-traffic"), DECISION_ENDPOINT("decision-endpoint"),\n        STAGED_ORDER("staged-order"), SHORT_TRANSITIONS("short-transitions");')
t=one(t,'    final int adaptiveNodes, adaptiveCycles, recoveryTrials, tacticalExtraRounds;','    final int adaptiveNodes, adaptiveCycles, recoveryTrials, tacticalExtraRounds;\n    final int manoeuvreNodes, manoeuvreDepth;')
t=one(t,'        adaptiveNodes = bounded(', '        manoeuvreNodes = bounded(props, "racecraftManoeuvreNodes", 192, 0, 2048);\n        manoeuvreDepth = bounded(props, "racecraftManoeuvreDepth", 4, 2, 4);\n        adaptiveNodes = bounded(')
t=one(t,'&& (feature != Feature.ADAPTIVE_ESCAPE || adaptiveNodes > 0)','&& (feature != Feature.MANOEUVRE || manoeuvreNodes > 0)\n                && (feature != Feature.ADAPTIVE_ESCAPE || adaptiveNodes > 0)')
t=one(t,'+ ":" + adaptiveNodes + ":" + adaptiveCycles + ":" + recoveryTrials + ":" + tacticalExtraRounds;', '+ ":" + adaptiveNodes + ":" + adaptiveCycles + ":" + recoveryTrials + ":" + tacticalExtraRounds\n            + ":" + manoeuvreNodes + ":" + manoeuvreDepth;')
p.write_text(t)

# Root plan ownership, including independently enabled mid-race manoeuvres.
s=one(s,'            inheritedFollowup = null; pendingFollowup = null; pendingFirst = null; decisionRootKey = null;',
'''            inheritedFollowup = null; inheritedTraffic = null; pendingFollowup = null; pendingFirst = null; decisionRootKey = null;
            trafficDenials = trafficCheckpointTrials = trafficManoeuvreNodes = trafficManoeuvreForecasts = 0;''')
s=one(s,'            if (game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.FOLLOWUP)) {',
'''            if (game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.FOLLOWUP)
                    || game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)) {''')
s=one(s,'                inheritedFollowup = entry == null ? null : entry.action();',
'''                if (entry != null && entry.traffic() && game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.MANOEUVRE)) inheritedTraffic = entry;
                if (entry != null && !entry.traffic() && game.racecraftNext.enabled(game, playerNum, RacecraftNext.Feature.FOLLOWUP)) inheritedFollowup = entry.action();''')
s=one(s,'        if (!game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP)) return;',
'''        if (!game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP)
                && !game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE)) return;''')
s=one(s,'                        RacecraftNext.Feature.FOLLOWUP)\n                && decisionRootKey.equals',
'''                        pendingFollowup.traffic() ? RacecraftNext.Feature.MANOEUVRE : RacecraftNext.Feature.FOLLOWUP)
                && decisionRootKey.equals''')
s=one(s,'        if (root && pendingFirst != decision) pendingFollowup = null;',
'''        if (root && pendingFirst != decision) pendingFollowup = null;
        if (capture) System.err.println("RACECRAFT_TRAFFIC p=" + playerNum + " denial=" + trafficDenials
                + " checkpointTrials=" + trafficCheckpointTrials + " nodes=" + trafficManoeuvreNodes
                + " forecasts=" + trafficManoeuvreForecasts);''')

# Retain full bounded suffixes; old opening entries and rc3/rc4 stay readable.
p=Path('src/tr/logic/FollowupPlans.java'); t=p.read_text(); a=t.index('    record Entry('); b=t.index('    static String key(')
t=t[:a]+'''    record Entry(java.util.List<Direction> actions, String expectedKey, boolean traffic) {
        Entry {
            actions = java.util.List.copyOf(actions);
            if (actions.isEmpty() || actions.size() > (traffic ? 3 : 1) || expectedKey == null
                    || !expectedKey.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("invalid follow-up");
        }
        Entry(final Direction action, final String expectedKey) { this(java.util.List.of(action), expectedKey, false); }
        Direction action() { return actions.getFirst(); }
        static Entry traffic(final java.util.List<Direction> actions, final String key) { return new Entry(actions,key,true); }
    }
    private final Entry[] entries = new Entry[9];
    Entry find(final RaceGame game) {
        final Entry entry = entries[game.subgamestate];
        return entry != null && entry.expectedKey().equals(key(game)) ? entry : null;
    }
    void put(final int slot, final Entry entry) { entries[slot] = entry; }
    FollowupPlans copy() {
        final FollowupPlans result = new FollowupPlans();
        System.arraycopy(entries,0,result.entries,0,entries.length); return result;
    }
    String encode(final int players) {
        boolean any = false;
        for (int i=0;i<players;i++) any |= entries[i]!=null;
        if (!any) return "-";
        final StringBuilder out = new StringBuilder();
        for (int i=0;i<players;i++) {
            if(i>0) out.append('.');
            final Entry e=entries[i];
            if(e==null) { out.append('-'); continue; }
            if(e.traffic()) out.append("M_");
            out.append(String.join("+",e.actions().stream().map(Enum::name).toList())).append('~').append(e.expectedKey());
        }
        return out.toString();
    }
    static FollowupPlans parse(final String text, final int players) {
        final FollowupPlans result=new FollowupPlans();
        if(players<1||players>9) throw new IllegalArgumentException("follow-up roster mismatch");
        if(text.equals("-")) return result;
        final String[] parts=text.split("\\\\.",-1);
        if(parts.length!=players) throw new IllegalArgumentException("follow-up roster mismatch");
        for(int i=0;i<players;i++) {
            if(parts[i].equals("-")) continue;
            final String[] fields=parts[i].split("~",-1);
            if(fields.length!=2) throw new IllegalArgumentException("invalid follow-up encoding");
            final boolean traffic=fields[0].startsWith("M_");
            final String spec=traffic?fields[0].substring(2):fields[0];
            final java.util.List<Direction> actions=Arrays.stream(spec.split("\\\\+",-1)).map(Direction::valueOf).toList();
            result.entries[i]=new Entry(actions,fields[1],traffic);
        }
        return result;
    }

'''+t[b:]; p.write_text(t)
p=Path('src/tr/logic/RacecraftReplay.java');t=p.read_text()
t=one(t,'private static final class Scope','static final class Scope')
t=one(t,'private static boolean classifyLast','static boolean classifyLast')
t=one(t,'plans.equals("-") ? "rc3," : "rc4,"','plans.equals("-") ? "rc3," : plans.contains("M_") ? "rc5," : "rc4,"')
t=one(t,'h.length == 8 && h[0].equals("rc4")','h.length == 8 && (h[0].equals("rc4") || h[0].equals("rc5"))')
t=one(t,'        FollowupPlans.parse(plans, n);','        FollowupPlans.parse(plans, n);\n        if (plans.contains("M_") != h[0].equals("rc5")) throw new IllegalArgumentException("noncanonical plan version");')
t=t.replace('game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP)', '(game.racecraftNext.configured(RacecraftNext.Feature.FOLLOWUP) || game.racecraftNext.configured(RacecraftNext.Feature.MANOEUVRE))')
p.write_text(t)
p=Path('tools/racecraft_validation.py');t=p.read_text()
t=one(t,"header[0] == 'rc4'", "header[0] in ('rc4', 'rc5')")
t=one(t,"        if len(plans) != n or any(p != '-' and not re.fullmatch(r'(?:NW|N|NE|W|NONE|E|SW|S|SE)~[0-9a-f]{64}', p) for p in plans):", '''        atom = r'(?:NW|N|NE|W|NONE|E|SW|S|SE)'
        pattern = rf'(?:{atom}|M_{atom}(?:\\+{atom}){{0,2}})~[0-9a-f]{{64}}'
        if ('M_' in header[7]) != (header[0] == 'rc5'):
            raise ValueError('noncanonical plan version')
        if len(plans) != n or any(p != '-' and not re.fullmatch(pattern, p) for p in plans):''')
p.write_text(t)
p=Path('tools/racecraft_corpus.py'); t=p.read_text();
if "('rc3', 'rc4')" not in t: raise AssertionError('capture protocol anchor changed')
t=t.replace("('rc3', 'rc4')", "('rc3', 'rc4', 'rc5')");p.write_text(t)

# Checkpoint shortlist stays exactly on the best eligible solo plateau.
a,b=bounds(s,'\tprivate Direction bestCheckpointMove(');body=s[a:b]
body=one(body,'\t\tint bestValue = Integer.MAX_VALUE;', '''        final int[] values = trafficFeature(playerNum, RacecraftNext.Feature.CHECKPOINT_TRAFFIC) ? new int[9] : null;
        if (values != null) java.util.Arrays.fill(values, Integer.MAX_VALUE);
\t\tint bestValue = Integer.MAX_VALUE;''')
body=one(body,'\t\t\tif (value < bestValue) {','            if (values != null) values[d.ordinal()] = value;\n\t\t\tif (value < bestValue) {')
body=one(body,'\t\treturn best;', '        return values == null ? best : checkpointTrafficChoice(pos, vel, playerNum, best, values, bestValue);')
s=s[:a]+body+s[b:]

# Staged proposals remain subject to the same admission and downstream guards.
a,b=bounds(s,'\tprivate Direction stagedPaceOverride(');body=s[a:b]
body=one(body,'\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];','        final boolean ranked = trafficFeature(playerNum, RacecraftNext.Feature.STAGED_ORDER);\n\t\tfinal int chosenT = turnsByDir[chosen.ordinal()];')
body=one(body,'\t\tdouble bestRestDelta = Double.MAX_VALUE;','        int bestFinal = -1;\n\t\tdouble bestRestDelta = Double.MAX_VALUE;')
body=body.replace('scorerFieldOutcome(', 'stagedForecast(')
body=one(body,'if (chosenFinal < 0)','if (chosenFinal < 0 || ranked && chosenFinal == Integer.MAX_VALUE)')
body=one(body,'if (best == null || restDelta < bestRestDelta)', 'if (best == null || (ranked ? TrafficOpportunities.stagedBetter(candidateFinal, restDelta, bestFinal, bestRestDelta) : restDelta < bestRestDelta))')
body=one(body,'\t\t\t\tbest = d;', '\t\t\t\tbest = d;\n                bestFinal = candidateFinal;')
s=s[:a]+body+s[b:]

# Correct only top-level short projections in this independent experiment.
a,b=bounds(s,'\tprivate void simulateRoundPass(');body=s[a:b];brace=body.index('{')+1
body=body[:brace]+'''\n        if (trafficFeature(playerNum, RacecraftNext.Feature.SHORT_TRANSITIONS)) {
            shortRoundPass(playerNum, occupancy, simulatedVelocity, blockedOccupancy, nextPosition, nextVelocity);
            return;
        }
'''+body[brace:];s=s[:a]+body+s[b:]

# Normalise only chooser/tactical comparison cutoffs, never proof depths.
a,b=bounds(s,'    private TacticalComparison.Evaluation tacticalForecast(');body=s[a:b]
body=one(body,'final int demand = researchDemandDepth, probe = tacticalProbeDepth;', 'final int demand = researchDemandDepth, probe = tacticalProbeDepth, endpoint = decisionEndpointDepth;')
body=one(body,'        tacticalEndpoint = false;', '        tacticalEndpoint = false;\n        decisionEndpointDepth = trafficFeature(player, RacecraftNext.Feature.DECISION_ENDPOINT) ? simDepth + 1 : -1;')
body=one(body,'researchDemandDepth = demand; tacticalProbeDepth = probe; tacticalEndpoint = oldEndpoint;', 'researchDemandDepth = demand; tacticalProbeDepth = probe; tacticalEndpoint = oldEndpoint; decisionEndpointDepth = endpoint;')
s=s[:a]+body+s[b:]
a,b=bounds(s,'\tprivate int simOutcomeCore(');body=s[a:b]
body=one(body,'\t\tfor (int round = 0; round < rounds && !raceOver; round++) {', '''        final boolean decisionAligned = candidatePending && simDepth == decisionEndpointDepth;
\t\tfor (int round = 0; round < rounds + (decisionAligned ? 1 : 0) && !raceOver; round++) {''')
body=one(body,'for (int i = from; i < game.players.length; i++)', 'for (int i = from; i < (decisionAligned && round == rounds ? myIdx : game.players.length); i++)')
s=s[:a]+body+s[b:]
s=s.rstrip()[:-1]+(STAGE/'hooks.txt').read_text()+'\n}\n';AI.write_text(s)
for name in ['TrafficOpportunities.java','TrafficManoeuvres.java']:
    Path('src/tr/logic',name).write_text((STAGE/name).read_text())
for name in ['TrafficRacecraftTests.java']:
    Path('tests/tr/logic',name).write_text((STAGE/name).read_text())
Path('tests/test_traffic_protocol.py').write_text((STAGE/'test_traffic_protocol.py').read_text())
p=Path('run_tests.sh');p.write_text(p.read_text()+'\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.TrafficRacecraftTests\n')
p=Path('.github/workflows/racecraft-next.yml');t=p.read_text().replace('1c50a5cb740c2deb9bd8bf8a588c8693e4335aae',MASTER);p.write_text(t)
Path('tests/racecraft_traffic_cli.py').write_text((STAGE/'racecraft_traffic_cli.py').read_text())
p=Path('racing-memory.md');t=p.read_text();at=t.index('\n\n')+2
note='''## Peer traffic-opportunity experiments (2026-10-06, not promoted)

Integrated current master 82d259a, preserving 281/292b/299/300a and the owner rules.
Independent candidate-only flags: denial, manoeuvre, checkpoint-traffic,
decision-endpoint, staged-order, short-transitions. The multi-move graph nominates
at most two trajectories; every proposal and the incumbent are reforecast under
one common all-scorer continuation with exact referee transitions. Its schedule
is only a proposal model. Bounded suffixes are committed/read/replayed/undone as
policy state (rc5); hints do not consume them. Existing experiment flags remain.
No map, user.properties, fleet track, default policy, or master modification.
No performance or promotion evidence is claimed. Test results are recorded in
docs/experiments/traffic-opportunities/validation.json only after execution.

'''
p.write_text(t[:at]+note+t[at:])
Path('docs/experiments/traffic-opportunities').mkdir(parents=True,exist_ok=True)
Path('docs/experiments/traffic-opportunities/README.md').write_text((STAGE/'README.md').read_text())
subprocess.run(['git','add','src','tests','tools','run_tests.sh','racing-memory.md','docs','.github/workflows/racecraft-next.yml'],check=True)
if subprocess.check_output(['git','diff','--name-only','--diff-filter=U'],text=True).strip(): raise AssertionError('unresolved merge')
print('Integrated current master and applied six independent traffic experiments.')
