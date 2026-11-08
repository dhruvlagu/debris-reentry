# PREREG.md

Calibrated Reentry Forecasting for Uncontrolled LEO Objects. Pre-commitment record, Step 0B scope.

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

## 2. Decided in chat before any decay counts (date: [date])

- **Fleet exclusions:** large constellation payloads excluded. CubeSat fleets excluded in the main rule and included in the Test Plan C alternative rule.
- **Altitude bands:** 3 bands, measured at each horizon's issue time, used for reporting and stratification, not as a primary test factor. Band rule proposed in Section 4.
- **Maneuver filter:** exclude signatures drag cannot produce: a sustained rise in semi-major axis, or a perigee change with apogee roughly constant. Rule and constants in Section 4; sigma values to be filled.
- **Kp data cutoff** (decided after downloading the GFZ file and seeing the D flag, before any decay counts): Kp is preliminary (D=0) from 2026-10-01 to 2026-11-04. Decays after 2026-09-30 are excluded so every forecast window uses definitive Kp.

## 3. Clarifications made after seeing stage-1 counts, before any tracking data (date: [date])

These are in effect in the scripts already run. They were made after the counts, so they are labeled as post-count.

- **Name filter applies to PAYLOAD only.** The first version removed 320 IRIDIUM and 28 ORBCOMM debris objects by name. Breakup debris is uncontrolled and in scope.
- **Fleet name lists.** Constellation: STARLINK, ONEWEB, IRIDIUM, GLOBALSTAR, ORBCOMM, KUIPER, GUOWANG, QIANFAN. CubeSat fleets: FLOCK, LEMUR, DOVE, SPACEBEE. Line drawn: identical-design fleets from one operator are excluded; one-off rideshare satellites are kept. At decision time: 2,699 fleet payloads excluded, 9,592 objects remained.
- **Clusters:** cluster key = first 8 characters of INTLDES (launch id). 1993-036 and 1997-051 are merged into one cluster (2009 Cosmos 2251 and Iridium 33 collision). 1998-067 (ISS-deployed objects) is exempt from capping; each object is its own cluster.
- **Pre-pull cap:** at most 100 objects per cluster, fixed-seed random sample, seed 20261105. Result: `data/frozen/candidates.csv` (6,111 objects, 1,437 clusters).
- **Analysis cap:** at most 30 objects per cluster, applied after all filters, fixed seed. Provisional; 0C must justify or change it.
- **UNKNOWN object class (469 objects):** kept, reported as its own class.
- **Tracking-history window:** 90 days before decay through decay. Fixed now because gp_history is download-once per object.
- **Deviation:** the SATCAT raw file was pulled twice on [date] (one extra pull by an earlier script version, which also overwrote the file). The checksum was unchanged. Space-Track limits SATCAT to once per day. The script now reuses the saved file.

## 4. Proposed after inspecting decay messages, before tracking data (CONFIRM BEFORE COMMIT)

