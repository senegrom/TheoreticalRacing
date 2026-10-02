from pathlib import Path
import re, subprocess, runpy
MASTER = 'b54e9bb05f91c0011e8d5e82178d1d13f3c1b494'

def edit(path, old, new, count=1):
    p = Path(path); s = p.read_text()
    if s.count(old) != count: raise RuntimeError(f'{path}: expected {count} occurrences of {old[:100]!r}, got {s.count(old)}')
    p.write_text(s.replace(old,new))

p = Path('racing-memory.md')
s = p.read_text()
if '<<<<<<<' in s:
    s = re.sub(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>>[^\n]*\n', lambda m: m[2]+'\n'+m[1], s, flags=re.S)
    p.write_text(s); subprocess.run(['git','add',str(p)],check=True)
p = Path('src/tr/logic/RaceAi.java'); s = p.read_text()
if '<<<<<<<' in s:
    def resolve(m):
        ours, theirs = m[1], m[2]
        if 'lastResearchOutcome = workspace.researchOutcome' in ours:
            return theirs+ours[ours.index('            lastResearchOutcome'):]
        if 'workspace.researchOwnMoves++' in ours: return '                if (i == myIdx) workspace.researchOwnMoves++;\n'
        if 'Nonterminal crossings are ordinary candidates' in ours: return theirs
        raise RuntimeError('Unexpected AI conflict: '+m[0])
    s = re.sub(r'<<<<<<< HEAD\n(.*?)=======\n(.*?)>>>>>>>[^\n]*\n',resolve,s,flags=re.S)
    p.write_text(s); subprocess.run(['git','add',str(p)],check=True)

if 'private int timeoutVerdict(' not in s:
    # Common rule corrections do not depend on an experimental flag.
    s = s.replace('if (game.racecraftNext.driving(game, playerNum)\n                && !rivalWithinCheb', 'if (!rivalWithinCheb')
    s = s.replace('// Candidate experiments obey the literal solo rule even before a duel tactic.\n        // The equivalent master rule correction is independently queued as round 294.', '// The literal solo rule precedes tactics for control and candidate alike.')
    p.write_text(s)
    edit('src/tr/logic/RacecraftNext.java', ', START_TIES("start-ties")', '')
    edit('src/tr/logic/RacecraftNext.java', 'feature != Feature.OPENING || openingTrials > 0', 'feature != Feature.OPENING || openingTrials > 0 && opening(game, player)')
    Path('src/tr/logic/StartPlacement.java').write_text(subprocess.check_output(['git','show',MASTER+':src/tr/logic/StartPlacement.java'],text=True))
    p2 = Path('src/tr/logic/RacecraftReplay.java'); r=p2.read_text()
    r=re.sub(r'        Board withStart\(.*?\n        }\n', '', r, flags=re.S)
    a=r.index('    /** Only the final AI placer:'); b=r.index('    /** cf3,',a); r=r[:a]+r[b:]
    p2.write_text(r)
    p2=Path('tests/tr/logic/RacecraftNextTests.java'); t=p2.read_text()
    a=t.index('    private static void placement()'); b=t.index('    private static void replay()',a)
    t=t[:a]+'''    private static void placement() {
        final Properties p = new Properties(); p.setProperty("racecraftNext", "start-ties");
        boolean rejected = false;
        try { new RacecraftNext(p); } catch (final IllegalArgumentException expected) { rejected = true; }
        check(rejected, "owner-rejected starting replay was re-enabled");
    }

'''+t[b:]; p2.write_text(t)
    p2=Path('tests/racecraft_next_cli.py'); p2.write_text(p2.read_text().replace('crash-rank,rank-time,opening,start-ties','crash-rank,rank-time,opening'))
    # Shared pure timeout ranking, including cyclic ties and projected progress.
    g=Path('src/tr/logic/RaceGame.java'); text=g.read_text()
    text=text.replace('return lapGates != null && turnCounter > (long) totalLaps * 750 * players.length;', 'return RaceTimeout.reached(this, turnCounter);')
    old='''standing.add(new Standing(p, OptimalPotential.remainingEvents(p.getNextGate(), p.getLap(), totalLaps),
					turnsToGateOrUnknown(p), k));'''
    assert old in text
    text=text.replace(old,'''final RaceTimeout.Progress progress = RaceTimeout.progress(this, p, k);
            standing.add(new Standing(p, progress.owed(), progress.toGate(), progress.order()));''')
    text=text.replace('''java.util.Comparator
			.comparingInt(Standing::owed).thenComparingInt(Standing::toGate).thenComparingInt(Standing::order)''','''(a, b) -> new RaceTimeout.Progress(a.owed(), a.toGate(), a.order())
                    .compareTo(new RaceTimeout.Progress(b.owed(), b.toGate(), b.order()))''')
    a=text.index('\t/** Turns to the car\'s next gate on the reachability maps, or unknown. */'); b=text.index('\n\tprivate static Direction directionOf',a)
    text=text[:a]+text[b:]; g.write_text(text)
    d=Path('src/tr/logic/RaceAiDuelSearch.java'); text=d.read_text()
    text=text.replace('''if (timedOut(game, turn))
            return 1;''','''if (timedOut(game, turn))
            return timeoutWin(game, mine, rival, false) ? 1 : UNKNOWN;''')
    text=text.replace('''if (timedOut(game, turn))
            return UNKNOWN;''','''if (timedOut(game, turn))
            return timeoutWin(game, mine, rival, true) ? 1 : UNKNOWN;''')
    text=text.replace('return game.lapGates != null && turn > (long) game.totalLaps * 750 * game.players.length;', 'return RaceTimeout.reached(game, turn);')
    idx=text.index('    private static boolean inPlanningDomain')
    text=text[:idx]+'''    private static boolean timeoutWin(final RaceGame game, final State mine, final State rival,
            final boolean ourTurn) {
        return RaceTimeout.progress(game, mine.lap, mine.gate, mine.x, mine.y, mine.vx, mine.vy, ourTurn ? 0 : 1)
                .compareTo(RaceTimeout.progress(game, rival.lap, rival.gate, rival.x, rival.y,
                        rival.vx, rival.vy, ourTurn ? 1 : 0)) < 0;
    }

'''+text[idx:]; d.write_text(text)
    d=Path('src/tr/logic/RaceAiTactics.java'); text=d.read_text()
    text=text.replace('        int escapeX = 0, escapeY = 0, escapes = 0;', '''        // At the limit the rival is classified by progress, not forced to move.
        // The deeper solver evaluates the candidate's projected progress instead.
        if (RaceTimeout.reached(game, (long) game.turnCount() + 1)) return null;
        int escapeX = 0, escapeY = 0, escapes = 0;'''); d.write_text(text)
    p=Path('src/tr/logic/RaceAi.java'); s=p.read_text()
    s=s.replace('''recordResearch(workspace, RacecraftOutcome.Status.CRASHED, liveCount - 1, 0);
                return -1;
            }
			final RaceGame.MoveResult candidate''','''workspace.researchOwnMoves = 0;
                return timeoutVerdict(workspace, game.subgamestate, myIdx, 0, outFinalTier, outFieldCost);
            }
			final RaceGame.MoveResult candidate''')
    needle='''				usePlayerFrame(i);
                if (i == myIdx) workspace.researchOwnMoves++;'''
    assert needle in s
    s=s.replace(needle,'''                if (RaceTimeout.reached(game, workspace.turns)) {
                    if (!myFinished) return timeoutVerdict(workspace, i, myIdx, rivalsFinished,
                            outFinalTier, outFieldCost);
                    raceOver = true;
                    break;
                }
'''+needle)
    idx=s.index('\n\tprivate void updateRolloutFrame(')
    s=s[:idx]+'''
    /** No phantom movement: classify the projected board with the live referee's order. */
    private int timeoutVerdict(final RolloutWorkspace w, final int slot, final int self,
            final int finishers, final int[] tier, final long[] field) {
        final int[] order = RaceTimeout.order(game, slot, w.laps, w.gates, w.px, w.py, w.vx, w.vy, w.alive);
        int rank = -1;
        for (int k = 0; k < order.length; k++) if (order[k] == self) rank = k;
        if (rank < 0) throw new IllegalStateException("timeout mover not live");
        if (rank > 0 || game.players.length == 1) w.researchOwnMoves++;
        recordResearch(w, rank == 0 && game.players.length > 1 ? RacecraftOutcome.Status.CLASSIFIED
                : RacecraftOutcome.Status.TIMED_OUT, finishers + rank, 0);
        if (tier != null) tier[0] = 3;
        if (field != null) field[0] = 0;
        if (simDepth == placeKeyDepth) placeKey = (long) (finishers + rank) * PLACE_KEY_STRIDE + w.researchOwnMoves;
        return rankVerdict(finishers + rank, 0);
    }
'''+s[idx:]
    p.write_text(s)
    o=Path('src/tr/logic/RacecraftOutcome.java'); text=o.read_text().replace('CLASSIFIED, CRASHED','CLASSIFIED, TIMED_OUT, CRASHED').replace('status == Status.CLASSIFIED || crashed()', 'status == Status.CLASSIFIED || status == Status.TIMED_OUT || crashed()'); o.write_text(text)
    ledger=Path('racing-memory.md'); text=ledger.read_text(); split=text.index('\n')+1
    text=text[:split]+'''
## Peer branch review repairs (2026-10-02, not promoted)

Integrated master b54e9bb (rounds 291/296 and the current owner rules) into
work/racecraft-outcomes-opening-20260928. Review repairs share projected
progress classification at timeout, isolate experimental controls, remove the
owner-rejected start-ties replay, and harden opening/corpus validation.
The old round-298 screens are not evidence for these repaired variants.
No fleet or lone-candidate gain is claimed; completed validation is recorded
separately after execution. Master and the earlier PR are not modified.

'''+text[split:]; ledger.write_text(text)
# Further reviewed edits are separate idempotent stages.
for path in sorted(Path('.review-fixes').glob('stage*.py')): runpy.run_path(str(path))
# Print every remaining turn-limit consumer for the semantic review.
s=Path('src/tr/logic/RaceAi.java').read_text()
for m in re.finditer(r'750',s): print('TIMEOUT CONSUMER:',s[max(0,m.start()-500):m.end()+400])
subprocess.run(['git','add','src','tests','racing-memory.md'],check=True)
