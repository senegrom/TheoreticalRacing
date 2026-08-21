#!/usr/bin/env python3
"""Materialize direct exact occupancy maps for projected opponent worlds."""
from pathlib import Path

path = Path('src/tr/logic/RaceAi.java')
source = path.read_text()

anchor = '''\tprivate static final class TwoRoundWorkspace {
'''
cell_class = '''\t/** Exact touched-cell occupancy counts for one projected board. Counts,
\t * rather than booleans, preserve duplicate-cell semantics while allowing
\t * O(1) successor tests and O(1) mover removal/reinsertion. */
\tprivate static final class CellOccupancy {
\t\tfinal byte[] counts;
\t\tfinal int[] touched;
\t\tfinal int width;
\t\tfinal int height;
\t\tint touchedCount;

\t\tCellOccupancy(final int width, final int height) {
\t\t\tthis.width = width;
\t\t\tthis.height = height;
\t\t\tcounts = new byte[width * height];
\t\t\ttouched = new int[width * height];
\t\t}

\t\tvoid clear() {
\t\t\tfor (int i = 0; i < touchedCount; i++)
\t\t\t\tcounts[touched[i]] = 0;
\t\t\ttouchedCount = 0;
\t\t}

\t\tvoid rebuild(final int[][] cells) {
\t\t\tclear();
\t\t\tfor (final int[] cell : cells)
\t\t\t\tif (cell != null)
\t\t\t\t\tadd(cell[0], cell[1]);
\t\t}

\t\tvoid add(final int x, final int y) {
\t\t\tif (x < 0 || y < 0 || x >= width || y >= height)
\t\t\t\treturn;
\t\t\tfinal int index = x * height + y;
\t\t\tif (counts[index]++ == 0)
\t\t\t\ttouched[touchedCount++] = index;
\t\t}

\t\tvoid remove(final int x, final int y) {
\t\t\tif (x < 0 || y < 0 || x >= width || y >= height)
\t\t\t\treturn;
\t\t\tfinal int index = x * height + y;
\t\t\tif (counts[index] != 0)
\t\t\t\tcounts[index]--;
\t\t}

\t\tboolean contains(final int x, final int y) {
\t\t\treturn x >= 0 && y >= 0 && x < width && y < height
\t\t\t\t\t&& counts[x * height + y] != 0;
\t\t}
\t}

\tprivate static final class TwoRoundWorkspace {
'''
assert source.count(anchor) == 1
source = source.replace(anchor, cell_class, 1)

