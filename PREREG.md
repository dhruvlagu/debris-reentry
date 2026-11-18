# PREREG.md

Calibrated Reentry Forecasting for Uncontrolled LEO Objects. Pre-commitment record, Steps 0B and 0C.

**How to read this file.** A rule counts as pre-committed only from the date of the git commit that contains it. Rules are grouped by when they were decided, so a reader can see which were set before any data and which were clarified after seeing counts. Nothing here is edited silently. Changes go in a new dated section at the bottom.

Status: DRAFT. Fill every `[date]`. Confirm or edit Section 4 and Section 5 before committing.

---

## 1. Locked in PROTOCOL.md (Nov 3 version), before any data

- **Regimes:** disturbed = at least one 3-hour Kp of 6 or more in the window; moderate = max Kp 5 to under 6; quiet = max Kp under 5. Recorded for the 3 days before issue and for the window to decay.
- **Storm event:** Kp >= 6 blocks merged when separated by less than 48 hours. Counts also reported at 12 and 24 hours.
- **Horizon resolution and label-noise rule:** resolution = 20% of the horizon. Drop a horizon if label noise exceeds half the resolution for more than 25% of objects.
- **Provisional thresholds:** at least 300 usable decays total; at least 100 in the final test block; at least 40 disturbed overall; at least 15 disturbed in the final test block spanning at least 3 independent storms.
- **Power rule:** at least 80% power for a 15% improvement, else narrow the question or switch projects.
- **Primary test:** paired, block bootstrap by week, alpha 0.05.
- All binding rules in PROTOCOL.md Section 8 apply (point-in-time integrity, three-way chronological split, final test opened once, no tuning on final test).

## 2. Decided in chat before any decay counts (date: 11/04/2026)

- **Fleet exclusions:** large constellation payloads excluded. CubeSat fleets excluded in the main rule and included in the Test Plan C alternative rule.
- **Altitude bands:** 3 bands, measured at each horizon's issue time, used for reporting and stratification, not as a primary test factor. Band rule proposed in Section 4.
- **Maneuver filter:** exclude signatures drag cannot produce: a sustained rise in semi-major axis, or a perigee change with apogee roughly constant. Rule and constants in Section 4; sigma values to be filled.
- **Kp data cutoff** (decided after downloading the GFZ file and seeing the D flag, before any decay counts): Kp is preliminary (D=0) from 2026-10-01 to 2026-11-04. Decays after 2026-09-30 are excluded so every forecast window uses definitive Kp.

## 3. Clarifications made after seeing stage-1 counts, before any tracking data (date: 11/05/2026)

These are in effect in the scripts already run. They were made after the counts, so they are labeled as post-count.

- **Name filter applies to PAYLOAD only.** The first version removed 320 IRIDIUM and 28 ORBCOMM debris objects by name. Breakup debris is uncontrolled and in scope.
- **Fleet name lists.** Constellation: STARLINK, ONEWEB, IRIDIUM, GLOBALSTAR, ORBCOMM, KUIPER, GUOWANG, QIANFAN. CubeSat fleets: FLOCK, LEMUR, DOVE, SPACEBEE. Line drawn: identical-design fleets from one operator are excluded; one-off rideshare satellites are kept. At decision time: 2,699 fleet payloads excluded, 9,592 objects remained.
- **Clusters:** cluster key = first 8 characters of INTLDES (launch id). 1993-036 and 1997-051 are merged into one cluster (2009 Cosmos 2251 and Iridium 33 collision). 1998-067 (ISS-deployed objects) is exempt from capping; each object is its own cluster.
- **Pre-pull cap:** at most 100 objects per cluster, fixed-seed random sample, seed 20261105. Result: `data/frozen/candidates.csv` (6,111 objects, 1,437 clusters).
- **Analysis cap:** at most 30 objects per cluster, applied after all filters, fixed seed. Provisional; 0C must justify or change it.
- **UNKNOWN object class (469 objects):** kept, reported as its own class.
- **Tracking-history window:** 90 days before decay through decay. Fixed now because gp_history is download-once per object.
- **Deviation:** the SATCAT raw file was pulled twice on 11/05/2026 (one extra pull by an earlier script version, which also overwrote the file). The checksum was unchanged. Space-Track limits SATCAT to once per day. The script now reuses the saved file.

