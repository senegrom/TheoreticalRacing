package tr.logic;

import java.util.ArrayList;
import java.util.Arrays;
import java.util.List;

/** Per-race experience and completed proof strategies. Only committed physical
 * moves teach the archive. Forecasts receive detached copies and never teach it.
 * Old successful paths are proposals, not occupancy or safety guarantees. */
final class LearningMemory {
    static final int SLOTS = 9, CAPACITY = 64, WINDOW = 4;
    record Pose(int x, int y, int vx, int vy, int lap, int gate, boolean left) {
        static Pose of(final Player p) {
            return new Pose(p.getPosition()[0], p.getPosition()[1], p.getVelocity()[0], p.getVelocity()[1],
                    p.getLap(), p.getNextGate(), p.hasLeftGrid());
        }
        static Pose of(final int[] r) { return new Pose(r[2],r[3],r[4],r[5],r[7],r[8],r[13]!=0); }
        boolean sameEntry(final Pose other) {
            return x==other.x && y==other.y && vx==other.vx && vy==other.vy && gate==other.gate && left==other.left;
        }
        String encode() { return x+"_"+y+"_"+vx+"_"+vy+"_"+lap+"_"+gate+"_"+(left?1:0); }
        static Pose parse(final String text) {
            final String[] f=text.split("_",-1);
            if(f.length!=7) throw new IllegalArgumentException("invalid remembered pose");
            final int[] v=Arrays.stream(f).mapToInt(Integer::parseInt).toArray();
            if(v[0]<0||v[1]<0||Math.abs((long)v[2])>100000||Math.abs((long)v[3])>100000
                    ||v[4]<0||v[5]<0||v[5]>2||v[6]<0||v[6]>1) throw new IllegalArgumentException("invalid pose ledger");
            final Pose pose=new Pose(v[0],v[1],v[2],v[3],v[4],v[5],v[6]!=0);
            if(!pose.encode().equals(text)) throw new IllegalArgumentException("noncanonical pose");
            return pose;
        }
    }
    record Segment(Pose start, List<Direction> actions, Pose end) {
        Segment {
            actions=List.copyOf(actions);
            if(actions.isEmpty()||actions.size()>WINDOW||start.lap()!=end.lap()||start.left()!=end.left())
                throw new IllegalArgumentException("invalid corner segment");
            long x=start.x(),y=start.y(),vx=start.vx(),vy=start.vy();
            for(final Direction a:actions) { vx+=a.dx;vy+=a.dy;x+=vx;y+=vy; }
            if(x!=end.x()||y!=end.y()||vx!=end.vx()||vy!=end.vy())
                throw new IllegalArgumentException("remembered kinematics mismatch");
        }
        String encode() { return start.encode()+"~"+String.join("+",actions.stream().map(Enum::name).toList())+"~"+end.encode(); }
        static Segment parse(final String text) {
            final String[] f=text.split("~",-1);
            if(f.length!=3) throw new IllegalArgumentException("invalid segment encoding");
            return new Segment(Pose.parse(f[0]),Arrays.stream(f[1].split("\\+",-1)).map(Direction::valueOf).toList(),Pose.parse(f[2]));
        }
    }
    private final List<List<Segment>> archive=new ArrayList<>(), recent=new ArrayList<>();
    private final ProofNumberSearch.Plan[] proofs=new ProofNumberSearch.Plan[SLOTS];
    LearningMemory() { for(int i=0;i<SLOTS;i++) { archive.add(new ArrayList<>());recent.add(new ArrayList<>()); } }
    LearningMemory copy() {
        final LearningMemory out=new LearningMemory();
        for(int i=0;i<SLOTS;i++) { out.archive.get(i).addAll(archive.get(i));out.recent.get(i).addAll(recent.get(i));out.proofs[i]=proofs[i]; }
        return out;
    }
    ProofNumberSearch.Plan proof(final int slot) { return proofs[slot]; }
    void proof(final int slot, final ProofNumberSearch.Plan plan) { proofs[slot]=plan; }
    List<Segment> remembered(final int slot, final Pose entry) {
        final List<Segment> matches=new ArrayList<>();
        for(final Segment s:archive.get(slot)) if(s.start().lap()<entry.lap() && s.start().sameEntry(entry)) matches.add(s);
        matches.sort(java.util.Comparator.comparingInt((Segment s)->-s.actions().size()).thenComparing(Segment::encode));
        return List.copyOf(matches.subList(0,Math.min(2,matches.size())));
    }
    /** Must be called AFTER the live Undo snapshot and BEFORE applying the move.
     * Detached complete-race replays call it at the same point. */
    void commitCorner(final RaceGame game, final Direction action) {
        final int slot=game.subgamestate;
        final Player p=game.players[slot];
        if(!game.racecraftNext.enabled(game,p.getNumber(),RacecraftNext.Feature.CORNER_MEMORY)
                ||game.raceTurnLimitReached()||p.isFinished()||action==null) return;
        final Pose start=Pose.of(p);
        final long nx=(long)start.x()+start.vx()+action.dx, ny=(long)start.y()+start.vy()+action.dy;
        if(nx<Integer.MIN_VALUE||nx>Integer.MAX_VALUE||ny<Integer.MIN_VALUE||ny>Integer.MAX_VALUE) { recent.get(slot).clear();return; }
        boolean occupied=false;
        for(int i=0;i<game.players.length;i++) if(i!=slot && !game.players[i].isFinished()) {
            final int[] other=game.players[i].getPosition(); occupied|=other[0]==nx && other[1]==ny;
        }
        final RaceGame.MoveResult move=game.evaluateMove(start.lap(),start.gate(),!start.left(),start.x(),start.y(),(int)nx,(int)ny,occupied);
        final boolean left=start.left()||game.startZoneA!=null&&!game.startZoneA.contains(nx,ny);
        if(!move.legal()||move.finishes()||move.lapCross()||left!=start.left()) { recent.get(slot).clear();return; }
        final Pose end=new Pose((int)nx,(int)ny,start.vx()+action.dx,start.vy()+action.dy,move.lapAfter(),move.gateAfter(),left);
        observe(game,slot,new Segment(start,List.of(action),end));
    }
    void observe(final RaceGame game, final int slot, final Segment step) {
        if(step.actions().size()!=1) throw new IllegalArgumentException("observation is one committed move");
        final List<Segment> tail=recent.get(slot);
        if(!tail.isEmpty()&&!tail.get(tail.size()-1).end().equals(step.start())) tail.clear();
        tail.add(step); if(tail.size()>WINDOW) tail.remove(0);
        for(int first=0;first<tail.size()-1;first++) {
            final List<Direction> actions=new ArrayList<>();
            for(int i=first;i<tail.size();i++) actions.addAll(tail.get(i).actions());
            if(actions.size()!=WINDOW) continue;
            final Pose start=tail.get(first).start(), end=step.end();
            boolean bends=false;
            int vx=start.vx(), vy=start.vy();
            for(final Direction a:actions) { bends|=(long)vx*(vy+a.dy)!=(long)vy*(vx+a.dx);vx+=a.dx;vy+=a.dy; }
            if(!bends) continue;
            final int from=distance(game,start), to=distance(game,end);
            if(from==Integer.MAX_VALUE||to==Integer.MAX_VALUE||to>=from||start.lap()!=end.lap()||start.left()!=end.left()) continue;
            final Segment segment=new Segment(start,actions,end);
            final List<Segment> library=archive.get(slot);
            boolean known=false;
            for(final Segment prior:library) known|=prior.start().sameEntry(segment.start()) && prior.actions().equals(segment.actions());
            if(!known) {
                library.add(segment);
                // Stable spatial sampling, not a FIFO that forgets lap one before lap two arrives.
                library.sort(java.util.Comparator.comparing(LearningMemory::priority));
                if(library.size()>CAPACITY) library.remove(library.size()-1);
            }
        }
    }
    private static String priority(final Segment s) {
        final Pose p=s.start();
        return RacecraftReplay.sha(p.x()+":"+p.y()+":"+p.vx()+":"+p.vy()+":"+p.gate()+":"+p.left()+":"+s.actions());
    }
    private static int distance(final RaceGame game,final Pose s) {
        if(game.lapGates==null) return game.reach.turnsToFinish(s.x(),s.y(),s.vx(),s.vy());
        final OptimalPotential map=game.optimalPotential();
        return map==null?Integer.MAX_VALUE:map.movesToFinish(OptimalPotential.remainingEvents(s.gate(),s.lap(),game.totalLaps),s.x(),s.y(),s.vx(),s.vy());
    }
    String encode(final int n) {
        boolean any=false;
        for(int i=0;i<n;i++) any|=!archive.get(i).isEmpty()||!recent.get(i).isEmpty()||proofs[i]!=null;
        if(!any) return "-";
        final List<String> slots=new ArrayList<>();
        for(int i=0;i<n;i++) slots.add(segments(archive.get(i))+"@"+segments(recent.get(i))+"@"+(proofs[i]==null?"-":proofs[i].encode()));
        return String.join(".",slots);
    }
    private static String segments(final List<Segment> list) {
        return list.isEmpty()?"-":String.join("/",list.stream().map(Segment::encode).toList());
    }
    static LearningMemory parse(final String text,final int n) {
        if(n<1||n>SLOTS||text.length()>524288) throw new IllegalArgumentException("learning memory limit");
        final LearningMemory out=new LearningMemory(); if(text.equals("-")) return out;
        final String[] slots=text.split("\\.",-1);
        if(slots.length!=n) throw new IllegalArgumentException("learning memory roster mismatch");
        for(int i=0;i<n;i++) {
            final String[] f=slots[i].split("@",-1);
            if(f.length!=3) throw new IllegalArgumentException("learning memory shape");
            readSegments(f[0],out.archive.get(i),CAPACITY,false);readSegments(f[1],out.recent.get(i),WINDOW,true);
            if(!f[2].equals("-")) {
                out.proofs[i]=ProofNumberSearch.Plan.parse(f[2]);
                if(out.proofs[i].place()>n) throw new IllegalArgumentException("proof rank outside roster");
            }
        }
        if(!out.encode(n).equals(text)) throw new IllegalArgumentException("noncanonical learning memory");
        return out;
    }
    private static void readSegments(final String text,final List<Segment> out,final int cap,final boolean trail) {
        if(text.equals("-")) return;
        final String[] rows=text.split("/",-1);if(rows.length>cap) throw new IllegalArgumentException("too many remembered segments");
        for(final String row:rows) {
            final Segment s=Segment.parse(row);
            if(trail&&(s.actions().size()!=1||!out.isEmpty()&&!out.get(out.size()-1).end().equals(s.start())))
                throw new IllegalArgumentException("discontinuous learning trail");
            if(!trail && (s.actions().size()<2||out.contains(s))) throw new IllegalArgumentException("duplicate/short corner");
            out.add(s);
        }
    }
}
