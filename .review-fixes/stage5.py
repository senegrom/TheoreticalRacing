from pathlib import Path
p=Path('tests/tr/logic/RacecraftFixTests.java'); s=p.read_text()
if 'midRaceReferee();' not in s:
    s=s.replace('        timeoutReferee();','        timeoutReferee();\n        midRaceReferee();')
    idx=s.index('    private static Direction rotate(')
    s=s[:idx]+'''    private static RaceGame midRace(final boolean pocket) throws Exception {
        final RaceGame g=straight(""); gates(g);
        g.lapGates[2]=new Line2D.Double(70,1,70,19);
        g.players=new Player[]{car(1,Player.INIT_POS,Player.INIT_POS,0,0),
                car(2,Player.INIT_POS,Player.INIT_POS,0,0),car(3,69,10,4,0),car(4,40,14,0,0)};
        g.players[0].setFinishedPlace(1); g.players[1].setFinishedPlace(4);
        g.researchClassification(1,1); g.subgamestate=2; g.setQueryTurnCounter(50);
        g.players[2].incrementLap(); g.players[2].setNextGate(2);
        if(pocket){
            g.startZoneA=new java.awt.geom.Area(new java.awt.geom.Rectangle2D.Double(0,0,10,5));
            g.players[2].setPosition(new int[]{5,2}); g.players[2].setVelocity(new int[]{0,-1});
            // This car returned to a cell in the grid/corridor overlap. Its earlier
            // departure still forbids entering the part outside the corridor.
            g.players[2].restoreLapState(new int[]{0,1,0,0,0,0,1});
        }
        return g;
    }

    private static void midRaceReferee() throws Exception {
        for(final boolean pocket:new boolean[]{false,true}){
            final RaceGame model=midRace(pocket), referee=midRace(pocket);
            final String before=RacecraftReplay.snapshot(model);
            final RacecraftReplay.Board root=RacecraftReplay.parse(model,before);
            final Direction action=pocket?Direction.N:Direction.E;
            final RacecraftReplay.Tail tail=RacecraftReplay.run(model,root,2,action,1,false);
            check(tail.complete() && tail.place()==(pocket?3:2),"mid-race tail lost prior classification");
            check(tail.outcome().status()==(pocket?RacecraftOutcome.Status.CRASHED:RacecraftOutcome.Status.FINISHED),
                    "grid entitlement or combined checkpoint/finish did not survive replay");
            check(before.equals(RacecraftReplay.snapshot(model)),"mid-race replay changed live state");
            referee.setAutoMode(true); referee.setAutoRaceEndHook(()->{});
            final Path log=Files.createTempFile("review-mid-race-", ".log"); referee.setGameLogPath(log.toString());
            set(referee,"gamestate",GameState.PLAY);
            final Player player=referee.players[2]; final int[] x=player.getPosition(),v=player.getVelocity();
            final int[] nv={v[0]+action.dx,v[1]+action.dy},nx={x[0]+nv[0],x[1]+nv[1]};
            final Method commit=RaceGame.class.getDeclaredMethod("commitMove",int[].class,int[].class,int[].class);
            commit.setAccessible(true);
            try{
                commit.invoke(referee,x,nv,nx);
                check(RacecraftReplay.snapshot(referee).equals(tail.finalState()),"mid-race tail differs from live referee");
            }finally{Files.deleteIfExists(log);}
        }
    }

'''+s[idx:]; p.write_text(s)
