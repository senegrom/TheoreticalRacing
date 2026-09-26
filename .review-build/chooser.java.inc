	/** Review experiments are root/candidate gated; the control keeps the promoted chooser. */
	private Direction jointChooser(final int[] pos, final int[] vel, final int playerNum,
			final Direction best, final double[] scoreByDir, final double bestScore) {
		final boolean rootExperiment = simDepth == 0 && trueConfirmDepth == 0;
		final boolean crossing = rootExperiment && RacecraftReview.enabled(game, playerNum,
				RacecraftReview.Feature.CROSSING);
		final boolean diverse = rootExperiment && RacecraftReview.enabled(game, playerNum,
				RacecraftReview.Feature.DIVERSE);
		final boolean projected = rootExperiment && RacecraftReview.enabled(game, playerNum,
				RacecraftReview.Feature.PROJECTED_PLACE);
		final Direction[] order = RacecraftReview.shortlist(scoreByDir, bestScore, diverse);
		if (order.length < 2) return best;
		final long[] verdicts = new long[order.length];
		java.util.Arrays.fill(verdicts, -1L);
		Direction pick = null;
		long pickVerdict = -1L;
		for (int k = 0; k < order.length; k++) {
			final Direction d = order[k];
			final int nx = pos[0] + vel[0] + d.dx, ny = pos[1] + vel[1] + d.dy;
			if (crossing) {
				final Player mover = game.players[game.subgamestate];
				final RaceGame.MoveResult move = game.evaluateMove(mover.getLap(), mover.getNextGate(),
						pos[0], pos[1], nx, ny, game.isCrashingPlayer(nx, ny, playerNum));
				if (move.finishes()) return d;
				if (!move.legal()) continue;
			} else if (game.crossesFinishLegally(pos[0], pos[1], nx, ny)) {
				// Unchanged control, including the known nonterminal-crossing abort.
				return best;
			}
			final long verdict = reviewChooserVerdict(pos, vel, playerNum, d, projected, -1);
			verdicts[k] = verdict;
			if (pick == null || verdict >= 0 && (pickVerdict < 0 || verdict < pickVerdict)) {
				pick = d;
				pickVerdict = verdict;
			}
		}
		if (pick == null) return best;
		if (rootExperiment && RacecraftReview.enabled(game, playerNum, RacecraftReview.Feature.SELECTIVE)) {
			// Upgrade only a tied alternative and only one directly interacting rival.
			// This is a declared first-response model, not a coalition or a safety proof.
			Direction alternative = null;
			for (int k = 0; k < order.length; k++)
				if (order[k] != pick && pickVerdict >= 0 && verdicts[k] == pickVerdict) {
					alternative = order[k];
					break;
				}
			if (alternative != null) {
				final int rival = reviewContestingRival(pos, vel, playerNum, pick, alternative);
				if (rival >= 0) {
					final long stronger = reviewChooserVerdict(pos, vel, playerNum, pick, projected, rival);
					final long alternativeStronger = reviewChooserVerdict(pos, vel, playerNum,
							alternative, projected, rival);
					if (RacecraftReview.improvesTiedForecast(pickVerdict, pickVerdict, stronger, alternativeStronger))
						pick = alternative;
				}
			}
		}
		return pick;
	}

	/** Forecast side channels are scoped/restored even when a nested policy throws. */
	private long reviewChooserVerdict(final int[] pos, final int[] vel, final int playerNum,
			final Direction direction, final boolean projected, final int strongerRival) {
		final int oldKeyDepth = placeKeyDepth, oldProjected = reviewProjectedDepth;
		final long oldKey = placeKey;
		final int oldReplyDepth = reviewReplyDepth, oldRival = reviewReplyRival;
		final boolean oldReplyUsed = reviewReplyUsed;
		try {
			placeKeyDepth = simDepth + 1;
			placeKey = -1;
			reviewProjectedDepth = projected ? simDepth + 1 : -1;
			reviewReplyDepth = strongerRival >= 0 ? simDepth + 1 : -1;
			reviewReplyRival = strongerRival;
			reviewReplyUsed = false;
			final int nvx = vel[0] + direction.dx, nvy = vel[1] + direction.dy;
			final int outcome = simOutcome(pos[0] + nvx, pos[1] + nvy, nvx, nvy, playerNum,
					AI1_CHOOSER_ROUNDS, true, true, true, true, true, AI1_SCORER_MAXRIVALS, null);
			// An unreached required reply cannot certify a model comparison.
			final long verdict = strongerRival >= 0 && !reviewReplyUsed ? -1
					: outcome >= 0 && placeKey >= 0 ? placeKey : outcome;
			if (reviewTrace != null && simDepth == 0)
				reviewTrace.candidate(direction, strongerRival < 0 ? "nominal" : "one-stronger-reply", verdict);
			return verdict;
		} finally {
			placeKeyDepth = oldKeyDepth;
			placeKey = oldKey;
			reviewProjectedDepth = oldProjected;
			reviewReplyDepth = oldReplyDepth;
			reviewReplyRival = oldRival;
			reviewReplyUsed = oldReplyUsed;
		}
	}

	/** Intersection of physical one-step landing rectangles with our next-step
	 * rectangle is only a cheap activation test. All cars stay in the actual rollout. */
	private int reviewContestingRival(final int[] pos, final int[] vel, final int playerNum,
			final Direction first, final Direction second) {
		int selected = -1, bestDistance = Integer.MAX_VALUE;
		for (int i = 0; i < game.players.length; i++) {
			final Player rival = game.players[i];
			if (rival.isFinished() || rival.getNumber() == playerNum) continue;
			final int[] rp = rival.getPosition(), rv = rival.getVelocity();
			for (final Direction d : new Direction[]{first, second}) {
				final int vx = vel[0] + d.dx, vy = vel[1] + d.dy;
				final int futureX = pos[0] + 2 * vx, futureY = pos[1] + 2 * vy;
				final int distance = Math.max(Math.abs(futureX - rp[0] - rv[0]),
						Math.abs(futureY - rp[1] - rv[1]));
				if (distance <= 2 && distance < bestDistance) {
					selected = i;
					bestDistance = distance;
				}
			}
		}
		return selected;
	}

