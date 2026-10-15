from pathlib import Path
import re
import shutil

ROOT=Path('.')
def edit(path,fn):
    p=ROOT/path;s=p.read_text();p.write_text(fn(s))
def one(s,a,b):
    if s.count(a)!=1: raise RuntimeError('expected unique insertion: '+a[:100]+' count='+str(s.count(a)))
    return s.replace(a,b,1)

for p in Path('.learning-20261015').glob('*.java'):
    target=Path('tests/tr/logic' if p.name.endswith('Tests.java') else 'src/tr/logic')/p.name
    shutil.copyfile(p,target)
for name in ('racecraft_league.py','racecraft_learning_memory.py'):
    p=Path('.learning-20261015')/name
    if p.exists(): shutil.copyfile(p,Path('tools')/name)
for name in ('test_learning_protocol.py','racecraft_learning_cli.py'):
    p=Path('.learning-20261015')/name
    if p.exists(): shutil.copyfile(p,Path('tests')/name)

def config(s):
    s=one(s,'TWO_JUDGE("two-judge");','TWO_JUDGE("two-judge"), FORECAST_REPAIR("forecast-repair"), CORNER_MEMORY("corner-memory"),\n        TIME_INVESTMENT("time-investment"), EVENT_AWARE("event-aware"), PROOF_NUMBER("proof-number"),\n        LEARNING_CONTROL("learning-control");')
    s=one(s,'    final int creativeNodes, creativeTrials, selfishPlies;', '    final int creativeNodes, creativeTrials, selfishPlies;\n    final int learningNodes, learningTrials, repairAttempts, repairRewind, eventUpgrades, proofMoves;')
    s=one(s,'        capture = Boolean.parseBoolean(audit);','''        capture = Boolean.parseBoolean(audit);
        learningNodes = bounded(props,"racecraftLearningNodes",12000,0,40000);
        learningTrials = bounded(props,"racecraftLearningTrials",16,0,32);
        repairAttempts = bounded(props,"racecraftRepairAttempts",3,0,6);
        repairRewind = bounded(props,"racecraftRepairRewind",2,0,2);
        eventUpgrades = bounded(props,"racecraftEventUpgrades",1,0,4);
        proofMoves = bounded(props,"racecraftProofMoves",7,5,12);''')
    s=one(s,'                && (!creative(feature) || creativeNodes > 0 && creativeTrials > 0)',
          '                && (!creative(feature) || creativeNodes > 0 && creativeTrials > 0)\n                && (!learning(feature) || learningNodes > 0 && learningTrials > 0)')
    s=one(s,'+ ":" + creativeNodes + ":" + creativeTrials + ":" + selfishPlies; }','+ ":" + creativeNodes + ":" + creativeTrials + ":" + selfishPlies\n            + ":" + learningNodes + ":" + learningTrials + ":" + repairAttempts + ":" + repairRewind + ":" + eventUpgrades + ":" + proofMoves; }')
    s=one(s,'return feature.ordinal() >= Feature.PACE_FEINTS.ordinal();','return feature.ordinal() >= Feature.PACE_FEINTS.ordinal() && feature.ordinal() <= Feature.TWO_JUDGE.ordinal();')
    marker='    boolean any(final RaceGame game, final int player) {'
    s=one(s,marker,'''    static boolean learning(final Feature feature) { return feature.ordinal() >= Feature.FORECAST_REPAIR.ordinal(); }
    boolean learningConfigured() { for (final Feature f : features) if (learning(f)) return true; return false; }
    boolean learningEnabled(final RaceGame game, final int player) {
        return game.candidatePolicy(player) && learningConfigured() && learningNodes > 0 && learningTrials > 0;
    }
    boolean learningForecastEnabled(final RaceGame game, final int player) {
        for (final Feature f : features) if (learning(f) && f != Feature.PROOF_NUMBER && enabled(game,player,f)) return true;
        return false;
    }

'''+marker)
    return s
edit('src/tr/logic/RacecraftNext.java',config)

