package tr.logic;

import java.util.ArrayList;
import java.util.List;

/** Spend at most one mapped solo move on an explicitly contested two-car
 * endgame. Map costs nominate attacks; they are not physical deadline proofs. */
final class TimeInvestment {
    private TimeInvestment() {}
    static List<List<Direction>> propose(final RaceGame game,final StrategyState root,
            final Direction incumbent,final int limit) {
        if(limit<=0||root.live()!=2) return List.of();
        final int self=root.slot(), rival=CreativeForecast.target(root);
        final int mine=root.distance(game,self), theirs=root.distance(game,rival);
        if(mine==Integer.MAX_VALUE||theirs==Integer.MAX_VALUE||mine>14||theirs>14) return List.of();
        final List<List<Direction>> result=new ArrayList<>();
        final StrategyState baseline=root.after(game,incumbent);
        if(baseline==null||baseline.live()!=2) return List.of();
        final int rivalBase=cheapestReply(game,baseline);
        final StrategyState.Budget budget=new StrategyState.Budget(limit);
        for(final Direction action:root.legal(game,true)) {
            if(!budget.take()) return List.copyOf(result);
            if(action==incumbent) continue;
            final StrategyState next=root.after(game,action);
            if(next==null||next.live()!=2) continue;
            final int distance=next.distance(game,self), rivalCost=cheapestReply(game,next);
            if(distance!=Integer.MAX_VALUE&&(long)distance+1<=mine+1L
                    &&rivalBase!=Integer.MAX_VALUE&&rivalCost>rivalBase) result.add(List.of(action));
            if(result.size()==2) return List.copyOf(result);
        }
        final List<AmbushPlans.Target> targets=AmbushPlans.mandatory(game,CreativePaths.Own.of(root.board.cars[rival]),3,budget);
        for(final AmbushPlans.Target target:targets) {
            for(final List<Direction> path:AmbushPlans.intercept(game,CreativePaths.Own.of(root.board.cars[self]),target,budget,1))
                if(!result.contains(path)) { result.add(path);if(result.size()==2) return List.copyOf(result); }
            if(budget.left()==0) break;
        }
        return List.copyOf(result);
    }
    private static int cheapestReply(final RaceGame game,final StrategyState state) {
        int best=Integer.MAX_VALUE;
        for(final Direction action:state.legal(game,true)) {
            final StrategyState next=state.after(game,action);
            if(next!=null) best=Math.min(best,next.distance(game,state.slot()));
        }
        return best;
    }
}