## 4. Proposed after inspecting decay messages, before tracking data (CONFIRM BEFORE COMMIT)

- **Labels** come from the SATCAT decay date (Space-Track PRECEDENCE 1, its most recent record type, present for every candidate). `decay_msg` is a cross-check only. TIP and 60day messages are never used as labels (using Space-Track's own forecast as ground truth would be circular in the comparison).
- **Exclude** objects whose `decay_msg` and SATCAT dates differ at all, by one or more calendar days (114 of 4,762 dual-source objects at decision time, 47 of them by 2 or more days). Reason: a 1-day mismatch means the label could be off by up to 36 hours, beyond the 7-day horizon's 16.8 hour tolerance. Count the exclusions. SATCAT-only labels are flagged single-source and tested in a sensitivity run without them.
- **Label convention check (reporting only, changes no rule):** for objects with a final TIP message, report how often the SATCAT date matches the UTC date of the last TIP predicted decay time, and the spread of the difference. The 12 hour noise statistic above stays fixed whatever this shows.
- **Date-only convention:** label = that date at 12:00 UTC, uncertainty +/- 12 hours.
- **Label-noise statistic:** worst-case half-width of the date label, 12 hours. Under the 20% rule, 1-day (2.4 h) and 3-day (7.2 h) horizons fail. At 7 days, 25.2% of objects exceed tolerance, above the 25% threshold, so 7 days is dropped. Retained horizons: 30 and 14 days. Revisit only through a logged amendment.
- **Space-Track comparator:** use `60day_msg`. For horizon H, take the latest message published at or before the issue time and at most 7 days earlier. Filter messages only on their own content (predicted decay between 0 and 60 days after the message epoch), never using the true decay date. Objects without a message are dropped from the comparison only. Scope caveat stated wherever the comparison appears: it covers only objects Space-Track predicted, likely biased toward larger or higher-priority objects.

- **Altitude bands:** 3 bands per horizon, edges = the 33.3rd and 66.7th percentiles of mean altitude (semi-major axis minus 6378.135 km) of the latest element set published before issue, computed per horizon over all candidates with at least one such element set, then frozen. Reason: fixed km edges fail at short horizons, where nearly every object is below 300 km. Edges are computed from feature values only, before any outcome or attrition by band is examined. Tracking retention is reported per band.
- **Split dates (by date, not performance), with a 30-day embargo at each boundary:** train = decays 2015-01-01 to 2022-12-31; validation = decays 2023-01-31 to 2024-12-31; final test = decays 2025-01-31 to 2025-12-31. The final test ends in 2025 because tle2026 is unpublished. Decays in the 30 days after a block ends are dropped, because their issue times fall inside the previous block, where a model fit on that block's outcomes would know the future. Limitation to state: the most extreme storm of the cycle (I believe May 2024) falls in validation, so the final test cannot check extreme-storm calibration.
- **Maneuver filter (proposed rule; fill sigma_a and sigma_p from `00b_noise_sigma.py` BEFORE the filter is run on anything):** checked over the whole 90-day window including after issue time (the question is whether decay was drag-driven), ignoring element sets in the final 3 days before decay (noise grows near decay and sigma was measured 14+ days before decay; a burn inside the last 3 days can be missed, a stated limitation). Signature A, SMA rise: flag if 3 or more consecutive element sets have semi-major axis above the running minimum of earlier sets by more than 5 x sigma_a. Signature B, burn: flag if between consecutive element sets 0.25 to 2 days apart perigee falls by more than 5 x sigma_p while apogee changes by less than 20% of that fall. sigma = 1.4826 x MAD of consecutive differences, 0.25 to 2 days apart, 14+ days before decay, pilot objects. Flagged objects are excluded and counted by signature. Constants 5, 3, 20% and 3 days are set now and varied (3 and 10 sigma) in the Step 15 sensitivity analysis. Sigma values (pilot, 148 objects, 18,862 pairs, drift removed per object): sigma_a = 0.2158 km, sigma_p = 0.2125 km, so thresholds are 1.08 km (Signature A) and 1.06 km (Signature B). First estimate, superseded because it pooled real decay drift into the spread: sigma_a = 0.4107 km, sigma_p = 0.344 km. Sigma values locked on 11/07/2026.
- **Signature B dropped (documented 11/16/2026, Amendment 30):** the amended Signature B (`src/00b_stepB.py`: 3-set medians, 5 sigma, 20% apogee ratio, last 3 days skipped, max window gap 3 days; step SDs SIG_SP = 0.4036 km for perigee and SIG_SA = 0.4809 km for apogee, locked 2026-11-07) was run on 163 pilot objects. Debris false-positive rate: 14 of 77 = 18.2%, against the pre-set criterion of 5% or less, so Signature B is dropped. By type: payload 5 of 53 (9.4%), rocket body 0 of 14, unknown 0 of 19. [FILL: confirm whether these 163 are the same pilot set as the 148 objects used for the original sigma.] The single-pair Signature B rule in the bullet above is superseded and was not applied to the scored set. Only Signature A was applied, to near-circular objects. Perigee-lowering burns are not screened, and some payload flags (5 of 53) are unresolved. Both are stated limitations. Scored counts are unchanged.

## 5. Open items (must be filled before the step that depends on them)

- Sigma lock dated 11/07/2026 (Section 4). Done.
- Correlation and effective-sample-size estimates for the week/storm and parent-cluster structures. [Step 0C; design recorded in Section 7]
- Arm 2 definition; exclusion rules and the two alternatives; density models and versions; drag coefficient assumption and range; orbit-averaging method and eccentricity cutoff; decay altitude and its mapping to decay time; ballistic-coefficient window, minimum records, poor-fit rule; hindsight definition; fixed +/-20% rule; conformal procedure and assumptions. [Steps 3 to 5]
- Final model specification. [Step 9, tag lock-v1]

## 6. Frozen inputs at the time of this draft

| File | SHA-256 |
|---|---|
| data/raw/satcat_decayed.json | 78893f9c0fba8035cc1e743f4d8cbefa1b8f0023dfc4281cf76b7ae7d849bf1e |
| data/raw/Kp_ap_Ap_SN_F107_since_1932.txt | 551a3e483130409a42ab28d971425d68084da39da1217fd99b6ec6d32264d128 |
| data/raw/decay_msgs.json | c8fac15b078f5d0bd7c2746ad71456d3db4cae93e987f4cf3006f13a9503d9cc |
| data/frozen/candidates.csv | 1fa7d208d967af44e355a86691798a34b388c5f85968334a41e44ec1926010ab |

*Added 11/17/2026 after 0C and 0D:*

| File | SHA-256 |
|---|---|
| data/frozen/modelA_train.parquet | 519df726d31ca9943760be4885c50faa9ff143b62d8e80e678ac7a56771e2f23 |
| data/frozen/tle_merged_dupfilt.csv | 32a99648ff0ba6635baaaf424bf48adfaef42cbd464e2cca02a6ed4fb1a7b897 |
| data/frozen/tle_merged.csv | 6410b187f232af3ad225288d24a322bd3b0cba5aad9afce0c9a9d031d3abab65 |
| data/frozen/pilot_ids.csv | 8326d10001f61ed35d5219472945adb2f86cc3df914963abb5d1080621c49420 |
| results/0d/selection.json | 2b91de55d63f6aa89ed0036ce201dbd783fafd179738e87072266e8a999072c8 |
| results/0c_stress/stress_results.csv | 3f24ff97788c6229f55d7bf2c0c27294575a78a1c5e24c70dee4fb618cc3aac1 |
| results/0c_stress/spec.json | 2a10b62a67fc708ba7969be522cf3bb182fe0bf83ff4d524939e4c886d13c809 |
| src/00c_stress.py | 6ba32f2fa8c6a53f3382cae0702fba5f9b69a5980399671e440a4ef158c44cbe |

Pull sources: Space-Track SATCAT (decays 2015-01-01 to 2026-09-30, 12,291 rows); Space-Track decay class (92,596 rows); GFZ Potsdam Kp/Ap/F10.7 file (34,682 lines, 40 header lines).

## 7. Step 0B outcomes and Step 0C pre-registration (11/13/2026)

### Step 0B outcomes

- **Horizons:** retain 30 and 14 days only. At 7 days, 25.2% of objects exceed the 16.8-hour tolerance, above the locked 25% limit, so drop 7 days. The 3-day and 1-day horizons fail the 12-hour label-noise check and are removed.
- **Threshold results:** all reported thresholds pass at both retained horizons. Thresholds are at least 300 total, at least 100 test, at least 40 disturbed overall, and at least 15 disturbed test objects spanning at least 3 independent storms.

| Horizon | Total | Test | Disturbed overall | Disturbed test | Test storms | Result |
|---|---:|---:|---:|---:|---:|---|
| 30 d | 3,332 | 559 | 1,788 | 327 | 13 | Pass |
| 14 d | 3,468 | 564 | 1,110 | 240 | 12 | Pass |

At 30 days, the largest single storm contains 70 disturbed test objects. Storm counts, not object counts, govern precision for disturbed-regime coverage. The 0B counts are recorded in `results/0b_regimes_L24.txt`; the full label-noise gate is in `results/0b_gate_full_L24.txt`.

### Step 0C design, before any 0C result

- **Baseline:** minimal Model A, extrapolating orbital decay rate from the 10 days before issue, as in Protocol Step 4. For eccentricity > 0.01, fit on perigee-altitude rate rather than exclude; report results stratified by eccentricity. Outlier handling uses the Theil-Sen estimator. `flag_jump` from `00b_merge.py` is not used in the primary fit because it is computed from neighbors on both sides, including records published after issue time, violating Rule 1. A run with flagged records dropped is reported as a non-causal diagnostic only.
- **0C stand-in baseline (amendment 22, 11/14/2026):** training errors of frozen Model A have median log error about 1.8 (overprediction near 6x), so a 15% relative improvement against raw Model A is trivially detectable and says nothing about B versus C or Test Plan D. The primary 0C simulation uses Model A errors with the per-horizon training median subtracted; spread, correlation, and tails are preserved. Raw Model A is reported as an optimistic bound. Model A itself is not changed. The Step 6 checkpoint compares real model errors with these assumptions and may force a 0C rerun.
- **Effect statistic:** relative reduction in median absolute log(predicted/actual) error, per horizon, computed on paired objects and issue times: 100 x (baseline median - candidate median) / baseline median.
- **Test:** paired bootstrap resampled by both week and parent cluster, at least 2,000 simulations, seed 20261114. Candidate improvements: 10%, 15%, and 25%. An improvement counts as detected only if both tests reject at one-sided alpha = 0.05. The locked power rule remains at least 80% power for a 15% improvement.
- **0C test and generator (amendment 23, 11/14/2026):** a smoke run showed centered Model A errors are heavy-tailed (median absolute log error 0.25, SD 1.2) and parent-cluster ICC is 0.74 to 0.86, so a Gaussian generator and week-only bootstrap would misstate power. The primary 0C simulation uses an empirical-quantile generator and the paired bootstrap resampled by both week and parent cluster; an improvement counts as detected only if both reject at one-sided alpha = 0.05. Week-only and Gaussian runs are reported as sensitivities.
- **Correlation grid:** 0x, 1x, and 2x the training estimate.
- **Variance-inflation grid:** 1x, 2x, and 3x the training residual SD. Training is quiet (mean F10.7 88.0; 1.7% of days have Kp >= 6) while test is disturbed (mean F10.7 151.7; 6.0% of days have Kp >= 6). Estimate all primary quantities from training only. Training-only estimates are expected to be optimistic; the supplied test-regime summaries are context for this sensitivity grid, not estimates of variance or forecast performance. Because the grid was motivated in part by test-block summaries, this is a possible test-informed-design concern.
- **Dependence structures:** same-week/same-storm and same-parent-cluster. The parent-cluster sample has 1,437 clusters with a 30-object cap. Effective n uses the larger design effect. Residual SDs, correlations, design effects, and effective n are unknown until computed from training data. `src/00c_power.py` is present in the worktree; the script's one-sided alpha 0.05 and dual (week + parent cluster) bootstrap were used for 0C power under Amendment 23; the locked rule gives alpha 0.05 and week block bootstrap with no sidedness; the choices are post hoc; the real-data Step 10 test must be fixed by amendment before Step 6.
- **Coverage precision:** use storm-level n_eff. If 80% and 90% coverage are not separable at that n_eff, report disturbed-regime coverage as descriptive only, following the Protocol 0B fail action.
- **Calibration data:** primary estimates use training data only. Validation data may be used only for a separately labeled ICC sensitivity, under logged Amendment 29. It is not used to calibrate variance or tune a model.
- **Items 7 and 8 order dependency:** use simulation-only with stated assumed effects for the initial 0C run. Rerun arm 1 versus arm 2 distinguishability and Test Plan D detectable sizes after Step 4 Models B/C exist, and log that rerun as a deviation. Arm distinguishability measured on the quiet training block does not transfer to the test block.
- **15% justification:** a 15% relative reduction in median absolute log error is the prespecified effect size for power planning and is my judgment of operational relevance, not a result in the paper. Pardini and Anselmo (2018, *J. Space Saf. Eng.* 5(1), 46-62): abstract, highlights, and introduction only; full text is paywalled. [READ IN FULL: N] Their percentage error of residual lifetime is predicted/true remaining time - 1, which maps to my log error through log(1 + percentage error). They report a mean error of about 10% and a +/-20% window needed for 90% confidence (+/-25% in the last two days, +/-30% for 95%) from campaigns starting about 10 to 15 days before re-entry, so they provide no evidence at my 30-day horizon. If window width scales with typical error, a 15% error reduction would narrow a 90% window from +/-20% to about +/-17%, or from +/-2.8 days to +/-2.4 days at 14 days. Their targets were targets of opportunity predicted by one team, so transfer to a population that is about 60% debris is not established.
- **TIP feasibility:** among candidate-associated TIP messages in `data/raw/decay_msgs.json`, the empirical content lead is 0 to 7 days for 7,556 of 7,562 nonnegative predictions (99.92%), calculated as `DECAY_EPOCH - MSG_EPOCH`. Space-Track's official [TIP class definition](https://www.space-track.org/basicspacedata/modeldef/class/tip/format/html) lists `MSG_EPOCH`, `DECAY_EPOCH`, and `WINDOW`; its [API help](https://www.space-track.org/documentation) says the final TIP may be polled every 10 minutes when reentry is within 12 hours. The docs do not specify a general 7-day forecast window. Using only message publication and predicted-decay times, the latest prior TIP predicting decay after issue exists for one training object at each retained horizon and none in validation or test. Drop the TIP comparison: there is no eligible test-block overlap. This availability check uses issue times derived from labels and is a post hoc feasibility diagnostic, not a model result; possible temporal leakage is flagged below.
- **Test Plan C tight-label sensitivity:** include the sensitivity subset whose last element set is within 24 hours of the label. This is a post-issue selection criterion, so it is for sensitivity reporting only, never a forecast filter, feature, or tuning input. Flag the possible temporal leakage and report the subset counts.
- **0C results:** primary run 11/14 to 11/16/2026, seed 20261114, 2,000 sims per condition. Summary in the go/no-go record below. Uneven-effect stress test run and closed under D6.

### Carried-forward amendment record

These entries are carried forward from PROTOCOL.md Section 6.5, dated 11/03/2026:

9. Added pre-written Step 16 headlines for density-model differences by regime and null results.
10. Added Appendix C fields for the primary contrast, BC-refit and BC-frozen variants, smallest meaningful density difference, and kill-rule text.
11. Updated Appendix F Step 0A source-review and amendment requirements, and Step 14 variant reporting.
12. Bumped the protocol header to v4.

The flat tracking rule now applies uniformly across altitude bands, with per-band retention reporting, as recorded in PROTOCOL.md Sections 8 and 9.0B. The flat tracking rule is recorded as Amendment 19 (cross-referenced as Amendment 28). PROTOCOL.md Section 6.5 Amendment 11 is a different change.

### Step 0C go/no-go record

Date: 11/16/2026
Part: 0C
Threshold (written before looking): At least 80% power for a 15% improvement.
Measured value: 0.904 to 1.000 at 30 days, 0.972 to 1.000 at 14 days (minimum observed power 0.904 at 30 days and 0.972 at 14 days)
Pass / Fail / Narrowed claim: Pass on the 15% rule at both retained horizons, including under uneven effects (D6: minimum power 0.892 at 30 d, 0.950 at 14 d). Items 7, 8, 10 remain deferred (D1, D2). Pass is relative to centered Model A errors and must be re-checked at the Step 6 checkpoint. Narrowed: disturbed-regime coverage descriptive only.
If narrowed, new claim: Disturbed-regime coverage descriptive only; interval-calibration claims limited to overall, quiet, and moderate regimes.
Fallback triggered? (Y/N): N
Data problems found: Model A overprediction (median log error 1.85 at 30 d, 1.86 at 14 d) required centered stand-in baseline; 79 rows excluded by 10-day fitting window; eccentric objects (29.2% at 30 d, 25.6% at 14 d) and ISS-prefixed clusters (14.9% at 30 d) overrepresented in training; parent-cluster ICC strong (normal-score ICC 0.356 at 30 d, 0.522 at 14 d); storm-level coverage underpowered (13 storms SE 0.083 power 0.370 at 30 d; 12 storms SE 0.087 power 0.357 at 14 d); items 7, 8, 10 not run pending Models B/C; uneven-effect stress test closed (D6).

### Step 0D record (11/16/2026)

Selection: 25 training-block objects at the 30 d horizon, seed 20261116, `src/00d_select.py`, `results/0d/selection.json` (sha256 2b91de55d63f6aa89ed0036ce201dbd783fafd179738e87072266e8a999072c8). Quota minimums set before any check: ISS cluster 3, rocket body 3, eccentric 5, debris 5, remainder random. Result: 9 eccentric, 6 ISS cluster, 13 debris, 7 payload, 5 rocket body; status ok 21, cap 4, floor 0, UNKNOWN 0.
Check 1 (point-in-time, independent refit): pass. 48 object-horizon rows checked (2 of 50 absent from the parquet as insufficient). Smallest margin between record availability and issue time 0.11 h (must be at least 0). Independent refit matched the frozen parquet on every row.
Check 2 (rerun): pass. Script rerun identical. `00c_build_modelA.py` rerun from frozen inputs reproduced the full parquet (2,696 rows).
Check 3 (controlled or maneuvering): [FILL: Dhruv sign-off after viewing inspect10.png and flagged6.png]. Seeded 10 inspected: 32020, 39395, 31790, 37885, 51543, 46090, 40363, 38085, 40359, 42800. See D8.
Check 4 (dates, time zones): pass. Labels at 12:00 UTC, issue time equals label minus horizon exactly, 25 of 25 decay dates match the SATCAT DECAY field, TLE epochs naive and sorted, none after the decay label by more than 1 day.
Check 5 (altitude sanity): [FILL: Dhruv sign-off]. Observed: the Model A fit follows the 10-day window and lies above the accelerating decay curve, as expected for a straight-line fit. 32020 (e = 0.261) is capped: perigee is flat while decay is apogee-driven. Last-TLE-to-label gaps above 72 h: 50647 (82.8 h), 42697 (75.4 h), 21622 (74.0 h), carried to the Step 7 review.
Check 6 (runtime): refit 1.0 ms per object-horizon, about 3 s per horizon at full scale. Refit only; excludes the physics model and conformal.
Verdict: [FILL: pass, narrowed, or fail]. Scope per D7.

### Deviations (Steps 0C and 0D)

D1. 11/16/2026. Items 7 and 8 not run (no Models B/C), rerun after Step 4. Reason: Models B and C have not yet been built, so arm 1 versus arm 2 distinguishability and Test Plan D detectable effect sizes cannot be measured. Results affected: initial 0C MDE estimates rely on simulated effects against the centered Model A stand-in; arm distinguishability and Test Plan D sensitivity remain unmeasured until after Step 4.
D2. 11/16/2026. Item 10 (density-by-regime power, variants a and b, 5% threshold) not run, [DECIDE: defer with D1]. Reason: requires Models B and C across density models and BC refit/frozen variants. Results affected: RQ2 headline power evaluation deferred.
D3. 11/16/2026. One-sided alpha and dual bootstrap are post hoc. Reason: adopted under Amendment 23 following smoke-run error tails and cluster ICC; conflicts with the locked rule of alpha 0.05 week block bootstrap with no sidedness specified. Results affected: simulated 0C power decisions; final evaluation test rule must be reconciled by amendment before Step 6.
D4. 11/17/2026. ICC conflict resolved. The smoke run quoted the raw-error parent-cluster ICC (0.741 at 30 d, 0.865 at 14 d, recomputed 11/17/2026). The primary and stress runs use the normal-score ICC (0.356, 0.522), which matches the median-based effect statistic and the empirical-quantile generator. Raw-scale clustering is much stronger, plausibly from heavy tails including constant cap and floor errors (not isolated). Normal-score values govern. Results affected: none.
D5. 11/17/2026. Variance-inflation grid (1x, 2x, 3x) registered but not run. [DECIDE: accept or reject this reason: the effect statistic is a ratio of medians and the bootstrap is ratio-based, so multiplying all errors by a constant leaves power unchanged. Non-multiplicative shifts, such as heavier tails or a different eccentric mix in the test block, are not tested.] Flagged test-informed. Results affected: sensitivity of power to a quiet-training vs disturbed-test variance shift is not measured.
D6. 11/16 to 11/17/2026. Uneven-effect stress test, run and closed. `src/00c_stress.py` (standalone reconstruction of the 0C generator, training data only, seed 20261114, 2,000 sims per condition, 199 resamples, both week and parent-cluster bootstrap must reject, one-sided alpha 0.05). Scenarios and decision rule set before the run: null; uniform 15% (control); 30% in a random half of parent clusters; same by decay week; 25% on eccentric objects with the rest set to average 15%; 0% on eccentric objects with about 21% on near-circular. The 30% and 25% concentrations are my choices, not sourced. A 200-sim smoke run preceded the full run; nothing was changed after it. Grid: baseline-candidate correlation 0.3, 0.6, 0.9; shared-effect multiplier 0, 1, 2. Result: minimum power across non-null scenarios 0.892 at 30 d and 0.950 at 14 d (rule: at least 0.80); false-alarm rate at most 0.038; realized effects 14.8 to 16.3%. Control (uniform) minimum 0.892 and 0.950 vs 0C 0.904 and 0.972, so this generator is slightly more conservative than `00c_power.py` at the weakest corner. Cluster ICCs reproduced the notebook (0.356 at 30 d, 0.522 at 14 d); week ICCs 0.139 and 0.158. Outputs: results/0c_stress/stress_results.csv and spec.json. Limits: scenarios are mild (no gain concentrated in a few clusters); power is relative to centered Model A errors, not Model B or C; test-block regime and eccentric mix are not simulated. Results affected: the 0C go/no-go Pass is no longer provisional on this item.
D7. 11/16/2026. 0D walking skeleton ran Model A plus a fixed +/-20% interval only, on 25 training objects. Conformal (Step 5) and physics Models B and C (Step 4) do not exist. Check 5 uses Model A's altitude fit, not a drag integration. Reason: those components are built after 0D in protocol order. Results affected: the 0D physics sanity check is incomplete until rerun with Model B after Step 4. The 25 objects contain no floor-status and no UNKNOWN-class objects, so those paths are untested.
D8. 11/17/2026. 0D check 3 cross-check used the original single-pair Signature B rule and flagged 6 of 25 objects (debris: 21622, 44467, 40068, 44325; rocket body: 40363; payload: 39395). Plots showed no persistent perigee step. A local rate z-score (hit rate against the median and MAD of 10 neighboring records on each side) gave z < 3 for 26 of 30 hits, including every hit on 21622, 40068, 39395 and 44325. Four hits on two objects had z of 3.4 or more: 40363 (z 7.9, one 1.39 km fall) and 44467 (z 5.1, 3.7, 3.4, including two 6.6 km falls 10 days apart). 44467 is breakup debris and cannot maneuver; 40363 is a rocket body, unresolved, one small event. None judged a maneuver. Probable reason for the flags (inference, not tested): the rule compares raw perigee falls to a sigma computed after drift removal. The amended rule had already failed its criterion (Amendment 30). Informational. Results affected: nothing in the scored set.

### New amendments

13. 11/13/2026. Recorded the 0B horizon gate outcome: 30 and 14 days retained, 7 days dropped at 25.2% over tolerance versus the locked 25% limit, and 3 and 1 days removed. Reason: apply the measured label-noise gate. Could affect usable counts, power, and horizon-level conclusions.
14. 11/13/2026. Shortened the final test end date to 2025-12-31 because tle2026 is unpublished; retained the stated train and validation dates and 30-day embargo. Could affect test counts, storm coverage, and precision.
15. 11/13/2026. Pre-registered the Step 0C simulation design and left unresolved choices marked [DECIDE]. Reason: set the analysis before any 0C result exists. Could affect power, detectable effects, and coverage precision.
16. 11/13/2026. Added the TIP-overlap feasibility check and fallback. Reason: 7 days was dropped and overlap at retained horizons is unknown. Could affect whether a Space-Track comparison is reported and its eligible sample.
17. 11/13/2026. Added the tight-label sensitivity subset to Test Plan C with a post-issue-selection warning. Reason: carry forward the specified sensitivity run without allowing it to influence forecasting. Could affect sensitivity-set counts and interpretation.
18. 11/14/2026. Resolved the Step 0C baseline, eccentric-object treatment, effect statistic, seed, calibration data rule, and simulation-only handling for items 7 and 8. Reason: record the user's decisions before 0C results. Could affect power, detectable effects, and ICC sensitivity estimates.
19. 11/14/2026. Clarified flat tracking minimum and per-band retention reporting in the protocol, preserving the existing 3-record/14-day threshold. Reason: align conflicting protocol sections. Could affect object retention by band, not the threshold itself.
20. 11/14/2026. Derived TIP content lead and point-in-time overlap from `data/raw/decay_msgs.json` and checked Space-Track's TIP class definition and API help. Reason: resolve comparator feasibility without assuming a window. Could affect whether a TIP comparison is reported; the check used label-derived issue times and is a possible temporal-leakage deviation.
21. 11/14/2026. Clarified Model A outlier handling and excluded `flag_jump` from the primary fit because it uses post-issue records; flagged-record dropping is non-causal diagnostic only. Reason: preserve Rule 1 point-in-time integrity. Could affect primary-fit specification and diagnostic interpretation.
22. 11/14/2026. Added the centered Model A error distribution as the Step 0C simulation stand-in, with raw Model A as an optimistic bound and a Step 6 checkpoint against real model errors. Reason: prevent trivial detectability from Model A's large training median error from being mistaken for evidence about B versus C or Test Plan D. Could affect simulated power and require a 0C rerun.
23. 11/14/2026. Replaced the week-only/Gaussian Step 0C power assumptions with an empirical-quantile generator and a paired bootstrap by week and parent cluster, requiring both tests to reject. Reason: smoke-run error tails and parent-cluster ICC make simpler assumptions unreliable. Could affect power and whether improvements count as detected.
24. 11/14/2026. Expanded the 15% power-planning justification with the limited Pardini and Anselmo (2018) review, its applicability limits, and an explicitly hypothetical 14-day operational-width calculation. Reason: distinguish project judgment from literature evidence and make the relevance argument transparent. Could affect interpretation of the chosen effect size, but does not change it.
25. [FILL: original adoption date from notebook 11/12/2026 entry; renumbered 11/16/2026]. Retained TLE records that lack checksums (short records, mostly 2015 to 2020). Reason: excluding them would remove most historical tracking data from 2015 to 2020. Overlap checks against checksum-valid copies: 99.01 to 99.74% identical; 653 of 120,488 overlapping pairs differed, 540 substantially. On conflict the checksum-valid record is kept, which does not independently establish its correctness. Could affect tracking counts and label timing.
26. [FILL: original adoption date; renumbered 11/16/2026]. Excluded 510 objects decaying in 2026 from the in-scope candidates (5,601 retained, 2015 to 2025). [FILL: reason as written in the notebook]. Could affect test block size and candidate counts.
27. [FILL: original adoption date; renumbered 11/16/2026]. Duplicate-removal rule restricted to objects with eccentricity at or below 0.01. Reason: the original near-circular noise threshold was invalid for eccentric orbits (297 duplicate groups with orbital-element spreads up to 26,451 km). The revised rule removed 111 additional rows without changing scored-object counts. Could affect TLE counts for eccentric objects only.
28. 11/16/2026. Cross-reference: PROTOCOL.md Sec 6.6 item 13 (renumbered to 28), the flat 3-record tracking minimum applies in every altitude band with retention reported by band. Same change as Amendment 19, recorded under both numbers because the two files were renumbered separately. No numeric change.
29. 11/16/2026. Kept primary 0C estimates training-only and permitted validation data only for a separately labeled ICC sensitivity, with no calibration or tuning (PROTOCOL.md Sec 6.6 item 14, renumbered to 29). Reason: avoid number collision with PREREG Amendment 14. Could affect ICC sensitivity reporting only.
30. 11/16/2026. Recorded that Signature B was dropped after failing its pre-set debris false-positive criterion, and that the scored set used Signature A only. Reason: this file still listed Signature B as active, and `src/00b_stepB.py` cites a nonexistent "PREREG Amendment 1". Documentation only, no counts changed. [FILL: date `00b_stepB.py apply` was first run].
