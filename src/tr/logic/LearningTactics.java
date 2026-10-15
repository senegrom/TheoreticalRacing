package tr.logic;

/** Shared activation rules; no changes to computed starts or the literal
 * twenty-cell solo boundary. League profiles use the same geometric boundary. */
final class LearningTactics {
    private LearningTactics() {}
    static boolean near(final RaceGame game) {
        final Player me=game.players[game.subgamestate];
        final int[] x=me.getPosition();
        if(me.isFinished()) return false;
        for(final Player rival:game.players) if(rival!=me&&!rival.isFinished()) {
            final int[] p=rival.getPosition();
            if(Math.abs((long)x[0]-p[0])<=20&&Math.abs((long)x[1]-p[1])<=20) return true;
        }
        return false;
    }
    static ProofNumberSearch.Result proof(final RaceGame game) {
        final RacecraftNext config=game.racecraftNext;
        final int player=game.players[game.subgamestate].getNumber();
        if(!near(game)||!config.enabled(game,player,RacecraftNext.Feature.PROOF_NUMBER))
            return new ProofNumberSearch.Result(null,null,0,false,0);
        final StrategyState root=StrategyState.capture(game);
        final ProofNumberSearch.Plan retained=game.learningMemory.proof(root.slot());
        if(retained!=null&&root.live()==2) {
            final ProofNumberSearch.Answer answer=retained.at(root);
            if(answer!=null&&root.legal(game,true).contains(answer.action()))
                return new ProofNumberSearch.Result(retained,answer.action(),0,false,answer.left());
        }
        return ProofNumberSearch.iterative(game,root,5,config.proofMoves,config.learningNodes);
    }
}
