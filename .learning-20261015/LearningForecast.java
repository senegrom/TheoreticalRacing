package tr.logic;

import java.util.ArrayList;
import java.util.HashSet;
import java.util.List;
import java.util.Set;

/** Detached, decision-aligned aware forecast. Refinement replaces specified cheap
 * decisions, never selects a convenient rival response. Every rerun starts from
 * the same root and recomputes all intervening decisions. This is not a proof. */
@SuppressWarnings("try")
final class LearningForecast {
    private LearningForecast() {}
    record Settings(int repairs, int rewind, int eventUpgrades, boolean memory) {
        Settings { if(repairs<0||repairs>6||rewind<0||rewind>2||eventUpgrades<0||eventUpgrades>4)
            throw new IllegalArgumentException("learning forecast budget"); }
    }
    record Decision(String key, int slot, boolean cheap) {}
    record Failure(int slot, List<Decision> history) { Failure { history=List.copyOf(history); } }
    record Result(RacecraftOutcome outcome, List<Direction> prefix, String nextKey,
            int fullCalls, int repairs, int eventCalls, int memories, Failure failure) {
        Result { prefix=List.copyOf(prefix); }
    }
    interface Policy {
        Direction select(RaceGame game, boolean strong);
    }
    static Result run(final RaceGame game, final RacecraftReplay.Board root,
            final List<Direction> prefix, final int horizon, final int target, final Settings settings) {
        final RaceAi policy=new RaceAi(game);
        return run(game,root,prefix,horizon,target,settings,(g,strong)->strong?policy.researchFullFirst():policy.researchScorer());
    }
    static Result run(final RaceGame game, final RacecraftReplay.Board root,
            final List<Direction> prefix, final int horizon, final int target, final Settings settings, final Policy policy) {
        if(prefix.isEmpty()||prefix.size()>4||horizon<prefix.size()||horizon>24||target==root.slot
                ||target < -1||target>=root.cars.length) throw new IllegalArgumentException("invalid learning forecast");
        final Set<String> upgrades=new HashSet<>();
        int full=0, events=0, memories=0;
        for(int attempt=0;;attempt++) {
            final Result result=once(game,root,prefix,horizon,target,settings,upgrades,policy);
            full+=result.fullCalls(); events+=result.eventCalls();memories+=result.memories();
            final String next=attempt<settings.repairs()?refine(result.failure(),upgrades,settings.rewind()):null;
            if(next==null) return new Result(result.outcome(),result.prefix(),result.nextKey(),full,attempt,events,memories,result.failure());
            upgrades.add(next);
        }
    }
    /** The failure move, then up to two previous cheap decisions of THAT car.
     * Previously upgraded boards remain upgraded on reruns. */
    static String refine(final Failure failure, final Set<String> upgraded, final int rewind) {
        if(failure==null) return null;
        int preceding=0;
        final List<Decision> history=failure.history();
        for(int i=history.size()-1;i>=0;i--) {
            final Decision decision=history.get(i);
            if(decision.slot()!=failure.slot()) continue;
            if(preceding++>rewind) break;
            if(decision.cheap()&&!upgraded.contains(decision.key())) return decision.key();
        }
        return null;
    }
    /** Cheap choice trigger: multiple physical actions but only one mapped
     * minimum-time action, or a minimum-time landing contests a rival's next
     * acceleration band. Forced moves do not consume an extra upgrade. */
    static boolean commitment(final RaceGame game, final StrategyState state) {
        final List<Direction> legal=state.legal(game,true);
        if(legal.size()<2) return false;
        int best=Integer.MAX_VALUE,count=0;
        boolean contested=false;
        final int[] me=state.board.cars[state.slot()];
        for(final Direction action:legal) {
            final StrategyState child=state.after(game,action);
            if(child==null) continue;
            final int distance=child.distance(game,state.slot());
            if(distance<best) { best=distance;count=1; } else if(distance==best) count++;
            final int x=me[2]+me[4]+action.dx,y=me[3]+me[5]+action.dy;
            for(int i=0;i<state.board.cars.length;i++) if(i!=state.slot()&&state.place(i)==0) {
                final int[] r=state.board.cars[i];
                if(Math.abs((long)x-r[2]-r[4])<=1 && Math.abs((long)y-r[3]-r[5])<=1) contested=true;
            }
        }
        return best!=Integer.MAX_VALUE&&(count==1||contested);
    }
    private static Result once(final RaceGame game,final RacecraftReplay.Board root,final List<Direction> prefix,
            final int horizon,final int target,final Settings settings,final Set<String> upgrades,final Policy policy) {
        final List<Direction> ownPrefix=new ArrayList<>();
        final List<Decision> history=new ArrayList<>();
        int own=0,full=0,eventCalls=0,memories=0;
        String nextKey=null;
        Failure failure=null;
        boolean selfUsed=false,targetUsed=false,stopped=false;
        List<Direction> remembered=List.of();int memoryIndex=0;
        RacecraftOutcome.Status status=RacecraftOutcome.Status.RUNNING;
        try(RacecraftReplay.Scope scope=new RacecraftReplay.Scope(game,root)) {
            for(final Player player:game.players) if(!player.isAi())
                return unknown(ownPrefix,nextKey,full,eventCalls,memories,failure);
            boolean complete=RacecraftReplay.classifyLast(game);
            for(int event=0;event<(horizon+1)*root.cars.length&&!complete;event++) {
                final int slot=game.subgamestate;
                if(game.raceTurnLimitReached()) {
                    final List<String> expired=RacecraftReplay.expire(game);
                    boolean retired=false;
                    for(final String row:expired) if(row.startsWith(root.slot+":")) { own++;retired=true; }
                    status=retired?RacecraftOutcome.Status.TIMED_OUT:RacecraftOutcome.Status.CLASSIFIED;
                    complete=true;break;
                }
                if(slot==root.slot) {
                    if(own==1) nextKey=FollowupPlans.key(game);
                    if(own==horizon) { stopped=true;break; }
                }
                final boolean forced=slot==root.slot&&own<prefix.size();
                final StrategyState board=StrategyState.capture(game);
                final String key=board.key();
                boolean fromMemory=false;
                if(!forced&&slot==root.slot&&settings.memory()) {
                    if(memoryIndex>=remembered.size()) {
                        final List<LearningMemory.Segment> matches=game.learningMemory.remembered(slot,LearningMemory.Pose.of(game.players[slot]));
                        remembered=matches.isEmpty()?List.of():matches.get(0).actions();memoryIndex=0;
                        if(!remembered.isEmpty()) memories++;
                    }
                    fromMemory=memoryIndex<remembered.size();
                }
                final boolean initial=!forced&&!fromMemory&&(slot==root.slot&&!selfUsed||slot==target&&!targetUsed);
                final boolean extra=!forced&&!fromMemory&&!initial&&slot==root.slot
                        &&eventCalls<settings.eventUpgrades()&&commitment(game,board);
                final boolean strong=!forced&&!fromMemory&&(initial||extra||upgrades.contains(key));
                final Direction action=forced?prefix.get(own):fromMemory?remembered.get(memoryIndex++):policy.select(game,strong);
                if(strong) full++;
                if(extra) eventCalls++;
                if(!forced&&slot==root.slot) selfUsed=true;
                if(slot==target) targetUsed=true;
                // History remembers policy eligibility, not whether a previous
                // pass happened to upgrade that decision.
                history.add(new Decision(key,slot,!forced&&!fromMemory&&!initial&&!extra));
                if(action==null) return unknown(ownPrefix,nextKey,full,eventCalls,memories,failure);
                if((forced||fromMemory)&&!board.legal(game,true).contains(action))
                    return unknown(ownPrefix,nextKey,full,eventCalls,memories,failure);
                final RaceGame.MoveResult move=board.evaluate(game,action);
                if(move==null) return unknown(ownPrefix,nextKey,full,eventCalls,memories,failure);
                if(!move.legal()&&failure==null&&!forced&&!fromMemory) failure=new Failure(slot,history);
                if(slot==root.slot) { if(ownPrefix.size()<4) ownPrefix.add(action);own++; }
                final String transition=RacecraftReplay.advance(game,action);
                if(slot==root.slot&&game.players[root.slot].isFinished())
                    status=transition.contains(":FINISH:")?RacecraftOutcome.Status.FINISHED:RacecraftOutcome.Status.CRASHED;
                complete=RacecraftReplay.classifyLast(game);
                if(game.players[root.slot].isFinished()) {
                    if(status==RacecraftOutcome.Status.RUNNING) status=RacecraftOutcome.Status.CLASSIFIED;
                    stopped=true;break;
                }
                if(!complete) CreativeForecast.advanceSlot(game,slot);
            }
            if(!complete&&!stopped) return unknown(ownPrefix,nextKey,full,eventCalls,memories,failure);
            final StrategyState end=StrategyState.capture(game);
            final int place=end.place(root.slot);
            return new Result(new RacecraftOutcome(status,place==0?game.researchFinishedFirst():place-1,own,end.distance(game,root.slot)),
                    ownPrefix,nextKey,full,0,eventCalls,memories,failure);
        }
    }
    private static Result unknown(final List<Direction> prefix,final String key,final int full,
            final int events,final int memories,final Failure failure) {
        return new Result(RacecraftOutcome.unknown(),prefix,key,full,0,events,memories,failure);
    }
}
