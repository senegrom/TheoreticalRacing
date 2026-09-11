package tr.logic;

import com.sun.jdi.Bootstrap;
import com.sun.jdi.ObjectReference;
import com.sun.jdi.ThreadReference;
import com.sun.jdi.VirtualMachine;
import com.sun.jdi.connect.Connector;
import com.sun.jdi.connect.LaunchingConnector;
import com.sun.jdi.event.BreakpointEvent;
import com.sun.jdi.event.ClassPrepareEvent;
import com.sun.jdi.event.Event;
import com.sun.jdi.event.EventSet;
import com.sun.jdi.event.VMDeathEvent;
import com.sun.jdi.event.VMDisconnectEvent;
import com.sun.jdi.request.BreakpointRequest;
import com.sun.jdi.request.ClassPrepareRequest;
import com.sun.jdi.request.EventRequest;
import java.lang.reflect.Field;
import java.lang.reflect.Method;
import java.nio.charset.StandardCharsets;
import java.nio.file.Files;
import java.nio.file.Path;
import java.util.BitSet;
import java.util.List;
import java.util.Map;
import java.util.concurrent.TimeUnit;
import java.util.concurrent.atomic.AtomicReference;

/** Deterministic monitor-boundary regression using unmodified production methods. */
public final class LapMemoPublicationTests {
    private LapMemoPublicationTests() {}

    private static void check(final boolean condition, final String message) {
        if (!condition) throw new AssertionError(message);
    }

    public static void main(final String[] args) throws Exception {
        final List<String> source = Files.readAllLines(Path.of(args[0]));
        int line = 0;
        for (int i = 0; i < source.size(); i++)
            if (source.get(i).strip().equals("if (m == null || m.gateTurns == null) return false;")) line = i + 1;
        check(line != 0, "lap-adoption boundary missing");
        final Path directory = Files.createTempDirectory("lap-memo-publication-");
        final Path go = directory.resolve("publish");
        final LaunchingConnector connector = Bootstrap.virtualMachineManager().defaultConnector();
        final Map<String, Connector.Argument> options = connector.defaultArguments();
        options.get("main").setValue(Fixture.class.getName() + " \"" + go + "\"");
        options.get("options").setValue("-Djava.awt.headless=true -cp \"" + System.getProperty("java.class.path") + "\"");
        final VirtualMachine vm = connector.launch(options);
        final ClassPrepareRequest prepare = vm.eventRequestManager().createClassPrepareRequest();
        prepare.addClassFilter("tr.logic.Reachability");
        prepare.enable();
        boolean checked = false;
        try {
            final long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(20);
            while (!checked && System.nanoTime() < deadline) {
                final EventSet events = vm.eventQueue().remove(1000);
                if (events == null) continue;
                try {
                    for (final Event event : events) {
                        if (event instanceof ClassPrepareEvent ready) {
                            final BreakpointRequest bp = vm.eventRequestManager().createBreakpointRequest(
                                    ready.referenceType().locationsOfLine(line).get(0));
                            bp.setSuspendPolicy(EventRequest.SUSPEND_EVENT_THREAD);
                            bp.enable();
                            prepare.disable();
                        } else if (event instanceof BreakpointEvent bp) {
                            bp.request().disable();
                            final ObjectReference memo = (ObjectReference) bp.location().declaringType().getValue(
                                    bp.location().declaringType().fieldByName("REACH_MEMO"));
                            // Pre-fix code deterministically fails here: lookup released the
                            // monitor before the readiness check and bundle copy.
                            check(bp.thread().ownedMonitors().contains(memo),
                                    "lap reader released the publication monitor before checking/copying the bundle");
                            Files.writeString(go, "publish");
                            boolean blocked = false;
                            final long until = System.nanoTime() + TimeUnit.SECONDS.toNanos(5);
                            while (!blocked && System.nanoTime() < until) {
                                for (final ThreadReference thread : vm.allThreads())
                                    if (thread.name().equals("lap-memo-writer")
                                            && thread.status() == ThreadReference.THREAD_STATUS_MONITOR) blocked = true;
                                if (!blocked) Thread.sleep(5);
                            }
                            check(blocked, "publisher was not excluded while the reader held the bundle lock");
                            checked = true;
                        } else if (event instanceof VMDeathEvent || event instanceof VMDisconnectEvent) {
                            throw new AssertionError("fixture exited before the adoption boundary");
                        }
                    }
                } finally { events.resume(); }
            }
            check(checked, "lap publication schedule timed out");
            // Detach after the schedule so VM-death events cannot suspend process exit.
            vm.dispose();
            final Process process = vm.process();
            check(process.waitFor(10, TimeUnit.SECONDS), "fixture did not finish");
            System.out.print(new String(process.getInputStream().readAllBytes(), StandardCharsets.UTF_8));
            System.err.print(new String(process.getErrorStream().readAllBytes(), StandardCharsets.UTF_8));
            check(process.exitValue() == 0, "lap publication fixture failed");
            System.out.println("LapMemoPublicationTests: reader excludes concurrent publication; complete retry preserves all fields and queries OK");
        } finally {
            if (vm.process().isAlive()) {
                vm.process().destroyForcibly();
                vm.process().waitFor(5, TimeUnit.SECONDS);
            }
            Files.deleteIfExists(go);
            Files.deleteIfExists(directory);
        }
    }

