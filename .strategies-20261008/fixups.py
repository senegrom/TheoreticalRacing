from pathlib import Path

p=Path('src/tr/logic/ResponseStrategies.java');s=p.read_text().replace('MAX_STATES = 128','MAX_STATES = 256');p.write_text(s)
for name in ('src/tr/logic/RacecraftReplay.java','tools/racecraft_validation.py'):
    p=Path(name);s=p.read_text().replace('> 131072','> 262144').replace('len(nodes) <= 128','len(nodes) <= 256');p.write_text(s)
p=Path('src/tr/logic/PlaceCertificates.java');s=p.read_text()
s=s.replace('for (final Direction action : root.legal(game, true)) {',
'''final java.util.List<Direction> roots = new java.util.ArrayList<>(root.legal(game, true));
        roots.sort(java.util.Comparator.comparingInt(d -> TrafficOpportunities.ownDistance(game, root.slot(), d)));
        for (final Direction action : roots) {''')
s=s.replace('if (freePly) forcedNodes++;',
'''if (freePly) forcedNodes++;
            if (ourTurn) for (final Direction action : legal) {
                final RaceGame.MoveResult finish = state.evaluate(game, action);
                if (finish != null && finish.finishes()) return new Bound(state.board.first + 1, 1);
            }''')
p.write_text(s)
p=Path('tests/tr/logic/StrategyResearchTests.java');s=p.read_text()
s=s.replace('g.trackA=new Area(strip);g.startZoneA=new Area();g.finishLine=',
'''g.trackA=new Area(strip);g.startZoneA=new Area();
        set(g,"legalRaster",null);set(g,"subRaster",null);
        g.finishLine=''')
s=s.replace('"thin oblique lane is not physically forced"','"thin oblique lane is not physically forced: "+root.legal(g,false)')
s=s.replace('g.ai.commitResearchPlan(a);\n            check(!g.followups.encode(2).equals("-"),',
'''final String request="cf4,300,"+a+"|"+before;
            final String answer=RacecraftReplay.answer(g,request);
            check(answer.contains(RacecraftReplay.sha(request)) && before.equals(RacecraftReplay.snapshot(g)),
                    "response-memory replay lost request binding or mutated live state");
            g.ai.computeAiMove();
            g.ai.commitResearchPlan(a);
            check(!g.followups.encode(2).equals("-"),''')
p.write_text(s)