old = '''\t\tfinal byte[] aheadOccupancy;
\t\tfinal int[] aheadTouched;
\t\tint aheadTouchedCount;

\t\tTwoRoundWorkspace(final int players, final int cells) {
'''
new = '''\t\tfinal byte[] aheadOccupancy;
\t\tfinal int[] aheadTouched;
\t\tfinal CellOccupancy blockedOccupancy;
\t\tfinal CellOccupancy world1Occupancy;
\t\tint aheadTouchedCount;

\t\tTwoRoundWorkspace(final int players, final int width, final int height) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\taheadOccupancy = new byte[cells];
\t\t\taheadTouched = new int[players];
\t\t}
\t}

\tprivate static final class PredictionWorkspace {
\t\tfinal int[][][] result;
\t\tfinal int[][][] cells;

\t\tPredictionWorkspace(final int steps, final int players) {
\t\t\tresult = new int[steps][players][];
\t\t\tcells = new int[steps][players][2];
\t\t}
\t}
'''
new = '''\t\t\taheadOccupancy = new byte[width * height];
\t\t\taheadTouched = new int[players];
\t\t\tblockedOccupancy = new CellOccupancy(width, height);
\t\t\tworld1Occupancy = new CellOccupancy(width, height);
\t\t}
\t}

\tprivate static final class PredictionWorkspace {
\t\tfinal int[][][] result;
\t\tfinal int[][][] cells;
\t\tfinal CellOccupancy[] occupancy;

\t\tPredictionWorkspace(final int steps, final int players,
\t\t\t\tfinal int width, final int height) {
\t\t\tresult = new int[steps][players][];
\t\t\tcells = new int[steps][players][2];
\t\t\toccupancy = new CellOccupancy[steps];
\t\t\tfor (int step = 0; step < steps; step++)
\t\t\t\toccupancy[step] = new CellOccupancy(width, height);
\t\t}
\t}
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\tfinal int[][] predicted = predictedSteps[0];
\t\t// In-traffic ply-2 foresight RESTORED (fore2): the v4/v5 pack gate that
'''
new = '''\t\tfinal int[][] predicted = predictedSteps[0];
\t\tfor (int step = 0; step < predictedSteps.length; step++)
\t\t\tpredictionWorkspace.occupancy[step].rebuild(predictedSteps[step]);
\t\tfinal CellOccupancy predictedOccupancy = predictionWorkspace.occupancy[0];
\t\t// In-traffic ply-2 foresight RESTORED (fore2): the v4/v5 pack gate that
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\tfinal double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictedSteps, playerNum, worlds.world1, aheadOccupancy);
'''
new = '''\t\t\tfinal double[] deepCounted = searchMinTurnsCountedSoft3(newX, newY, newVx, newVy, AI1_DEEP_LOOKAHEAD, 0,
\t\t\t\t\tpredictionWorkspace.occupancy, playerNum, worlds.world1Occupancy, aheadOccupancy);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\tfinal int d2SafeCount = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy, playerNum, predicted),
\t\t\t\t\tcountFutureSafeSuccessorsTimed(newX, newY, newVx, newVy, world));
'''
new = '''\t\t\tfinal int d2SafeCount = Math.max(countFutureSafeSuccessors(newX, newY, newVx, newVy,
\t\t\t\t\tplayerNum, predictedOccupancy),
\t\t\t\t\tcountFutureSafeSuccessorsTimed(newX, newY, newVx, newVy, worlds.world1Occupancy));
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

source = source.replace(
'''countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, false)''',
'''countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predictedOccupancy, null, false)''')
source = source.replace(
'''countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predicted, null, true)''',
'''countBrakeProofs(newX, newY, newVx, newVy, widthBudget, predictedOccupancy, null, true)''')

old = '''\tprivate Direction pureMinTurnsMoveSim(final int[] pos, final int[] vel, final int[][] occupied) {
'''
new = '''\tprivate Direction pureMinTurnsMoveSim(final int[] pos, final int[] vel,
\t\t\tfinal CellOccupancy occupied) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
source = source.replace('''\t\t\tif (cellOccupiedByPrediction(newX, newY, occupied))\n''',
                        '''\t\t\tif (occupied.contains(newX, newY))\n''', 1)

old = '''\t\tif (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
\t\t\ttwoRoundWorkspace = new TwoRoundWorkspace(players,
\t\t\t\t\t(game.gameCols + 1) * (game.gameRows + 1));
'''
new = '''\t\tif (twoRoundWorkspace == null || twoRoundWorkspace.current.length != players)
\t\t\ttwoRoundWorkspace = new TwoRoundWorkspace(players,
\t\t\t\t\tgame.gameCols + 1, game.gameRows + 1);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\tworkspace.blocked[playerNum - 1] = workspace.candidatePosition;
\t\tsimulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
\t\t\t\tworkspace.round1Position, workspace.round1Velocity);
\t\tcurrent[playerNum - 1] = null;
\t\tSystem.arraycopy(current, 0, workspace.world1, 0, current.length);
\t\tworkspace.blocked[playerNum - 1] = null;
\t\tsimulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
\t\t\t\tworkspace.round2Position, workspace.round2Velocity);
'''
new = '''\t\tworkspace.blocked[playerNum - 1] = workspace.candidatePosition;
\t\tworkspace.blockedOccupancy.rebuild(workspace.blocked);
\t\tsimulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
\t\t\t\tworkspace.blockedOccupancy, workspace.round1Position, workspace.round1Velocity);
\t\tcurrent[playerNum - 1] = null;
\t\tSystem.arraycopy(current, 0, workspace.world1, 0, current.length);
\t\tworkspace.world1Occupancy.rebuild(workspace.world1);
\t\tworkspace.blocked[playerNum - 1] = null;
\t\tworkspace.blockedOccupancy.remove(candX, candY);
\t\tsimulateRoundPass(playerNum, current, simulatedVelocity, workspace.blocked,
\t\t\t\tworkspace.blockedOccupancy, workspace.round2Position, workspace.round2Velocity);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\tprivate void simulateRoundPass(final int playerNum, final int[][] occupancy,
\t\t\tfinal int[][] simulatedVelocity, final int[][] blocked,
\t\t\tfinal int[][] nextPosition, final int[][] nextVelocity) {
'''
new = '''\tprivate void simulateRoundPass(final int playerNum, final int[][] occupancy,
\t\t\tfinal int[][] simulatedVelocity, final int[][] blocked,
\t\t\tfinal CellOccupancy blockedOccupancy,
\t\t\tfinal int[][] nextPosition, final int[][] nextVelocity) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\t\tfinal int idx = p.getNumber() - 1;
\t\t\t\tfinal int[] current = occupancy[idx];
\t\t\t\tblocked[idx] = null;
\t\t\t\tfinal int[] velocity = simulatedVelocity[idx];
\t\t\t\tfinal Direction direction = pureMinTurnsMoveSim(current, velocity, blocked);
'''
new = '''\t\t\t\tfinal int idx = p.getNumber() - 1;
\t\t\t\tfinal int[] current = occupancy[idx];
\t\t\t\tblocked[idx] = null;
\t\t\t\tblockedOccupancy.remove(current[0], current[1]);
\t\t\t\tfinal int[] velocity = simulatedVelocity[idx];
\t\t\t\tfinal Direction direction = pureMinTurnsMoveSim(current, velocity, blockedOccupancy);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\t\t\t\t\t&& game.isMoveLegalGeometryCached(current[0], current[1], current[0] + nvx, current[1] + nvy)
\t\t\t\t\t\t\t&& !cellOccupiedByPrediction(current[0] + nvx, current[1] + nvy, blocked)) {
'''
new = '''\t\t\t\t\t\t\t&& game.isMoveLegalGeometryCached(current[0], current[1], current[0] + nvx, current[1] + nvy)
\t\t\t\t\t\t\t&& !blockedOccupancy.contains(current[0] + nvx, current[1] + nvy)) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\t\t\t\toccupancy[idx] = positionOut;
\t\t\t\tblocked[idx] = positionOut;
'''
new = '''\t\t\t\toccupancy[idx] = positionOut;
\t\t\t\tblocked[idx] = positionOut;
\t\t\t\tblockedOccupancy.add(nx, ny);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\tprivate double searchMinTurnsSoft3(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
\t\t\tfinal int[][][] predictedSteps, final int playerNum, final int[][] occupancy, final byte[] aheadOccupancy) {
'''
new = '''\tprivate double searchMinTurnsSoft3(final int x, final int y, final int vx, final int vy, final int levels, final int stepIdx,
\t\t\tfinal CellOccupancy[] predictedSteps, final int playerNum,
\t\t\tfinal CellOccupancy occupancy, final byte[] aheadOccupancy) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

source = source.replace('''\t\t\t\tif (cellOccupiedByPrediction(nx, ny, occupancy))\n''',
                        '''\t\t\t\tif (occupancy.contains(nx, ny))\n''', 2)
source = source.replace('''\t\t\t\tif (stepIdx < predictedSteps.length && cellOccupiedByPrediction(nx, ny, predictedSteps[stepIdx]))\n''',
                        '''\t\t\t\tif (stepIdx < predictedSteps.length && predictedSteps[stepIdx].contains(nx, ny))\n''', 2)

old = '''\tprivate double[] searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
\t\t\tfinal int stepIdx, final int[][][] predictedSteps, final int playerNum, final int[][] occupancy,
\t\t\tfinal byte[] aheadOccupancy) {
'''
new = '''\tprivate double[] searchMinTurnsCountedSoft3(final int x, final int y, final int vx, final int vy, final int levels,
\t\t\tfinal int stepIdx, final CellOccupancy[] predictedSteps, final int playerNum,
\t\t\tfinal CellOccupancy occupancy, final byte[] aheadOccupancy) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\tprivate int countFutureSafeSuccessorsTimed(final int x, final int y, final int vx, final int vy,
\t\t\tfinal int[][] occupancy) {
'''
new = '''\tprivate int countFutureSafeSuccessorsTimed(final int x, final int y, final int vx, final int vy,
\t\t\tfinal CellOccupancy occupancy) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
source = source.replace('''\t\t\tif (cellOccupiedByPrediction(nx, ny, occupancy))\n''',
                        '''\t\t\tif (occupancy.contains(nx, ny))\n''', 1)

old = '''\t\tif (predictionWorkspace == null || predictionWorkspace.result.length != projectionSteps
\t\t\t\t|| predictionWorkspace.result[0].length != game.players.length)
\t\t\tpredictionWorkspace = new PredictionWorkspace(projectionSteps, game.players.length);
'''
new = '''\t\tif (predictionWorkspace == null || predictionWorkspace.result.length != projectionSteps
\t\t\t\t|| predictionWorkspace.result[0].length != game.players.length)
\t\t\tpredictionWorkspace = new PredictionWorkspace(projectionSteps, game.players.length,
\t\t\t\t\tgame.gameCols + 1, game.gameRows + 1);
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)

old = '''\tprivate boolean cellOccupiedByPrediction(final int x, final int y, final int[][] predicted) {
\t\tfor (final int[] p : predicted) {
\t\t\tif (p != null && p[0] == x && p[1] == y)
\t\t\t\treturn true;
\t\t}
\t\treturn false;
\t}

'''
assert source.count(old) == 1
source = source.replace(old, '', 1)

old = '''\tprivate int countFutureSafeSuccessors(final int x, final int y, final int vx, final int vy, final int playerNum,
\t\t\tfinal int[][] predicted) {
'''
new = '''\tprivate int countFutureSafeSuccessors(final int x, final int y, final int vx, final int vy,
\t\t\tfinal int playerNum, final CellOccupancy predicted) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
source = source.replace('''\t\t\tif (cellOccupiedByPrediction(nx, ny, predicted))\n''',
                        '''\t\t\tif (predicted.contains(nx, ny))\n''', 1)

old = '''\tprivate int countBrakeProofs(final int x, final int y, final int vx, final int vy, final double targetSpeed,
\t\t\tfinal int[][] predicted, final int[] bestBrake, final boolean requireRoomy) {
'''
new = '''\tprivate int countBrakeProofs(final int x, final int y, final int vx, final int vy,
\t\t\tfinal double targetSpeed, final CellOccupancy predicted,
\t\t\tfinal int[] bestBrake, final boolean requireRoomy) {
'''
assert source.count(old) == 1
source = source.replace(old, new, 1)
source = source.replace('''\t\t\tif (cellOccupiedByPrediction(bx, by, predicted))\n''',
                        '''\t\t\tif (predicted.contains(bx, by))\n''', 1)

source = source.replace('{@link #cellOccupiedByPrediction}', '{@link CellOccupancy#contains}')
assert 'cellOccupiedByPrediction(' not in source
assert source.count('world1Occupancy') >= 4
assert source.count('blockedOccupancy') >= 8
assert source.count('predictionWorkspace.occupancy') >= 3
path.write_text(source)
print('materialized exact projected-cell occupancy maps')