    /** Synthetic complete base/lap maps avoid large allocations and timing-based stress. */
    public static final class Fixture {
        private Fixture() {}
        private static Object invoke(final Reachability reach, final String name) throws Exception {
            final Method method = Reachability.class.getDeclaredMethod(name, String.class);
            method.setAccessible(true);
            return method.invoke(reach, "lap-publication-test");
        }
        private static void fill(final Reachability reach) {
            reach.aliveW = reach.aliveH = reach.aliveSpan = 1;
            reach.turnsArr = new int[]{0};
            reach.aliveStates = new BitSet(1); reach.aliveStates.set(0);
            reach.roomy0 = new BitSet(1); reach.roomy1 = new BitSet(1);
            reach.minShed2 = new byte[]{0}; reach.minShed2Roomy = new byte[]{0}; reach.certSq = new byte[]{36};
        }
        public static void main(final String[] args) throws Exception {
            final Path go = Path.of(args[0]);
            Reachability.clearReachMemoForTests();
            final Reachability publisher = new Reachability(null);
            fill(publisher);
            invoke(publisher, "publishMemo");
            fill(publisher);
            publisher.gateTurns = new int[][]{{0}, {0}, {0}};
            publisher.robustReach = new BitSet[]{new BitSet(1), new BitSet(1), new BitSet(1)};
            final Field fallback = Reachability.class.getDeclaredField("robustSeedFallback");
            final Field phantom = Reachability.class.getDeclaredField("phantomAlive");
            fallback.setAccessible(true); phantom.setAccessible(true);
            fallback.setBoolean(publisher, true); phantom.setInt(publisher, 17);
            final Reachability reader = new Reachability(null);
            check(Boolean.TRUE.equals(invoke(reader, "adoptMemo")), "base memo missing");
            final AtomicReference<Throwable> failure = new AtomicReference<>();
            final Thread reading = new Thread(() -> {
                try { check(Boolean.FALSE.equals(invoke(reader, "adoptLapMemo")), "reader accepted unpublished lap maps"); }
                catch (final Throwable error) { failure.compareAndSet(null, error); }
            }, "lap-memo-reader");
            final Thread writing = new Thread(() -> {
                try {
                    final long deadline = System.nanoTime() + TimeUnit.SECONDS.toNanos(15);
                    while (!Files.exists(go)) {
                        check(System.nanoTime() < deadline, "publisher signal timed out");
                        Thread.sleep(5);
                    }
                    invoke(publisher, "publishLapMemo");
                } catch (final Throwable error) { failure.compareAndSet(null, error); }
            }, "lap-memo-writer");
            reading.start(); writing.start(); reading.join(); writing.join();
            if (failure.get() != null) throw new AssertionError("publication schedule failed", failure.get());
            check(Boolean.TRUE.equals(invoke(reader, "adoptLapMemo")), "complete lap memo missing");
            for (final String name : new String[]{"gateTurns", "robustReach", "aliveStates", "roomy0", "roomy1",
                    "minShed2", "minShed2Roomy", "certSq"}) {
                final Field field = Reachability.class.getDeclaredField(name);
                field.setAccessible(true);
                check(field.get(reader) == field.get(publisher), "partial lap field: " + name);
            }
            check(fallback.getBoolean(reader) && phantom.getInt(reader) == 17, "lap diagnostics lost");
            check(reader.certBudget(0, 0, 0, 0) == 6, "certified speed changed");
            check(reader.shedableLanding(0, 0, 0, 0), "shedable landing changed");
            final long before = Reachability.reachMemoBytesForTests();
            invoke(publisher, "publishLapMemo");
            check(before == Reachability.reachMemoBytesForTests(), "duplicate lap publication changed byte accounting");
            Reachability.clearReachMemoForTests();
        }
    }
}