def memory(s):
    s=one(s,'CAPACITY = 32','CAPACITY = 64')
    s=one(s,'            final Pose start=tail.get(first).start(), end=step.end();',
        '''            if(actions.size()!=WINDOW) continue;
            final Pose start=tail.get(first).start(), end=step.end();
            boolean bends=false;
            int vx=start.vx(), vy=start.vy();
            for(final Direction a:actions) { bends|=(long)vx*(vy+a.dy)!=(long)vy*(vx+a.dx);vx+=a.dx;vy+=a.dy; }
            if(!bends) continue;''')
    s=one(s,'            if(!library.contains(segment)) { library.add(segment);if(library.size()>CAPACITY) library.remove(0); }',
        '''            boolean known=false;
            for(final Segment prior:library) known|=prior.start().sameEntry(segment.start()) && prior.actions().equals(segment.actions());
            if(!known) {
                library.add(segment);
                // Stable spatial sampling, not a FIFO that forgets lap one before lap two arrives.
                library.sort(java.util.Comparator.comparing(LearningMemory::priority));
                if(library.size()>CAPACITY) library.remove(library.size()-1);
            }''')
    s=one(s,'    private static int distance(','''    private static String priority(final Segment s) {
        final Pose p=s.start();
        return RacecraftReplay.sha(p.x()+":"+p.y()+":"+p.vx()+":"+p.vy()+":"+p.gate()+":"+p.left()+":"+s.actions());
    }
    private static int distance(''')
    return s
edit('src/tr/logic/LearningMemory.java',memory)

def game(s):
    s=one(s,'FollowupPlans followups = new FollowupPlans();','FollowupPlans followups = new FollowupPlans();\n    LearningMemory learningMemory = new LearningMemory();')
    s=s.replace('        final FollowupPlans followups;','        final FollowupPlans followups;\n        final LearningMemory learningMemory;')
    s=one(s,'            followups = game.followups.copy();','            followups = game.followups.copy();\n            learningMemory = game.learningMemory.copy();')
    s=one(s,'            game.followups = followups.copy();','            game.followups = followups.copy();\n            game.learningMemory = learningMemory.copy();')
    # reset paths; exclude the field declaration handled above
    s=re.sub(r'(?m)^(\s*)followups = new FollowupPlans\(\);',r'\1followups = new FollowupPlans();\n\1learningMemory = new LearningMemory();',s)
    return s
edit('src/tr/logic/RaceGame.java',game)

def replay(s):
    s=one(s,'final String identity, plans;', 'final String identity, plans, learning;')
    old='''                final String identity, final int[][] cars, final String plans) {
            this.plans = plans;'''
    new='''                final String identity, final int[][] cars, final String plans) {
            this(turn,laps,slot,first,last,identity,cars,plans,"-");
        }
        Board(final int turn, final int laps, final int slot, final int first, final int last,
                final String identity, final int[][] cars, final String plans, final String learning) {
            this.learning=learning;
            this.plans = plans;'''
    s=one(s,old,new)
    s=one(s,'new StringBuilder(plans.equals("-") ? "rc3,"', 'new StringBuilder(!learning.equals("-") ? "rc7," : plans.equals("-") ? "rc3,"')
    s=one(s,'if (!plans.equals("-")) out.append(\',\').append(plans);','if (!plans.equals("-") || !learning.equals("-")) out.append(\',\').append(plans);\n            if (!learning.equals("-")) out.append(\',\').append(learning);')
    s=one(s,'identity(game), cars, game.followups.encode(cars.length));','identity(game), cars, game.followups.encode(cars.length), game.learningMemory.encode(cars.length));')
    old='(h.length == 8 && (h[0].equals("rc4") || h[0].equals("rc5") || h[0].equals("rc6")))'
    s=one(s,old,old+' || (h.length == 9 && h[0].equals("rc7"))')
    s=one(s,'final String plans = h.length == 8 ? h[7] : "-";', 'final String plans = h.length >= 8 ? h[7] : "-";\n        final String learning = h.length == 9 ? h[8] : "-";\n        LearningMemory.parse(learning, n);')
    s=one(s,'final String version = plans.equals("-") ? "rc3"', 'final String version = !learning.equals("-") ? "rc7" : plans.equals("-") ? "rc3"')
    s=one(s,'return new Board(turn, laps, slot, first, last, h[6], rows, plans);','return new Board(turn, laps, slot, first, last, h[6], rows, plans, learning);')
    s=one(s,'        final FollowupPlans followups;', '        final FollowupPlans followups;\n        final LearningMemory learningMemory;')
    s=one(s,'            followups = game.followups;', '            followups = game.followups;\n            learningMemory = game.learningMemory;')
    s=one(s,'            game.followups = FollowupPlans.parse(board.plans, detached.length);','            game.followups = FollowupPlans.parse(board.plans, detached.length);\n            game.learningMemory = LearningMemory.parse(board.learning, detached.length);')
    s=one(s,'            game.followups = followups;', '            game.followups = followups;\n            game.learningMemory = learningMemory;')
    s=one(s,'|| game.racecraftNext.creativeConfigured()', '|| game.racecraftNext.creativeConfigured() || game.racecraftNext.learningConfigured()')
    return s