- **Labels** come from the SATCAT decay date (Space-Track PRECEDENCE 1, its most recent record type, present for every candidate). `decay_msg` is a cross-check only. TIP and 60day messages are never used as labels (using Space-Track's own forecast as ground truth would be circular in the comparison).
- **Exclude** objects whose `decay_msg` and SATCAT dates differ at all, by one or more calendar days (114 of 4,762 dual-source objects at decision time, 47 of them by 2 or more days). Reason: a 1-day mismatch means the label could be off by up to 36 hours, beyond the 7-day horizon's 16.8 hour tolerance. Count the exclusions. SATCAT-only labels are flagged single-source and tested in a sensitivity run without them.
- **Label convention check (reporting only, changes no rule):** for objects with a final TIP message, report how often the SATCAT date matches the UTC date of the last TIP predicted decay time, and the spread of the difference. The 12 hour noise statistic above stays fixed whatever this shows.
- **Date-only convention:** label = that date at 12:00 UTC, uncertainty +/- 12 hours.
- **Label-noise statistic:** worst-case half-width of the date label, 12 hours. Under the 20% rule this fails the 1-day (2.4 h) and 3-day (7.2 h) horizons and passes 7, 14, and 30 days. Planned horizons: 30, 14, 7. Revisit only through a logged amendment.
- **Space-Track comparator:** use `60day_msg`. For horizon H, take the latest message published at or before the issue time and at most 7 days earlier. Filter messages only on their own content (predicted decay between 0 and 60 days after the message epoch), never using the true decay date. Objects without a message are dropped from the comparison only. Scope caveat stated wherever the comparison appears: it covers only objects Space-Track predicted, likely biased toward larger or higher-priority objects.

- **Altitude bands:** 3 bands per horizon, edges = the 33.3rd and 66.7th percentiles of mean altitude (semi-major axis minus 6378.135 km) of the latest element set published before issue, computed per horizon over all candidates with at least one such element set, then frozen. Reason: fixed km edges fail at short horizons, where nearly every object is below 300 km. Edges are computed from feature values only, before any outcome or attrition by band is examined. Tracking retention is reported per band.
- **Provisional split dates (by date, not performance), with a 30-day embargo at each boundary:** train = decays 2015-01-01 to 2022-12-31; validation = decays 2023-01-31 to 2024-12-31; final test = decays 2025-01-31 to 2026-09-30. Decays in the 30 days after a block ends (the maximum horizon) are dropped, because their issue times fall inside the previous block, where a model fit on that block's outcomes would know the future. Limitation to state: the most extreme storm of the cycle (I believe May 2024) falls in validation, so the final test cannot check extreme-storm calibration.
- **Maneuver filter (proposed rule; fill sigma_a and sigma_p from `00b_noise_sigma.py` BEFORE the filter is run on anything):** checked over the whole 90-day window including after issue time (the question is whether decay was drag-driven), ignoring element sets in the final 3 days before decay (noise grows near decay and sigma was measured 14+ days before decay; a burn inside the last 3 days can be missed, a stated limitation). Signature A, SMA rise: flag if 3 or more consecutive element sets have semi-major axis above the running minimum of earlier sets by more than 5 x sigma_a. Signature B, burn: flag if between consecutive element sets 0.25 to 2 days apart perigee falls by more than 5 x sigma_p while apogee changes by less than 20% of that fall. sigma = 1.4826 x MAD of consecutive differences, 0.25 to 2 days apart, 14+ days before decay, pilot objects. Flagged objects are excluded and counted by signature. Constants 5, 3, 20% and 3 days are set now and varied (3 and 10 sigma) in the Step 15 sensitivity analysis. Sigma values (pilot, 148 objects, 18,862 pairs, drift removed per object): sigma_a = 0.2158 km, sigma_p = 0.2125 km, so thresholds are 1.08 km (Signature A) and 1.06 km (Signature B). First estimate, superseded because it pooled real decay drift into the spread: sigma_a = 0.4107 km, sigma_p = 0.344 km. Sigma values locked on [date].

## 5. Open items (must be filled before the step that depends on them)

- The numeric tracking requirement per altitude band (the 3-records-in-14-days minimum may need a different count per band). [Step 0B, before band retention is computed]
- Date the sigma lock in Section 4 (values already filled from `00b_noise_sigma.py`). [Step 0B, before the filter runs]
- Whether bootstrap clustering uses parent as well as week (proposal: yes, because breakup fragments decay across many weeks but share a cluster). [before 0C]
- Horizons kept after the label-noise gate. [Step 0B, expected 30, 14, 7]
- Arm 2 definition; exclusion rules and the two alternatives; density models and versions; drag coefficient assumption and range; orbit-averaging method and eccentricity cutoff; decay altitude and its mapping to decay time; ballistic-coefficient window, minimum records, poor-fit rule; hindsight definition; fixed +/-20% rule; conformal procedure and assumptions; split dates. [Steps 3 to 5]
- Final model specification. [Step 9, tag lock-v1]

## 6. Frozen inputs at the time of this draft

| File | SHA-256 |
|---|---|
| data/raw/satcat_decayed.json | 78893f9c0fba8035cc1e743f4d8cbefa1b8f0023dfc4281cf76b7ae7d849bf1e |
| data/raw/Kp_ap_Ap_SN_F107_since_1932.txt | 551a3e483130409a42ab28d971425d68084da39da1217fd99b6ec6d32264d128 |
| data/raw/decay_msgs.json | c8fac15b078f5d0bd7c2746ad71456d3db4cae93e987f4cf3006f13a9503d9cc |
| data/frozen/candidates.csv | 1fa7d208d967af44e355a86691798a34b388c5f85968334a41e44ec1926010ab |

Pull sources: Space-Track SATCAT (decays 2015-01-01 to 2026-09-30, 12,291 rows); Space-Track decay class (92,596 rows); GFZ Potsdam Kp/Ap/F10.7 file (34,682 lines, 40 header lines).
