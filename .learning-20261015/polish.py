from pathlib import Path
import shutil

def edit(name,old,new,count=1):
    p=Path(name);s=p.read_text()
    if s.count(old)!=count: raise RuntimeError('unexpected patch count: '+name+' '+old[:80]+' '+str(s.count(old)))
    p.write_text(s.replace(old,new))

edit('src/tr/logic/LearningChooser.java','int forecasts,int fullCalls,int repairs,int events,int memories,int proposals) {}',
     'int forecasts,int fullCalls,int repairs,int events,int memories,int proposals,boolean valid) {}')
edit('src/tr/logic/LearningChooser.java','new Choice(incumbent,null,false,false,0,0,0,0,0,0);',
     'new Choice(incumbent,null,false,false,0,0,0,0,0,0,false);')
edit('src/tr/logic/LearningChooser.java','new Choice(incumbent,null,false,false,calls,full,refined,upgrades,memories,proposals);',
     'new Choice(incumbent,null,false,false,calls,full,refined,upgrades,memories,proposals,false);')
edit('src/tr/logic/LearningChooser.java','tied(paceOutcome,best.outcome()),calls,full,refined,upgrades,memories,proposals);',
     'tied(paceOutcome,best.outcome()),calls,full,refined,upgrades,memories,proposals,true);')
edit('src/tr/logic/RaceAi.java','if(learned.forecasts()>0)', 'if(learned.valid())')
edit('src/tr/logic/RaceAi.java','learned != null && learned.forecasts() > 0','learned != null && learned.valid()')
edit('src/tr/logic/LearningMemory.java','text.length()>200000','text.length()>524288')
edit('src/tr/logic/LearningMemory.java','if(!f[2].equals("-")) out.proofs[i]=ProofNumberSearch.Plan.parse(f[2]);',
     'if(!f[2].equals("-")) {\n                out.proofs[i]=ProofNumberSearch.Plan.parse(f[2]);\n                if(out.proofs[i].place()>n) throw new IllegalArgumentException("proof rank outside roster");\n            }')
edit('tools/racecraft_learning_memory.py','len(text)>200000','len(text)>524288')
edit('src/tr/logic/RacecraftReplay.java','262144','1048576',1)
edit('src/tr/logic/RacecraftReplay.java','270000','1060000',1)
edit('src/tr/logic/OpponentLeague.java','request.length()>270000','request.length()>1060000')
edit('src/tr/logic/OpponentLeague.java','if(names.length!=game.players.length)', 'if(names.length<2||names.length!=game.players.length)')
edit('tools/racecraft_validation.py','len(text) > 262144','len(text) > 1048576')
edit('tools/racecraft_corpus.py',"'tools/racecraft_corpus.py', 'tools/racecraft_validation.py',", 
     "'tools/racecraft_corpus.py', 'tools/racecraft_validation.py', 'tools/racecraft_learning_memory.py',")
edit('tests/tr/logic/LearningRacecraftTests.java','pose(game.players[1],22,8,-1,0,0);','pose(game.players[1],22,8,0,0,0);')
edit('tests/tr/logic/LearningRacecraftTests.java','check(forecast.eventCalls()<=1,"event upgrade budget overrun");',
     'check(forecast.eventCalls()==1,"event upgrade failed to fire once at the later commitment");')
edit('tests/tr/logic/LearningRacecraftTests.java','    private static void memory() throws Exception {', '''    private static void selfRepair() throws Exception {
        final RaceGame game=fixture("forecast-repair");game.players=java.util.Arrays.copyOf(game.players,2);
        pose(game.players[0],20,8,0,0,0);pose(game.players[1],26,8,0,0,0);
        final LearningForecast.Policy weak=(g,strong)->g.subgamestate==1?Direction.NONE:
                strong&&g.players[0].getPosition()[0]>21?Direction.N:Direction.E;
        final RacecraftReplay.Board root=RacecraftReplay.capture(game);
        final LearningForecast.Result old=LearningForecast.run(game,root,List.of(Direction.E),3,-1,
                new LearningForecast.Settings(0,0,0,false),weak);
        final LearningForecast.Result fixed=LearningForecast.run(game,root,List.of(Direction.E),3,-1,
                new LearningForecast.Settings(1,0,0,false),weak);
        check(old.outcome().crashed()&&fixed.outcome().status()==RacecraftOutcome.Status.RUNNING,
                "own cheap doom was not repaired at the failed decision");
        check(fixed.repairs()==1,"self repair budget not observed");
    }
    private static void memory() throws Exception {''')
edit('tests/tr/logic/LearningRacecraftTests.java','repair();memory();investment();event();proof();league();',
     'repair();selfRepair();memory();investment();event();proof();league();')
shutil.copyfile('.learning-20261015/racecraft_learning_cli.py','tests/racecraft_learning_cli.py')
shutil.copyfile('.learning-20261015/README.md','docs/experiments/learning-racecraft/README.md')
p=Path('racing-memory.md');title,rest=p.read_text().split('\n',1)
p.write_text(title+'\n\n## Learning implementation validation (2026-10-15, branch only)\n\n'
    'Integrated source dfa9856 passed the JDK 25 build, complete Java contracts and\n'
    'Python suite. Added explicit unknown-comparison fallback, consistent bounded\n'
    'rc7 state limits, self-doom and positive event-upgrade witnesses, and the\n'
    'complete-race/league CLI. No fleet improvement or promotion claimed.\n'+rest)
print('Learning state bounds, abstention semantics, positive witnesses and runner completed')