edit('src/tr/logic/RacecraftReplay.java',replay)

# Mapped one-move debt is an overload: older ambush flag retains exactly zero debt.
def ambush(s):
    anchor='''            final Target target, final StrategyState.Budget budget) {
        final List<List<Direction>> result = new ArrayList<>();'''
    s=one(s,anchor,'''            final Target target, final StrategyState.Budget budget) {
        return intercept(game,initial,target,budget,0);
    }
    static List<List<Direction>> intercept(final RaceGame game, final CreativePaths.Own initial,
            final Target target, final StrategyState.Budget budget, final int allowance) {
        if(allowance<0||allowance>1) throw new IllegalArgumentException("investment allowance");
        final List<List<Direction>> result = new ArrayList<>();''')
    return one(s,'k, new ArrayList<>(), startDistance, result, budget);','k, new ArrayList<>(), startDistance + allowance, result, budget);')
edit('src/tr/logic/AmbushPlans.java',ambush)

def ai(s):
    s=one(s,'private final RaceGame game;', 'private final RaceGame game;\n    private ProofNumberSearch.Plan pendingLearningProof;\n    private Direction pendingLearningAction;\n    private String pendingLearningKey;')
    s=one(s,'        if (root) {\n            inheritedFollowup', '        if (root) {\n            pendingLearningProof=null; pendingLearningAction=null; pendingLearningKey=null;\n            inheritedFollowup')
    # Future tails from the new arms use the established commit-only infrastructure.
    s=s.replace('|| game.racecraftNext.creativeEnabled(game, playerNum)',
                '|| game.racecraftNext.creativeEnabled(game, playerNum) || game.racecraftNext.learningForecastEnabled(game, playerNum)')
    s=one(s,'    void commitResearchPlan(final Direction action) {','''    void commitResearchPlan(final Direction action) {
        if (game.racecraftNext.learningConfigured()) {
            final ProofNumberSearch.Plan installed = pendingLearningProof != null && action == pendingLearningAction
                    && pendingLearningKey != null && pendingLearningKey.equals(FollowupPlans.key(game)) ? pendingLearningProof : null;
            game.learningMemory.proof(game.subgamestate, installed);
            game.learningMemory.commitCorner(game,action);
            pendingLearningProof=null; pendingLearningAction=null; pendingLearningKey=null;
        }''')
    s=one(s,'&& !game.racecraftNext.creativeConfigured()) return;', '&& !game.racecraftNext.creativeConfigured() && !game.racecraftNext.learningConfigured()) return;')
    s=one(s,'|| game.racecraftNext.creativeEnabled(game, player);','|| game.racecraftNext.creativeEnabled(game, player) || game.racecraftNext.learningForecastEnabled(game, player);')
    marker='''        if (trafficFeature(playerNum, RacecraftNext.Feature.FORCED_SEQUENCE)) {'''
    s=one(s,marker,'''        if (!creativeModel && trafficFeature(playerNum, RacecraftNext.Feature.PROOF_NUMBER)) {
            final ProofNumberSearch.Result proof=LearningTactics.proof(game);
            if(proof.action()!=null) {
                pendingLearningProof=proof.plan(); pendingLearningAction=proof.action(); pendingLearningKey=FollowupPlans.key(game);
                return proof.action();
            }
        }
'''+marker)
    s=one(s,'&& !manoeuvre && !creativeRoot(playerNum)) return best;', '&& !manoeuvre && !creativeRoot(playerNum) && !learningRoot(playerNum)) return best;')
    anchor='''        if (real) auditOpening = planned;
        // Preserve current master 301a'''
    s=one(s,anchor,'''        LearningChooser.Choice learned=null;
        if(learningRoot(playerNum)) {
            learned=LearningChooser.choose(game,planned,cands,pace,inheritedTraffic,d -> {
                final int nvx=vel[0]+d.dx,nvy=vel[1]+d.dy;
                return relevantRival(playerNum,pos,pos[0]+nvx,pos[1]+nvy,nvx,nvy);
            });
            if(learned.forecasts()>0) {
                planned=learned.action();
                if(learned.tail()!=null) { pendingFirst=planned;pendingFollowup=learned.tail(); }
                if(game.racecraftNext.capture&&!game.racecraftReplay)
                    System.err.println("RACECRAFT_LEARNING p="+playerNum+" forecasts="+learned.forecasts()+" full="+learned.fullCalls()
                            +" repairs="+learned.repairs()+" events="+learned.events()+" memories="+learned.memories()+" proposals="+learned.proposals());
            }
        }
        if (real) auditOpening = planned;
        // Preserve current master 301a''')
    s=one(s,'chooserJudgedPace = addPace || paceInSet && paceVerdict != pickVerdict;',
        'chooserJudgedPace = learned != null && learned.forecasts() > 0\n                ? addPace || paceInSet && !learned.paceTied() : addPace || paceInSet && paceVerdict != pickVerdict;')
    anchor='    private boolean nextEnabled(final int player, final RacecraftNext.Feature feature) {'
    s=one(s,anchor,'''    private boolean learningRoot(final int player) {
        return simDepth==0 && !inScorerSim && !creativeModel && trueConfirmDepth==0
                && game.racecraftNext.learningForecastEnabled(game,player) && LearningTactics.near(game);
    }

'''+anchor)
    return s
