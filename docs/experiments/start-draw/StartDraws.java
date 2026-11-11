import java.io.*;
import java.nio.file.*;
import java.util.*;

/** Round 345's start-draw battery: the random-start (legacy) draw before round 345 ("master") and candidate
 *  fixes, as pure index sequences. RaceGame.findStartPosition gives the AI car in roster slot k (k = 1..n) an
 *  index in its free list: the zone's cells in x-then-y order minus the cells of cars 1..k-1 (isCrashingPlayer
 *  is exact occupancy). Before round 345 the index was startRng.nextInt(Z - k + 1), one new Random(seed) read
 *  car by car; since round 345 it is "percar". So a field's grid is a pure function of (zone cell list, seed,
 *  n), and car k's index of (seed, Z) alone.
 *
 *  java StartDraws.java dump <out> <seedLo> <seedHi> <Z,...> [variant,...]      raw indices per variant, Z, seed (8 cars)
 *  java StartDraws.java stats <out> <seedLo> <seedHi> <Z,...> [variant,...]     chi-square statistics per variant, Z
 */
public class StartDraws {
    static final int CARS = 8;
    static final String[] VARIANTS = {"master", "discard1", "splittable", "mixseed", "percar"};

    /** StartPlacement.draw (round 344), which random starts take since round 345: the number-th output of
     *  SplitMix64(seed), reduced unsigned to the pool. */
    static int draw(final long seed, final int number, final int size) {
        long z = seed + number * 0x9E3779B97F4A7C15L;
        z = (z ^ (z >>> 30)) * 0xBF58476D1CE4E5B9L;
        z = (z ^ (z >>> 27)) * 0x94D049BB133111EBL;
        return (int) Long.remainderUnsigned(z ^ (z >>> 31), size);
    }

    static void indices(final String variant, final long seed, final int z, final int[] out) {
        switch (variant) {
            case "master": {               // master: new Random(seed), one nextInt per car
                final Random r = new Random(seed);
                for (int k = 0; k < CARS; k++) out[k] = r.nextInt(z - k);
                break;
            }
            case "discard1": {             // negative control: master with its first output thrown away
                final Random r = new Random(seed);
                r.nextInt();
                for (int k = 0; k < CARS; k++) out[k] = r.nextInt(z - k);
                break;
            }
            case "splittable": {           // the stream replaced: new SplittableRandom(seed)
                final SplittableRandom r = new SplittableRandom(seed);
                for (int k = 0; k < CARS; k++) out[k] = r.nextInt(z - k);
                break;
            }
            case "mixseed": {              // java.util.Random kept, its seed mixed by SplitMix64 first
                final Random r = new Random(new SplittableRandom(seed).nextLong());
                for (int k = 0; k < CARS; k++) out[k] = r.nextInt(z - k);
                break;
            }
            case "percar": {               // arm 368's pure draw per car, reduced to the free list
                for (int k = 0; k < CARS; k++) out[k] = draw(seed, k + 1, z - k);
                break;
            }
            default: throw new IllegalArgumentException(variant);
        }
    }

    public static void main(final String[] args) throws IOException {
        final String mode = args[0];
        final Path out = Paths.get(args[1]);
        final long lo = Long.parseLong(args[2]), hi = Long.parseLong(args[3]);
        final int[] zs = Arrays.stream(args[4].split(",")).mapToInt(Integer::parseInt).toArray();
        final String[] variants = args.length > 5 ? args[5].split(",") : VARIANTS;
        try (PrintWriter w = new PrintWriter(Files.newBufferedWriter(out))) {
            final int[] idx = new int[CARS];
            if (mode.equals("dump")) {
                for (final String v : variants) for (final int z : zs) for (long s = lo; s <= hi; s++) {
                    indices(v, s, z, idx);
                    final StringBuilder b = new StringBuilder().append(v).append(' ').append(z).append(' ').append(s);
                    for (final int i : idx) b.append(' ').append(i);
                    w.println(b);
                }
                return;
            }
            // stats: per variant and Z, over seeds lo..hi:
            //  car k's index against uniform on Z-k+1 (Pearson chi-square, df Z-k);
            //  the joint (car 1, car 2) index table against independence (df (Z-1)(Z-2));
            //  every other pair of cars a < b: their index table against independence (df (Z-a)(Z-b));
            //  car 1's lag-one difference idx(s+1)-idx(s) mod Z against uniform (df Z-1);
            //  the share of seeds whose car 1 index equals the previous seed's (fair 1/Z).
            w.println("variant Z test df stat n");
            for (final String v : variants) for (final int z : zs) {
                final long[][] marg = new long[CARS][z];
                final long[][] joint = new long[z][z - 1];
                final long[][][][] pair = new long[CARS][CARS][][];
                for (int i = 0; i < CARS; i++) for (int j = i + 1; j < CARS; j++) pair[i][j] = new long[z - i][z - j];
                final long[] lag = new long[z];
                long same = 0, n = 0;
                int prev = -1;
                for (long s = lo; s <= hi; s++) {
                    indices(v, s, z, idx);
                    for (int k = 0; k < CARS; k++) marg[k][idx[k]]++;
                    for (int i = 0; i < CARS; i++) for (int j = i + 1; j < CARS; j++) pair[i][j][idx[i]][idx[j]]++;
                    joint[idx[0]][idx[1]]++;
                    if (prev >= 0) {
                        lag[Math.floorMod(idx[0] - prev, z)]++;
                        if (idx[0] == prev) same++;
                    }
                    prev = idx[0];
                    n++;
                }
                for (int k = 0; k < CARS; k++) {
                    final int m = z - k;
                    final double e = (double) n / m;
                    double x = 0;
                    for (int i = 0; i < m; i++) x += (marg[k][i] - e) * (marg[k][i] - e) / e;
                    w.printf(Locale.ROOT, "%s %d car%d %d %.4f %d%n", v, z, k + 1, m - 1, x, n);
                }
                double x = 0;
                for (int i = 0; i < z; i++) for (int j = 0; j < z - 1; j++) {
                    final double e = (double) marg[0][i] * marg[1][j] / n;
                    if (e > 0) x += (joint[i][j] - e) * (joint[i][j] - e) / e;
                }
                w.printf(Locale.ROOT, "%s %d joint12 %d %.4f %d%n", v, z, (z - 1) * (z - 2), x, n);
                for (int a = 0; a < CARS; a++) for (int b = a + 1; b < CARS; b++) {
                    if (a == 0 && b == 1) continue;
                    double xp = 0;
                    for (int i = 0; i < z - a; i++) for (int j = 0; j < z - b; j++) {
                        final double ep = (double) marg[a][i] * marg[b][j] / n;
                        if (ep > 0) xp += (pair[a][b][i][j] - ep) * (pair[a][b][i][j] - ep) / ep;
                    }
                    w.printf(Locale.ROOT, "%s %d pair%d%d %d %.4f %d%n", v, z, a + 1, b + 1, (z - a - 1) * (z - b - 1), xp, n);
                }
                final double e = (double) (n - 1) / z;
                double xl = 0;
                for (int i = 0; i < z; i++) xl += (lag[i] - e) * (lag[i] - e) / e;
                w.printf(Locale.ROOT, "%s %d lag1 %d %.4f %d%n", v, z, z - 1, xl, n - 1);
                w.printf(Locale.ROOT, "%s %d repeat1 0 %.6f %d%n", v, z, (double) same / (n - 1), n - 1);
            }
        }
    }
}
