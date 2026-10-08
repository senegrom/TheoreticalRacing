package tr.logic;

/** Immutable model-conditional forecast. Place is zero-based relative to
 * cars live at forecast entry. Unknown is never a predicted crash. */
record RacecraftOutcome(Status status, int ahead, int ownMoves, int remaining) {
    enum Status { UNKNOWN, RUNNING, FINISHED, CLASSIFIED, TIMED_OUT, CRASHED }

    RacecraftOutcome {
        if (status == null || ahead < 0 || ownMoves < 0 || remaining < 0)
            throw new IllegalArgumentException("invalid forecast outcome");
        if (status != Status.RUNNING && status != Status.UNKNOWN && remaining != 0)
            throw new IllegalArgumentException("resolved result has remaining moves");
    }

    static RacecraftOutcome unknown() {
        return new RacecraftOutcome(Status.UNKNOWN, 0, 0, Integer.MAX_VALUE);
    }
    boolean known() { return status != Status.UNKNOWN && remaining != Integer.MAX_VALUE; }
    boolean crashed() { return status == Status.CRASHED; }
    boolean resolved() {
        return status == Status.FINISHED || status == Status.CLASSIFIED || status == Status.TIMED_OUT || crashed();
    }
    boolean successful() { return resolved() && !crashed(); }
    long time() { return (long) ownMoves + remaining; }

    int liveVerdict() {
        if (crashed()) return -1;
        return numericKey();
    }
    int numericKey() {
        if (!known()) return Integer.MAX_VALUE;
        final long key = (long) ahead * RaceAi.VERDICT_PLACE_STRIDE
                + Math.min(time(), RaceAi.VERDICT_PLACE_STRIDE - 1L);
        return (int) Math.min(key, Integer.MAX_VALUE);
    }

    /** Survival preference is retained. Crash ranking only refines an
     * all-known-crashes comparison, not an uncertain survival forecast. */
    boolean betterThan(final RacecraftOutcome other, final boolean compareCrashes) {
        if (!known()) return false;
        if (other == null || !other.known()) return !crashed();
        if (crashed() != other.crashed()) return !crashed();
        if (crashed() && !compareCrashes) return false;
        return ahead < other.ahead || ahead == other.ahead && time() < other.time();
    }

    static int retirementAhead(final int liveCount, final int finishedInForecast) {
        if (liveCount < 1 || finishedInForecast < 0)
            throw new IllegalArgumentException("invalid retirement ledger");
        return liveCount + finishedInForecast - 1;
    }
}
