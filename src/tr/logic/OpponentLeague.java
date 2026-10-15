package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Offline cross-play endpoint. An actor sees the physical board, never its
 * opponents' profile identifiers or a candidate/champion label. Every mutable
 * strategy is evaluated by its OWN place/time; no coalition objective exists. */
@SuppressWarnings("try")
final class OpponentLeague {
    private OpponentLeague() {}
    record Profile(String name,int speed,int radius,int horizon) {
        static Profile parse(final String text) {
            if(text.equals("champion")||text.equals("scorer")||text.equals("pace")) return new Profile(text,0,0,0);
            final String[] f=text.split("_",-1);
            if(f.length!=4||!f[0].equals("g")) throw new IllegalArgumentException("unknown league profile");
            final int s=Integer.parseInt(f[1]),r=Integer.parseInt(f[2]),h=Integer.parseInt(f[3]);
            if(s<0||s>12||r<1||r>20||h<2||h>12||!text.equals("g_"+s+"_"+r+"_"+h))
                throw new IllegalArgumentException("league genome bounds");
            return new Profile(text,s,r,h);
        }
        Direction action(final RaceGame game,final RaceAi policy) {
            final Direction ordinary=policy.computeAiMove();
            final StrategyState root=StrategyState.capture(game);
            if(ordinary==null||name.equals("champion")||!LearningTactics.near(game)) return ordinary;
            final RaceGame.MoveResult immediate=root.evaluate(game,ordinary);
            if(immediate!=null&&immediate.finishes()) return ordinary;
            if(name.equals("scorer")) return policy.researchScorer();
            final List<Direction> legal=root.legal(game,true);
            Direction pace=null;int value=Integer.MAX_VALUE;
            for(final Direction d:legal) {
                final StrategyState next=root.after(game,d);
                final int distance=next==null?Integer.MAX_VALUE:next.distance(game,root.slot());
                if(distance<value) { value=distance;pace=d; }
            }
            if(pace==null) return ordinary;
            if(name.equals("pace")) return pace;
            final int[] me=root.board.cars[root.slot()];
            int nearest=Integer.MAX_VALUE;
            for(int i=0;i<root.board.cars.length;i++) if(i!=root.slot()&&root.place(i)==0) {
                final int[] r=root.board.cars[i];nearest=Math.min(nearest,Math.max(Math.abs(me[2]-r[2]),Math.abs(me[3]-r[3])));
            }
            if(Math.max(Math.abs(me[4]),Math.abs(me[5]))<speed||nearest>radius) return ordinary;
            final List<Direction> actions=new ArrayList<>();actions.add(ordinary);
            if(pace!=ordinary) actions.add(pace);
            for(final Direction d:legal) {
                if(actions.contains(d)) continue;
                final StrategyState next=root.after(game,d);
                if(next!=null&&next.distance(game,root.slot())<=value+1L) { actions.add(d);break; }
            }
            RacecraftOutcome best=null;Direction chosen=ordinary;
            for(final Direction d:actions) {
                final LearningForecast.Result prediction=LearningForecast.run(game,root.board,List.of(d),horizon,
                        CreativeForecast.target(root),new LearningForecast.Settings(0,0,0,false));
                if(best==null||LearningChooser.better(prediction.outcome(),best)) { best=prediction.outcome();chosen=d; }
            }
            return chosen;
        }
    }
    static String answer(final RaceGame game,final String request) {
        final int split=request.indexOf('|');
        if(split<0||request.length()>270000) throw new IllegalArgumentException("invalid league request");
        final String[] h=request.substring(0,split).split(",",-1);
        if(h.length!=3||!h[0].equals("league1")) throw new IllegalArgumentException("league header");
        final int bound=Integer.parseInt(h[1]);if(bound<1||bound>100000) throw new IllegalArgumentException("league work bound");
        final String[] names=h[2].split("/",-1);
        if(names.length!=game.players.length) throw new IllegalArgumentException("league roster");
        final Profile[] profiles=new Profile[names.length];
        for(int i=0;i<profiles.length;i++) profiles[i]=Profile.parse(names[i]);
        final RacecraftReplay.Board root=RacecraftReplay.parse(game,request.substring(split+1));
        final List<String> trace=new ArrayList<>();
        final int[] own=new int[names.length];
        final String[] statuses=new String[names.length];java.util.Arrays.fill(statuses,"RUNNING");
        Direction first=null;boolean firstLegal=false,complete;
        String finalState;int[] places;
        try(RacecraftReplay.Scope scope=new RacecraftReplay.Scope(game,root)) {
            for(final Player p:game.players) if(!p.isAi()) throw new IllegalArgumentException("league requires AI-only rosters");
            final RaceAi policy=new RaceAi(game);
            complete=RacecraftReplay.classifyLast(game);
            while(trace.size()<bound&&!complete) {
                final int slot=game.subgamestate;
                if(game.raceTurnLimitReached()) {
                    int live=0;for(final Player p:game.players) if(!p.isFinished()) live++;
                    if(live-1>bound-trace.size()) break;
                    final List<String> expired=RacecraftReplay.expire(game);
                    for(final String row:expired) { final int actor=Integer.parseInt(row.substring(0,row.indexOf(':')));own[actor]++;statuses[actor]="TIMED_OUT"; }
                    trace.addAll(expired);complete=true;break;
                }
                final Direction action=profiles[slot].action(game,policy);
                if(action==null) break;
                if(first==null) { first=action;firstLegal=RacecraftReplay.legalActions(game).contains(action); }
                own[slot]++;
                policy.commitResearchPlan(action);
                final String transition=RacecraftReplay.advance(game,action);trace.add(transition);
                if(game.players[slot].isFinished()) statuses[slot]=transition.contains(":FINISH:")?"FINISHED":"CRASHED";
                complete=RacecraftReplay.classifyLast(game);
                if(!complete) CreativeForecast.advanceSlot(game,slot);
            }
            places=new int[names.length];
            for(int i=0;i<places.length;i++) {
                places[i]=game.players[i].getFinishedPlace();
                if(places[i]!=0&&statuses[i].equals("RUNNING")) statuses[i]="CLASSIFIED";
            }
            finalState=RacecraftReplay.snapshot(game);
        }
        final StringBuilder out=new StringBuilder("{\"schema\":1,\"requestSha256\":\"").append(RacecraftReplay.sha(request))
                .append("\",\"maxMoves\":").append(bound).append(",\"profiles\":\"").append(h[2])
                .append("\",\"places\":").append(java.util.Arrays.toString(places)).append(",\"moves\":").append(java.util.Arrays.toString(own))
                .append(",\"trial\":{\"action\":\"").append(first==null?Direction.NONE:first).append("\",\"legal\":").append(firstLegal)
                .append(",\"complete\":").append(complete).append(",\"place\":").append(places[root.slot]).append(",\"ownMoves\":").append(own[root.slot])
                .append(",\"status\":\"").append(statuses[root.slot]).append("\",\"traceSha256\":\"").append(RacecraftReplay.sha(String.join("\n",trace)))
                .append("\",\"trace\":[");
        for(int i=0;i<trace.size();i++) { if(i>0) out.append(',');out.append('"').append(trace.get(i)).append('"'); }
        return out.append("],\"finalState\":\"").append(finalState).append("\"}}").toString();
    }
}