edit('src/tr/logic/RaceAi.java',ai)
edit('src/tr/logic/MoveQueries.java',lambda s:one(s,'        if (line.startsWith("cf4,"))', '        if (line.startsWith("league1,")) return OpponentLeague.answer(game,line);\n        if (line.startsWith("cf4,"))'))

# Canonical rc7 carries archives, rolling committed observations and proof tables.
def validation(s):
    s='import racecraft_learning_memory\n'+s if not s.startswith('from __future__') else s
    # Import after __future__, wherever the existing module header puts it.
    if 'import racecraft_learning_memory' not in s:
        s=s.replace('import hashlib','import hashlib\nimport racecraft_learning_memory')
    old="(len(header) == 8 and header[0] in ('rc4', 'rc5', 'rc6'))"
    s=one(s,old,old+" or (len(header) == 9 and header[0] == 'rc7')")
    s=one(s,'    if len(header) == 8:', '    if len(header) >= 8:')
    s=one(s,"        version = 'rc6' if 'R_'", "        version = 'rc7' if len(header) == 9 else 'rc6' if 'R_'")
    # rc7 may have no older pending plan at all.
    s=one(s,"        plans = header[7].split('.')", "        plans = ['-'] * len(rows) if len(header) == 9 and header[7] == '-' else header[7].split('.')")
    anchor='    if not 1 <= n <= 9 or any(len(row) != 14 for row in rows):'
    s=one(s,anchor,"    if len(header) == 9:\n        racecraft_learning_memory.validate(header[8], n)\n        if header[8] == '-': raise ValueError('noncanonical empty rc7 memory')\n"+anchor)
    return s
edit('tools/racecraft_validation.py',validation)
def corpus(s):
    old="(len(h) == 8 and h[0] in ('rc4', 'rc5', 'rc6'))"
    return one(s,old,old+" or (len(h) == 9 and h[0] == 'rc7')")
edit('tools/racecraft_corpus.py',corpus)

p=Path('run_tests.sh');s=p.read_text();s+='\njava -ea -Djava.awt.headless=true -cp test-bin tr.logic.LearningRacecraftTests\n';p.write_text(s)
notes=Path('docs/experiments/learning-racecraft');notes.mkdir(parents=True,exist_ok=True)
if Path('.learning-20261015/README.md').exists(): shutil.copyfile('.learning-20261015/README.md',notes/'README.md')
p=Path('racing-memory.md');title,body=p.read_text().split('\n',1)
p.write_text(title+'\n\n## Learning racecraft research (2026-10-15, branch only)\n\n'
    'Current aware champion and exact speed optimisations retained. New independently gated\n'
    'forecast repair/rewind, committed cross-lap corner experience, one-move time-investment\n'
    'proposals, event-triggered upgrades, and proof-number tactics. Offline competitive\n'
    'league evolves own-place-first counterpolicies. rc7 binds the complete experience and\n'
    'executable proof state; queries do not train it, Undo restores it. Defaults, computed\n'
    'starts and the 20-cell solo rule unchanged. Functional validation in progress; no\n'
    'fleet gain or promotion claimed. See docs/experiments/learning-racecraft.\n'+body)
print('Applied six learning experiments; no champion promotion or performance claim')
