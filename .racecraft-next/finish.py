from pathlib import Path

p = Path('src/tr/logic/RacecraftNext.java')
s = p.read_text()
s = s.replace('    boolean any(final RaceGame game, final int player) {', '''    String signature() { return features.toString() + ":" + openingRounds + ":" + openingTrials; }

    boolean any(final RaceGame game, final int player) {''')
p.write_text(s)
p = Path('src/tr/logic/RacecraftReplay.java')
s = p.read_text().replace('final class RacecraftReplay {', '@SuppressWarnings("try")\nfinal class RacecraftReplay {')
s = s.replace('if (game.startZoneA != null) for (final PathIterator it = game.startZoneA.getPathIterator(null);', '''for (final java.awt.geom.Area area : new java.awt.geom.Area[]{game.trackA, game.startZoneA})
            if (area != null) for (final PathIterator it = area.getPathIterator(null);''')
s = s.replace('if (maxMoves < 1 || self < 0 || self >= root.cars.length)', 'if (maxMoves < 1 || root.turn > Integer.MAX_VALUE - maxMoves || self < 0 || self >= root.cars.length)')
s = s.replace('RacecraftOutcome.Status focalStatus = RacecraftOutcome.Status.RUNNING;', '''RacecraftOutcome.Status focalStatus = complete ? RacecraftOutcome.Status.CLASSIFIED
                    : RacecraftOutcome.Status.RUNNING;''')
s = s.replace('            survivor.setFinishedPlace(first);\n            game.researchClassification(first, game.researchFinishedLast());', '''            survivor.setFinishedPlace(first);
            // checkFinished assigns this place without incrementing finishedFirst.''')
p.write_text(s)
p = Path('src/tr/logic/RaceAi.java')
s = p.read_text()
s = s.replace('    private RacecraftOutcome lastResearchOutcome;', '    private RacecraftOutcome lastResearchOutcome;\n    private boolean lastResearchRankTime;\n    private int researchOpeningTrials;')
s = s.replace('return lastResearchOutcome == null ? legacy >= 0 && legacy % VERDICT_PLACE_STRIDE == 0', 'return !lastResearchRankTime || lastResearchOutcome == null ? legacy >= 0 && legacy % VERDICT_PLACE_STRIDE == 0')
s = s.replace('            lastResearchOutcome = workspace.researchOutcome;\n            return nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME) && lastResearchOutcome != null', '''            lastResearchOutcome = workspace.researchOutcome;
            lastResearchRankTime = nextEnabled(playerNum, RacecraftNext.Feature.RANK_TIME);
            return lastResearchRankTime && lastResearchOutcome != null''')
s = s.replace('if (t >= 0 && t != Integer.MAX_VALUE && (rankRescue', 'if (t >= 0 && (!rankRescue || t != Integer.MAX_VALUE) && (rankRescue')
s = s.replace('        final int horizon = game.racecraftNext.openingRounds;', '        researchOpeningTrials = 0;\n        final int horizon = game.racecraftNext.openingRounds;')
s = s.replace('        researchDemandDepth = forcedSecondDepth = simDepth + 1;', '        researchOpeningTrials++;\n        researchDemandDepth = forcedSecondDepth = simDepth + 1;')
p.write_text(s)
print('Finished status adapters, exact disabled controls and referee bookkeeping')
