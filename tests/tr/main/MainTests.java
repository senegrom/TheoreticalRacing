package tr.main;

/** Dependency-free launcher argument regression tests. */
public final class MainTests {
	private MainTests() {}

	public static void main(final String[] args) {
		testValidOptions();
		testSeedRanges();
		testHeadlessModes();
		expectFailure(new String[]{"--track"}, "--track requires a value");
		expectFailure(new String[]{"--seed", "not-a-number"}, "--seed requires an integer");
		expectFailure(new String[]{"--query-moves", "in"}, "--query-moves requires a value");
		expectFailure(new String[]{"--unknown"}, "Unknown option");
		expectFailure(new String[]{"positional"}, "Unknown option");
		System.out.println("MainTests: OK");
	}

	private static void testSeedRanges() {
		Main.Options options = Main.parseArgs(new String[]{
				"--auto", "--seed", "1-3"
		});
		check(Long.valueOf(1).equals(options.seed()), "range start lost");
		check(Long.valueOf(3).equals(options.seedEnd()), "range end lost");

		options = Main.parseArgs(new String[]{
				"--auto", "--seed", "1-3", "--seed", "5"
		});
		check(Long.valueOf(5).equals(options.seed()), "replacement seed lost");
		check(options.seedEnd() == null, "scalar seed retained stale range end");

		options = Main.parseArgs(new String[]{
				"--auto", "--seed", Long.MAX_VALUE + "-" + Long.MAX_VALUE
		});
		check(Long.valueOf(Long.MAX_VALUE).equals(options.seed()), "maximum range start lost");
		check(Long.valueOf(Long.MAX_VALUE).equals(options.seedEnd()), "maximum range end lost");

		expectFailure(new String[]{"--seed", "1-3"}, "range requires --auto");
		expectFailure(new String[]{"--auto", "--seed", "1-3", "--dump-reach", "r"},
				"cannot be combined");
		expectFailure(new String[]{"--auto", "--seed", "1-3", "--query-moves", "i", "o"},
				"cannot be combined");
	}

	private static void testValidOptions() {
		final Main.Options options = Main.parseArgs(new String[]{
				"--auto", "--track", "sprint", "--props", "p.properties",
				"--log", "race.log", "--seed", "42", "--dump-reach", "reach.bin",
				"--query-moves", "-", "-"
		});
		check(options.auto(), "auto flag lost");
		check("sprint".equals(options.trackName()), "track value lost");
		check("p.properties".equals(options.propsPath()), "props value lost");
		check("race.log".equals(options.logPath()), "log value lost");
		check(Long.valueOf(42).equals(options.seed()), "seed value lost");
		check("reach.bin".equals(options.dumpReach()), "dump path lost");
		check("-".equals(options.queryIn()) && "-".equals(options.queryOut()), "query paths lost");
	}

	private static void testHeadlessModes() {
		check(!Main.parseArgs(new String[0]).headless(), "plain GUI launch became headless");
		check(Main.parseArgs(new String[]{"--auto"}).headless(), "auto mode not headless");
		check(Main.parseArgs(new String[]{"--dump-reach", "r"}).headless(), "dump mode not headless");
		check(Main.parseArgs(new String[]{"--query-moves", "i", "o"}).headless(), "query mode not headless");
	}

	private static void expectFailure(final String[] args, final String expected) {
		try {
			Main.parseArgs(args);
			throw new AssertionError("invalid arguments were accepted");
		} catch (final IllegalArgumentException error) {
			check(error.getMessage().contains(expected), "wrong error: " + error.getMessage());
		}
	}

	private static void check(final boolean condition, final String message) {
		if (!condition)
			throw new AssertionError(message);
	}
}
