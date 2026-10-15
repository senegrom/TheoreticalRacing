package tr.logic;

import java.util.ArrayList;
import java.util.LinkedHashSet;
import java.util.List;
import java.util.Set;
import java.util.function.ToIntFunction;

/** Common detached comparison for the new arms. learning-control exposes the
 * identical comparison without repair, memories, extra upgrades or proposals,
 * so experimental effects can be separated from the model integration itself. */
final class LearningChooser {
    private LearningChooser() {}
    record Choice(Direction action,FollowupPlans.Entry tail,boolean accepted,boolean paceTied,
            int forecasts,int fullCalls,int repairs,int events,int memories,int proposals) {}
    static boolean better(final RacecraftOutcome a,final RacecraftOutcome b) {
        return a!=null&&a.known()&&(b==null||!b.known()||a.ahead()<b.ahead()
                ||a.ahead()==b.ahead()&&a.time()<b.time());
    }
    static boolean tied(final RacecraftOutcome a,final RacecraftOutcome b) {
        return a!=null&&b!=null&&a.known()&&b.known()&&a.ahead()==b.ahead()&&a.time()==b.time();
    }
    static Choice choose(final RaceGame game,final Direction incumbent,final List<Direction> candidates,
            final Direction pace,final FollowupPlans.Entry inherited,final ToIntFunction<Direction> relevant) {
        final RacecraftNext config=game.racecraftNext;
        final int player=game.players[game.subgamestate].getNumber();
        if(incumbent==null||!config.learningEnabled(game,player))
            return new Choice(incumbent,null,false,false,0,0,0,0,0,0);
        final RacecraftReplay.Board root=RacecraftReplay.capture(game);
        final Set<List<Direction>> paths=new LinkedHashSet<>();
        paths.add(List.of(incumbent));
        for(final Direction action:candidates) paths.add(List.of(action));
        final boolean memory=config.enabled(game,player,RacecraftNext.Feature.CORNER_MEMORY);
        if(inherited!=null&&inherited.traffic()) paths.add(inherited.actions());
        if(memory) for(final LearningMemory.Segment segment:game.learningMemory.remembered(root.slot,LearningMemory.Pose.of(root.cars[root.slot])))
            paths.add(segment.actions());
        int proposals=0;
        if(config.enabled(game,player,RacecraftNext.Feature.TIME_INVESTMENT))
            for(final List<Direction> path:TimeInvestment.propose(game,new StrategyState(root),incumbent,config.learningNodes))
                if(paths.add(path)) proposals++;
        final int repairs=config.enabled(game,player,RacecraftNext.Feature.FORECAST_REPAIR)?config.repairAttempts:0;
        final int events=config.enabled(game,player,RacecraftNext.Feature.EVENT_AWARE)?config.eventUpgrades:0;
        LearningForecast.Result best=null;
        List<Direction> chosen=List.of(incumbent);
        RacecraftOutcome paceOutcome=null;
        boolean explicit=false;
        int calls=0,full=0,refined=0,upgrades=0,memories=0;
        for(final List<Direction> path:paths) {
            // The trial budget admits a path only when BOTH own-continuation
            // profiles can receive the same comparison, when memory is enabled.
            final int profiles=memory?2:1;
            if(calls+profiles>config.learningTrials) break;
            for(int profile=0;profile<profiles;profile++) {
                final LearningForecast.Settings settings=new LearningForecast.Settings(repairs,config.repairRewind,events,profile==1);
                final LearningForecast.Result result=LearningForecast.run(game,root,path,12,relevant.applyAsInt(path.get(0)),settings);
                calls++;full+=result.fullCalls();refined+=result.repairs();upgrades+=result.eventCalls();memories+=result.memories();
                if(path.size()==1&&path.get(0)==pace && (paceOutcome==null||better(result.outcome(),paceOutcome))) paceOutcome=result.outcome();
                if(best==null||better(result.outcome(),best.outcome())) {
                    best=result;chosen=path;explicit=path.size()>1||profile==1&&result.memories()>0;
                }
            }
        }
        if(best==null||!best.outcome().known()) return new Choice(incumbent,null,false,false,calls,full,refined,upgrades,memories,proposals);
        final Direction action=chosen.get(0);
        final FollowupPlans.Entry tail=!explicit||best.nextKey()==null||best.prefix().size()<2?null
                :FollowupPlans.Entry.traffic(best.prefix().subList(1,best.prefix().size()),best.nextKey());
        return new Choice(action,tail,action!=incumbent||tail!=null,tied(paceOutcome,best.outcome()),calls,full,refined,upgrades,memories,proposals);
    }
}
