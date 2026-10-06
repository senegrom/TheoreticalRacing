from pathlib import Path
import subprocess
source=Path('.traffic-20261006/apply.py').read_text()
a=source.index("p=Path('tools/racecraft_corpus.py'); t=p.read_text();")
b=source.index('\n\n# Checkpoint',a)
source=source[:a]+'''p=Path('tools/racecraft_corpus.py'); t=p.read_text()
t=one(t, "h[0] == 'rc4'", "h[0] in ('rc4', 'rc5')")
p.write_text(t)
'''+source[b:]
exec(compile(source,'.traffic-20261006/apply.py','exec'))
p=Path('src/tr/logic/RaceAi.java')
t=p.read_text().replace('/** Compatibility test/query seam. Production supplies its round-292b pace nominee. */',
                       '// Compatibility test/query seam. Production supplies its round-292b pace nominee.')
p.write_text(t)
p=Path('tests/tr/logic/TrafficRacecraftTests.java'); t=p.read_text()
t=t.replace('g.players[1]=car(2,20,12,14,0);prepare(g);',
'''g.players[1]=car(2,20,12,14,0);
        g.players[2]=car(3,58,7,0,0); // keep this a traffic decision, inside the unchanged 20-cell rule
        prepare(g);''')
t=t.replace('        stagedOrdering(); denial(); shortTransitions(); endpoints(); checkpointSubset(); manoeuvres(); memory();',
'''        int failures = 0;
        for (final String test : new String[]{"stagedOrdering", "denial", "shortTransitions", "endpoints", "checkpointSubset", "manoeuvres", "memory"}) {
            try {
                TrafficRacecraftTests.class.getDeclaredMethod(test).invoke(null);
                System.out.println("Traffic witness " + test + ": OK");
            } catch (final java.lang.reflect.InvocationTargetException error) {
                failures++; error.getCause().printStackTrace();
            }
        }
        check(failures == 0, "traffic behavioural failures: " + failures);''')
p.write_text(t)
subprocess.run(['git','add','src/tr/logic/RaceAi.java',str(p)],check=True)
