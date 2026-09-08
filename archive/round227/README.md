# Round 227 experiment archive

This archive preserves the completed `racecraft-round227-validation` experiment
at branch tip `1e0512b4c86271dcffc7bf86a4c8d5c512df0bae`.
Its complete history is retained as the parent history of this archive commit.
The candidate is preserved for future work; it has not been promoted into master.

The candidate patch applies to baseline
`f63cf1c3c87b7677a29c3c9f15a6ddbed49a090e`.
The original workflow is retained at `.github/workflows/round227-h2h.yml`
in this archive. It records the build and mirrored fleet commands, seeds,
candidate slot assignments, start modes and expected patch hashes.

The final successful run was
[34208227582](https://github.com/senegrom/TheoreticalRacing/actions/runs/34208227582).
Each start mode compares 840 mirrored race pairs (1,680 races).

| Start mode | Candidate minus champion mean place | Standard error |
| --- | ---: | ---: |
| legacy | -0.004 | 0.003 |
| informed | -0.005 | 0.003 |
| scatter | -0.000 | 0.001 |

These are the recorded head-to-head measurements, not a promotion decision.
Full summaries and both slot assignments' fleet records are under `results/`.

The original downloaded artifact ZIPs are retained alongside their extracted
contents. `manifest.json` records artifact IDs, byte sizes and SHA-256 hashes.
The original compressed candidate blob is `candidate.patch.xz`; its verified,
decompressed form is `candidate.patch`.

The archive is published as tag `archive/2026-09-08-round227-validation`.
To recover the complete experiment:

```sh
git fetch origin tag archive/2026-09-08-round227-validation
git switch --detach archive/2026-09-08-round227-validation
```

To work on the candidate, first copy `archive/round227/candidate.patch` outside
the checkout, create a work branch at the baseline above, then apply that copy
with `git apply --index`. The archived source tree itself remains the baseline;
the experimental policy exists in the preserved patch.

Archive verification: all three original ZIPs opened successfully; extracted
files match their ZIP members; compressed and decompressed candidate hashes
match the workflow; `git apply --check` accepts the patch on the preserved
baseline. No application source or decision logic was changed for this archive.

