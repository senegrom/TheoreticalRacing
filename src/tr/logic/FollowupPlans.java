package tr.logic;

import java.util.Arrays;

/** A remembered action is only an additional candidate, never an instruction to
 * execute a stale plan. Memory changes on committed moves, not on queries. */
final class FollowupPlans {
    record Entry(java.util.List<Direction> actions, String expectedKey, boolean traffic, ResponseStrategies.Tree responses) {
        Entry {
            actions = java.util.List.copyOf(actions);
            if (actions.isEmpty() || actions.size() > (traffic ? 3 : 1) || expectedKey == null
                    || !expectedKey.matches("[0-9a-f]{64}")) throw new IllegalArgumentException("invalid follow-up");
        }
        Entry(final java.util.List<Direction> actions, final String expectedKey, final boolean traffic) { this(actions, expectedKey, traffic, null); }
        Entry(final Direction action, final String expectedKey) { this(java.util.List.of(action), expectedKey, false); }
        boolean response() { return responses != null; }
        static Entry response(final ResponseStrategies.Tree tree, final String key) {
            if (tree == null || tree.empty()) throw new IllegalArgumentException("empty response plan");
            return new Entry(java.util.List.of(Direction.NONE), key, false, tree);
        }
        Direction action() { return actions.get(0); }
        static Entry traffic(final java.util.List<Direction> actions, final String key) { return new Entry(actions,key,true); }
    }
    private final Entry[] entries = new Entry[9];
    Entry find(final RaceGame game) {
        final Entry entry = entries[game.subgamestate];
        return entry != null && (entry.response() ? entry.responses().at(key(game)) != null
                : entry.expectedKey().equals(key(game))) ? entry : null;
    }
    void put(final int slot, final Entry entry) { entries[slot] = entry; }
    FollowupPlans copy() {
        final FollowupPlans result = new FollowupPlans();
        System.arraycopy(entries,0,result.entries,0,entries.length); return result;
    }
    String encode(final int players) {
        boolean any = false;
        for (int i=0;i<players;i++) any |= entries[i]!=null;
        if (!any) return "-";
        final StringBuilder out = new StringBuilder();
        for (int i=0;i<players;i++) {
            if(i>0) out.append('.');
            final Entry e=entries[i];
            if(e==null) { out.append('-'); continue; }
            if(e.response()) { out.append("R_").append(e.responses().encode()).append('~').append(e.expectedKey()); continue; }
            if(e.traffic()) out.append("M_");
            out.append(String.join("+",e.actions().stream().map(Enum::name).toList())).append('~').append(e.expectedKey());
        }
        return out.toString();
    }
    static FollowupPlans parse(final String text, final int players) {
        final FollowupPlans result=new FollowupPlans();
        if(players<1||players>9) throw new IllegalArgumentException("follow-up roster mismatch");
        if(text.equals("-")) return result;
        final String[] parts=text.split("\\.",-1);
        if(parts.length!=players) throw new IllegalArgumentException("follow-up roster mismatch");
        for(int i=0;i<players;i++) {
            if(parts[i].equals("-")) continue;
            final String[] fields=parts[i].split("~",-1);
            if(fields.length!=2) throw new IllegalArgumentException("invalid follow-up encoding");
            if(fields[0].startsWith("R_")) { result.entries[i]=Entry.response(ResponseStrategies.Tree.parse(fields[0].substring(2)),fields[1]); continue; }
            final boolean traffic=fields[0].startsWith("M_");
            final String spec=traffic?fields[0].substring(2):fields[0];
            final java.util.List<Direction> actions=Arrays.stream(spec.split("\\+",-1)).map(Direction::valueOf).toList();
            result.entries[i]=new Entry(actions,fields[1],traffic);
        }
        return result;
    }

    static String key(final RaceGame game) { return key(RacecraftReplay.capture(game)); }
    static String key(final RacecraftReplay.Board board) {
        final int[][] rows = Arrays.stream(board.cars).map(int[]::clone).toArray(int[][]::new);
        // UI trail pruning is not a policy input. Everything else, including
        // exact grid departure, ranks, clock, roster order and rules, is bound.
        for (final int[] row : rows) Arrays.fill(row, 9, 13, 0);
        return RacecraftReplay.sha(new RacecraftReplay.Board(board.turn, board.laps, board.slot,
                board.first, board.last, board.identity, rows).encode());
    }

    /** The exact first-cycle actions of the chooser model, with a detached
     * classification ledger. No new opponent policy is introduced to guess the
     * expected board. A mismatch at the next real turn invalidates the proposal. */
    static final class Projection {
        private final RaceGame game;
        private final RacecraftReplay.Board origin;
        private final int[][] rows;
        private int first, last;
        Projection(final RaceGame game) {
            this.game = game; origin = RacecraftReplay.capture(game);
            rows = Arrays.stream(origin.cars).map(int[]::clone).toArray(int[][]::new);
            first = origin.first; last = origin.last;
        }
        void step(final int slot, final RaceGame.MoveResult move, final int x, final int y,
                final int vx, final int vy) {
            final int[] row = rows[slot];
            if (move != null) {
                if (move.passCp1()) row[8] = 2;
                if (move.passCp2()) row[8] = 0;
            }
            if (move == null || !move.legal() || move.finishes()) {
                row[6] = move != null && move.finishes() ? ++first : rows.length - last++;
                row[2] = row[3] = Player.INIT_POS; row[4] = row[5] = 0;
            } else {
                row[2] = x; row[3] = y; row[4] = vx; row[5] = vy;
                if (move.lapCross()) { row[7]++; row[8] = 1; }
                if (game.startZoneA != null && !game.startZoneA.contains(x, y)) row[13] = 1;
            }
        }
        String key(final int turn, final int slot) {
            int live = 0;
            for (final int[] row : rows) if (row[6] == 0) live++;
            if (rows[slot][6] != 0 || live < 2 && rows.length > 1) return null;
            return FollowupPlans.key(new RacecraftReplay.Board(turn, origin.laps, slot,
                    first, last, origin.identity, rows));
        }
    }
}
