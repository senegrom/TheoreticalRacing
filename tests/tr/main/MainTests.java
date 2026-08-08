package tr.main;

/** Dependency-free launcher argument regression tests. */
public final class MainTests {
	private MainTests() {}

	public static void main(final String[] args) {
		testValidOptions();
		testHeadlessModes();
		expectFailure(new String[]{"--track"}, "--track requires a value");
		expectFailure(new String[]{"--seed", "not-a-number"}, "--seed requires an integer");
		expectFailure(new String[]{"--query-moves", "in"}, "--query-moves requires a value");
		expectFailure(new String[]{"--unknown"}, "Unknown option");
		expectFailure(new String[]{"positional"}, "Unknown option");
		System.out.println("MainTests: OK");
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
