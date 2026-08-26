# Branch archive — 2026-08-26 sweep

All branches except `master` were deleted on 2026-08-26 (user order:
"merge all new knowledge and delete all branches but main/master").
Every unmerged tip remains permanently reachable through one octopus
commit with 136 parents, tagged on origin:

    tag: archive/branches-2026-08-26  (octopus 7786cc65)
    recover a branch: git fetch origin --tags && git checkout <sha>

A concurrent cleanup (the other pipeline) deleted most branches while
this sweep ran and re-recorded two tips past the first octopus; the
final eight tips live at deletion time are anchored by a second tag:

    tag: archive/branches-2026-08-26.2  (octopus f98c9061)
    r173-adaptive-point-cache d94836b, r176-finish-sprint eb8dd2c,
    plus six unchanged tips also present in the first octopus.

Knowledge disposition: the promoted rounds are in master; every round
is censused in racing-memory.md (the 2026-08-26 sweep entry covers the
screen-only rounds). Notable unique content preserved only here: the
pyrace learned-AI prototype and the pre-rewrite AI history (see
backup-full-history), and the pre-rewrite track-correction history
(worktree-agent-ada2a22e19ba76814).

| tip | date | branch | last subject |
|-----|------|--------|--------------|
| 95d905935fd6 | 2026-07-07 | backup-full-history | pyrace: RL self-play loop (value head + REINFORCE, warm-started from BC) |
| 44d17d257360 | 2026-08-21 | origin/agent/rounds-179-181-unpublished-work | Record status of unpublished Rounds 179-181 |
| 69a1f25777de | 2026-06-09 | worktree-agent-ada2a22e19ba76814 | F1 tracks: correct racing direction + start/finish at the real S/F |
| 148b48cf25ae | 2026-08-15 | origin/agent/ai-racing-speed-96-champion-gate | Run the Round 96 post-mirror champion gate |
| 36388cee7639 | 2026-08-15 | origin/agent/ai-racing-speed-96-champion-promotion | Remove staged Round 95 and Round 96 evidence patch |
| e1e7bf9a7ca4 | 2026-08-15 | origin/agent/ai-racing-speed-96-frontier-probe | Probe the Round 96 finish frontier |
| 37267231106c | 2026-08-15 | origin/agent/ai-racing-speed-96-neutral-accel | Aggregate the Round 96 promotion battery |
| 465db792fc62 | 2026-08-15 | origin/agent/ai-racing-speed-96-neutral-accel-final | Remove staged Round 96 source patch |
| 8ae1637f738f | 2026-08-15 | origin/agent/ai-racing-speed-96-policy-export | Export Round 96 policy experiment |
| 02753403cdb0 | 2026-08-15 | origin/agent/ai-racing-speed-96-scored-finish-frontier | Fix the field-frontier compile scope |
| ff726d44c9af | 2026-08-15 | origin/agent/ai-racing-speed-97-bottleneck-brake | Rerun the full differential on optimized Round 97 |
| 0059470afc17 | 2026-08-15 | origin/agent/ai-racing-speed-97-source-export | Export exact Round 97 baseline source |
| f3e260c6fc9a | 2026-08-15 | origin/agent/ai-racing-speed-100-djs-probe | Summarize Round 100 danger-switch certificates |
| dba0040829ad | 2026-08-15 | origin/agent/ai-racing-speed-100-finish-probe | Summarize the Round 100 finish frontier |
| 64d12b66f3e8 | 2026-08-15 | origin/agent/ai-racing-speed-100-seal-pace-screen | Benchmark Round 100 decision runtime |
| bc1711f378e0 | 2026-08-15 | origin/agent/ai-racing-speed-100-source-export | Export exact Round 100 baseline source |
| 6d62b9f13661 | 2026-08-15 | origin/agent/ai-racing-speed-100-strict-field-probe | Diagnose Round 100 strict-field boundaries |
| 67498c0b83a6 | 2026-08-15 | origin/agent/ai-racing-speed-101-djs-retention | Screen Round 101 DJS retention |
| 427a71f10e42 | 2026-08-16 | origin/agent/ai-racing-speed-101-finish-denial | Replace finish-denial patch with verified exact patch |
| 7284184b43d7 | 2026-08-15 | origin/agent/ai-racing-speed-101-guarded-field | Rerun the guarded-field differential with the switchback guard |
| 18980e72e5cd | 2026-08-16 | origin/agent/ai-racing-speed-101-guarded-field-v3 | Keep candidate jar available for regression tests |
| a58c69006889 | 2026-08-16 | origin/agent/ai-racing-speed-101-guarded-quorum | Run refined guarded-quorum differential |
| 2954b69cbbd7 | 2026-08-15 | origin/agent/ai-racing-speed-101-source-export | Export exact Round 101 baseline source |
| 142373f7697c | 2026-08-16 | origin/agent/ai-racing-speed-102-guarded-field-export | Export the guarded-field candidate source |
| f998a1d6634d | 2026-08-16 | origin/agent/ai-racing-speed-102-stable-field-accel | Apply Round 102 stable field acceleration |
| 412b3a664ca0 | 2026-08-16 | origin/agent/ai-racing-speed-102-v3-export | Export the v3 pace candidate source |
| 427df0f641ae | 2026-08-16 | origin/agent/ai-racing-speed-102-v3-fresh-gate | Run fresh-seed and runtime gates for v3 |
| 5ef5add5fabd | 2026-08-16 | origin/agent/ai-racing-speed-102-v3-summary | Summarize the v3 pace differential |
| 160b3907c45e | 2026-08-16 | origin/agent/ai-racing-speed-103-agent-identity-gate | Launch Round 103 identity gate |
| ea57f9645ccf | 2026-08-16 | origin/agent/ai-racing-speed-103-ai2-field-gate | Gate Round 103 field acceleration for AI2 |
| 22c587ed1398 | 2026-08-16 | origin/agent/ai-racing-speed-103-controller | Materialize the Round 103 Zigzag rescue |
| 097bdf788f92 | 2026-08-16 | origin/agent/ai-racing-speed-103-field-horizon-probe | Probe structural guards for Spa counterexamples |
| ffad54db0ce3 | 2026-08-16 | origin/agent/ai-racing-speed-103-full-field-confirm | Gate all Round 103 full-policy rescues |
| d49801244dd9 | 2026-08-16 | origin/agent/ai-racing-speed-103-full-roster-confirm | Round 103: use full certified rival roster |
| d094beb7c15c | 2026-08-16 | origin/agent/ai-racing-speed-103-full-roster-confirm-v2 | Round 103: use full certified rival roster |
| 606af1c81d38 | 2026-08-16 | origin/agent/ai-racing-speed-103-min-confirm-gate | Gate minimal Round 103 true-rival confirmation |
| ebd061c2e11a | 2026-08-16 | origin/agent/ai-racing-speed-103-six-rival-gate | Launch Round 103 full gate |
| 1bda0ff3b69c | 2026-08-16 | origin/agent/ai-racing-speed-103-six-rival-mirror-gate | Add mirrored Round 103 candidate |
| e20453b7bd07 | 2026-08-16 | origin/agent/ai-racing-speed-103-six-rival-mirror-gate-v2 | Mirror Round 103 regression |
| 870704671937 | 2026-08-16 | origin/agent/ai-racing-speed-103-source-export | Fix Round 103 source export |
| 30c37ee649ca | 2026-08-16 | origin/agent/ai-racing-speed-103-spa-diagnostic | Trace Round 103 Spa counterexamples |
| e3c4740f39a6 | 2026-08-16 | origin/agent/ai-racing-speed-103-wide-confirm-gate | Gate Round 103 stable pace and wide confirmation |
| 888e29737651 | 2026-08-16 | origin/agent/ai-racing-speed-103-zigzag-final | Run Round 103 exact promotion gate |
| 94d008e4b32c | 2026-08-16 | origin/agent/ai-racing-speed-103-zigzag-rescue | Rerun Round 103 exact gate after materializer fix |
| 88ed5ca5b1d2 | 2026-08-16 | origin/agent/ai-racing-speed-104-controller-final | Run Round 104 gate at the latest controller head |
| f36f1b5f804b | 2026-08-16 | origin/agent/ai-racing-speed-104-real | Add Round 104 exact AI1 gate |
| a5a2800426e3 | 2026-08-16 | origin/agent/ai-racing-speed-104-source-export | Fix Round 104 source export |
| 4f74424d34dc | 2026-08-16 | origin/agent/ai-racing-speed-104-stable-forward-pack | Gate Round 104 stable forward-pack acceleration |
| 785e4f183e27 | 2026-08-17 | origin/agent/ai-racing-speed-106-champion-gate-v2 | Launch Round 106 mirrored champion gate |
| 42651308fe23 | 2026-08-17 | origin/agent/ai-racing-speed-106-launch-funnel | Add Round 106 exact differential tool |
| 71bb8624d87a | 2026-08-17 | origin/agent/ai-racing-speed-106-opening-pack-v2 | Launch Round 106 exact opening-pack gate |
| 4c46ad5e2671 | 2026-08-17 | origin/agent/ai-racing-speed-106-source-export | Fix Round 106 source export |
| 83c0544e76bb | 2026-08-17 | origin/agent/ai-racing-speed-107-controller-gate | Add exact Round 107 differential comparator |
| 158006f192d7 | 2026-08-17 | origin/agent/ai-racing-speed-107-gate | Launch Round 107 exact rescue gate |
| 0efcbccfcd0f | 2026-08-17 | origin/agent/ai-racing-speed-108-equal-speed-veto-gate | Retry transient Round 108 matrix failures without weakening gates |
| fee2721e59d6 | 2026-08-17 | origin/agent/ai-racing-speed-108-equal-speed-veto-parallel | Round 108: veto false equal-speed switch targets |
| 00331c7f1a7d | 2026-08-18 | origin/agent/ai-racing-speed-109-field-equal-probe | Refresh pace experiment status including narrowed candidate |
| 8b51029257a2 | 2026-08-17 | origin/agent/ai-racing-speed-109-hungaroring144-probe | Screen the broad Hungaroring 144 rescue on the current champion |
| f365fb3a64a4 | 2026-08-18 | origin/agent/ai-racing-speed-109-pace-certificate-sweep | Record Round 109 pace-certificate sweep |
| 5c22164a788c | 2026-08-17 | origin/agent/ai-racing-speed-110-dual-frontier | Launch the Round 110 exact promotion gate |
| 790ce370a459 | 2026-08-17 | origin/agent/ai-racing-speed-110-pareto-field-proof | Record Spa seed 11 Pareto counterexample |
| ac3da7de3a0c | 2026-08-17 | origin/agent/ai-racing-speed-111-opening-pack-census | Run the opening-pack frontier census |
| 02bd143015c1 | 2026-08-18 | origin/agent/ai-racing-speed-111-speed9-pareto | Launch narrowed speed-nine Pareto screen |
| dfe49f2a9fbb | 2026-08-18 | origin/agent/ai-racing-speed-111-speed9-simple | Record Coil speed-nine diagnostic |
| 349ad4f4744b | 2026-08-17 | origin/agent/ai-racing-speed-112-far-opening-confirm | Probe the far-opening target and counterexample |
| 37bd1b7c49f6 | 2026-08-18 | origin/agent/ai-racing-speed-112-finish31-frontier | Record synchronized far-finish screen |
| 9a63180bd94d | 2026-08-18 | origin/agent/ai-racing-speed-112-speed9-noncoast | Record non-coasting speed-nine probe |
| 06985870213b | 2026-08-18 | origin/agent/ai-racing-speed-113-speed9-noncoast-v2 | Record clean non-coasting speed-nine probe |
| a2c6d7143811 | 2026-08-18 | origin/agent/ai-racing-speed-113-speed9-spa-diagnostic | Record Spa speed-nine counterexamples |
| 36a4f681a193 | 2026-08-18 | origin/agent/ai-racing-speed-114-graduated-speed9 | Record graduated speed-nine boundary probe |
| 758d2df0962f | 2026-08-18 | origin/agent/ai-racing-speed-114-speed9-silverstone-diagnostic | Record Silverstone speed-nine counterexamples |
| fbea72f025a1 | 2026-08-18 | origin/agent/ai-racing-speed-115-graduated-frontier | Record promoted Round 115 master commit |
| 14dafc1118e3 | 2026-08-18 | origin/agent/ai-racing-speed-115-source-export | Record Round 115 source-export run |
| 63f03c568a03 | 2026-08-18 | origin/agent/ai-racing-speed-116-deep-high-speed-accel | Record Round 116 screen run |
| 37ece6f05872 | 2026-08-18 | origin/agent/ai-racing-speed-116-high-speed-h12 | Launch Round 116 high-speed 12-round pace gate |
| 232247bd0a4b | 2026-08-18 | origin/agent/ai-racing-speed-116-source-export | Publish Round 116 source-export run id |
| a04b9a28733a | 2026-08-18 | origin/agent/ai-racing-speed-117-six-ahead-accel | Record Round 117 promotion run |
| 51f01d81d885 | 2026-08-18 | origin/agent/ai-racing-speed-118-seven-ahead-screen | Record Round 118 seven-ahead census |
| 6c4aee36ed14 | 2026-08-18 | origin/agent/ai-racing-speed-118-source-export | Export live Round 118 source |
| 29e75c00c7be | 2026-08-18 | origin/agent/ai-racing-speed-119-low7-screen | Record Round 119 low-seven screen |
| 80effa093227 | 2026-08-18 | origin/agent/ai-racing-speed-119-six-ahead-moderate | Record Round 119 exact gate |
| c6a72eef6d2b | 2026-08-18 | origin/agent/ai-racing-speed-119-source-export | Record Round 119 source-export run |
| 26d21bbcfee8 | 2026-08-18 | origin/agent/ai-racing-speed-120-low-speed-ttf60 | Record Round 120 target screen |
| eae264198bb6 | 2026-08-18 | origin/agent/ai-racing-speed-120-source-export | Retry live Round 120 source export |
| 48d2843fbda0 | 2026-08-18 | origin/agent/ai-racing-speed-121-pareto-vector | Record Round 121 target screen |
| 579f4d235560 | 2026-08-18 | origin/agent/ai-racing-speed-122-trap-pareto | Record Round 122 target screen |
| 9aeaf23c945f | 2026-08-18 | origin/agent/ai-racing-speed-123-trap-diagnostic | Record trap-L2 frontier diagnostic |
| af8cbcc4056d | 2026-08-18 | origin/agent/ai-racing-speed-124-early-round-trap | Record Round 124 promotion status |
| 8f951a699b6a | 2026-08-18 | origin/agent/ai-racing-speed-125-low5-census | Record Round 125 low-five census |
| 4edb8897812a | 2026-08-18 | origin/agent/ai-racing-speed-126-equal-speed-veto | Record Round 126 promotion status |
| 96920455bda6 | 2026-08-19 | origin/agent/ai-racing-speed-127-dense-fast-funnel | Record Round 127 oracle-brake diagnostic |
| f312e06e9424 | 2026-08-18 | origin/agent/ai-racing-speed-127-z195-forensics | Record Round 127 forensic status |
| f4b85734c3b9 | 2026-08-19 | origin/agent/ai-racing-speed-129-frontier-promotion | Record Round 129 promotion status |
| 0157adae7c54 | 2026-08-19 | origin/agent/ai-racing-speed-131-point-containment-cache | Round 131: record exact gate run |
| 2fd5c5430294 | 2026-08-20 | origin/agent/ai-racing-speed-134-point-containment-cache | Round 134: record exact gate run |
| 375a4661b038 | 2026-08-19 | origin/agent/ai-racing-speed-135-finish-side-reject | Round 135: record finish probe run |
| bb0a9c8187eb | 2026-08-20 | origin/agent/ai-racing-speed-135-integer-finish-screen | Round 135: record integer-finish v2 run |
| fbab19b39c9d | 2026-08-20 | origin/agent/ai-racing-speed-136-blocked-bloom | Round 136: record blocked-Bloom screen run |
| 58655b359878 | 2026-08-20 | origin/agent/ai-racing-speed-137-mobility-workspace | Round 137: record mobility-workspace screen run |
| 019b50f03153 | 2026-08-20 | origin/agent/ai-racing-speed-138-mobility-batch | Round 138: record combined mobility screen run |
| 3e39085d6cf3 | 2026-08-20 | origin/agent/ai-racing-speed-139-counted-scratch | Round 139: record counted-scratch screen run |
| 788748bed107 | 2026-08-20 | origin/agent/ai-racing-speed-140-outside-raster | Round 140: record outside-raster screen run |
| 796d082e395b | 2026-08-20 | origin/agent/ai-racing-speed-141-forward-first-finish | Round 141: record forward-first screen run |
| 6406d57ebc0b | 2026-08-20 | origin/agent/ai-racing-speed-142-primitive-boundary-intersection | Round 142: record primitive-boundary screen run |
| 9e0cb97be99e | 2026-08-20 | origin/agent/ai-racing-speed-143-finish-edge-cache | Round 143: record finish-cache screen run |
| 38a1f8aa4aa6 | 2026-08-20 | origin/agent/ai-racing-speed-144-blocked-hash-workspace | Round 144: record exact hash screen run |
| 56bc5308b62e | 2026-08-20 | origin/agent/ai-racing-speed-145-combined-screen | Round 145: record combined screen run |
| 38bc4b65e1bc | 2026-08-20 | origin/agent/ai-racing-speed-147-magnitude-cache | Round 147: record magnitude screen run |
| 03c365458adc | 2026-08-20 | origin/agent/ai-racing-speed-148-profile | Round 148: record profile run |
| af49a95358c1 | 2026-08-20 | origin/agent/ai-racing-speed-149-path-containment | Round 149: record Path2D screen run |
| 2e2b63e74002 | 2026-08-20 | origin/agent/ai-racing-speed-150-dense-edge-cache | Round 150: record exhaustive gate run |
| 565bc628bbc6 | 2026-08-20 | origin/agent/ai-racing-speed-151-exact-integer-finish | Round 151: record integer finish screen run |
| c4ea429a1875 | 2026-08-20 | origin/agent/ai-racing-speed-152-adaptive-geometry-caches | Round 152: record adaptive-cache screen run |
| 9754b4d8950e | 2026-08-20 | origin/agent/ai-racing-speed-153-finish-side-reject | Round 153: record finish-side screen run |
| 1205bf6ffec2 | 2026-08-20 | origin/agent/ai-racing-speed-155-shared-dense-edge | Round 155: record shared dense screen run |
| 053b26ffc2bb | 2026-08-20 | origin/agent/ai-racing-speed-156-shared-dense-edge-gate | Round 156: record exhaustive gate run |
| 2899b58b5050 | 2026-08-20 | origin/agent/ai-racing-speed-157-shared-distance-map | Round 157: record shared-map gate run |
| f378502b1c4a | 2026-08-20 | origin/agent/ai-racing-speed-158-shared-legality-rasters | Round 158: record exhaustive gate run |
| c742390605f6 | 2026-08-20 | origin/agent/ai-racing-speed-159-post157-profile | Round 159: record profile run |
| 17a18ae5ddda | 2026-08-20 | origin/agent/ai-racing-speed-160-direct-blocked-bitset | Round 160: record exhaustive gate run |
| e6845c7b9747 | 2026-08-20 | origin/agent/ai-racing-speed-161-adaptive-geometry-caches | Round 161: record adaptive-cache screen run |
| e0b6018f9b27 | 2026-08-20 | origin/agent/ai-racing-speed-162-shared-point-containment | Round 162: record repaired screen run |
| 92bff6f60df1 | 2026-08-20 | origin/agent/ai-racing-speed-163-geometry-residuals | Round 163: record geometry screen run |
| cd4fba8c761c | 2026-08-20 | origin/agent/ai-racing-speed-164-ahead-occupancy-map | Round 164: record ahead-occupancy screen run |
| 047e275dddfe | 2026-08-20 | origin/agent/ai-racing-speed-165-live-occupancy-map | Round 165: record rebased live-occupancy screen |
| 27b634a4d632 | 2026-08-20 | origin/agent/ai-racing-speed-166-post160-profile | Round 166: record post-Round160 profile run |
| 308de3908499 | 2026-08-20 | origin/agent/ai-racing-speed-167-integer-finish-post160 | Round 167: record integer-finish screen run |
| b3d25da0c624 | 2026-08-20 | origin/agent/ai-racing-speed-168-combined-occupancy | Round 168: record combined occupancy screen |
| ed173ce8dd49 | 2026-08-20 | origin/agent/ai-racing-speed-169-counted-result-scratch | Round 169: record repaired counted-result screen |
| a4a8441f1860 | 2026-08-21 | origin/agent/ai-racing-speed-170-current-master-profile | Round 170: record profile run |
| 02e725ae632c | 2026-08-21 | origin/agent/ai-racing-speed-170-source-export | Round 170: record source export |
| d82865718e70 | 2026-08-21 | origin/agent/ai-racing-speed-171-projected-occupancy | Round 171: record projected occupancy gate |
| 883165d96d21 | 2026-08-21 | origin/agent/ai-racing-speed-172-finish-side-rescreen | Round 172: record finish-side rescreen |
| 3591ff664c7c | 2026-08-21 | origin/agent/ai-racing-speed-173-adaptive-point-cache | Round 173: record adaptive point-cache screen |
| 629c989289a6 | 2026-08-21 | origin/agent/ai-racing-speed-176-finish-sprint-true-confirm | Round 176: record exhaustive gate run |
| 4c1578b7df0a | 2026-08-21 | origin/agent/ai-racing-speed-176-source-export | Round 176: record source export |
