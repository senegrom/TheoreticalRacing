package tr.gui;

import java.awt.Shape;
import java.awt.geom.Area;
import java.awt.geom.Line2D;
import java.util.List;
import tr.logic.Player;
import tr.logic.Track;

/** The original renderer's data in grid coordinates for the native canvas UI. */
public final class RaceUI {
    public static final int GRID_DIST = 1;
    public float[][] startZone;
    public double[][] checkpoints;
    public int[][] closures;
    public Shape trackPol;
    public Line2D finishLine;
    public List<int[]> prePath;
    public RaceUI(final int rows, final int cols) {}
    public void finishTrack(final Shape corridor) {
        trackPol = corridor == null ? null : new Area(corridor);
    }
    public Object getGrid() { return null; }
    public void setLoopClosure(final int[][] value) { closures = value; }
    public void hideStartZone() { startZone = null; }
    public void setCheckpoints(final Line2D[] value) {
        checkpoints = value == null ? null : java.util.Arrays.stream(value)
                .map(l -> new double[]{l.getX1(), l.getY1(), l.getX2(), l.getY2()}).toArray(double[][]::new);
    }
    public void setFinishLine(final Line2D line) {
        finishLine = line == null ? null : new Line2D.Double(
                line.getX1(), line.getY1(), line.getX2(), line.getY2());
    }
    public void setPlayers(final Player[] players) {}
    public void setPrePath(final List<int[]> value) { prePath = value; }
    public void setStartZone(final float[][] value) { startZone = value; }
    public void setTrack(final Track track) {}
    /** The page draws velocities from the snapshot; nothing to keep. */
    public void setVelVector(final int[] value, final int player) {}
}
