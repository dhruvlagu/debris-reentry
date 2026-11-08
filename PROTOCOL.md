# Calibrated Reentry Forecasting for Uncontrolled Low Earth Orbit Objects

**Research Protocol (v4, aero-first)**
Category: Physical Science and Engineering. Project type: Engineering with Data Analysis.

This protocol is binding. Every threshold, rule, and metric below is written and dated before the results it governs are seen. Deviations are logged in the project notebook with date and reason. Locked items are never edited silently.

---

# Part I: Research Protocol

## 1. Summary

Thousands of dead satellites, spent rocket stages, and fragments orbit Earth with no way to steer. Atmospheric drag slowly pulls them down until they reenter. Drag depends on the air density at orbital altitude, and that density swells and shrinks with solar and geomagnetic activity (space weather). Predicting reentry is therefore a physics problem: model the drag, model the density, estimate how strongly drag acts on the object, and integrate the decay. A forecast is only as good as the weakest of those physical inputs.

**Working claim:** I built a physics-based orbit-decay model for uncontrolled objects in low Earth orbit and used held-out data to measure which physical uncertainty most limits reentry prediction at horizons of 30 days or less. I then measured whether adding space-weather information improves forecast accuracy and the calibration of prediction intervals, resolved by space-weather regime.

**Research questions**
1. **Error budget (supporting):** which physical input (atmospheric density model, space-weather forcing, or ballistic coefficient estimation) contributes most to reentry forecast error?
2. **Density model by regime (primary):** do differences between density models become meaningful under particular space-weather regimes, even if the overall effect is negligible?
3. **Space-weather value (secondary, overlaps Leonid):** does adding space-weather inputs improve short-horizon (30 days or less) forecasts over a physics baseline?
4. **Interval honesty:** are the stated prediction intervals calibrated, overall and by space-weather regime?

Data analysis is the instrument, not the subject. Frozen data, chronological held-out testing, and calibrated intervals are used to measure the physics honestly.

The claim is modest on purpose. A dominant error source, no dominant error source, improvement, no measurable improvement, and improvement only under some conditions are all valid, reportable results.

## 2. Why this matters

Reentry timing affects collision-risk planning, ground-risk warnings, and estimates of how much material burns up in the atmosphere. A forecast is only useful if its uncertainty is honest. A "90% interval" that contains the true reentry date only 60% of the time is worse than none, because people act on it. Knowing which physical input limits the forecast tells operators where better models or better space-weather prediction would pay off.

Environmental and policy motivation (orbital debris as a shared-resource problem, atmospheric effects of reentry) is context. It is not a result this project claims.

## 3. Key terms

- **TLE (two-line element set):** a public record of an object's estimated orbit, updated as it is tracked. It has an orbit epoch and a separate publication (creation) time.
- **Space-weather indices:** F10.7 (solar radio flux) and Kp/Ap (geomagnetic activity). They drive atmospheric density.
- **Atmospheric density model:** an empirical model (NRLMSIS family) that returns air density from altitude, position, time, and space-weather indices.
- **Ballistic coefficient (B):** mass divided by drag coefficient times cross-sectional area. A larger B means drag acts less on the object.
- **Issue time:** the moment a forecast is made. Only information available at or before it may be used.
- **Oracle (diagnostic) input:** an input that uses information from after the issue time. Used only to measure error sources, never reported as a forecast.
- **Coverage:** the fraction of true outcomes inside the stated interval. Three kinds are kept separate: guaranteed (under stated assumptions), observed (on the data), and expected future.
- **Conformal prediction:** a method that builds prediction intervals from past forecast errors.
- **Effective sample size:** the sample size after accounting for correlated errors. It is smaller than the raw count.

## 4. Scope

- **In scope:** uncontrolled objects (rocket bodies, debris, dead payloads) that decayed between 2015 and 2026 with sufficient terminal tracking, forecast at horizons of 30 days or less before reentry.
- **Out of scope:** controlled deorbits, active constellation satellites, maneuvering objects, objects still in orbit, ground-impact prediction, and emissions estimation.
- **Scope limit stated wherever results appear:** only objects that actually decayed are scored.

## 5. The physics of the forecast

### 5.1 Governing relations

- **Drag acceleration:** a_drag = -(1/2)(1/B) rho v_rel^2 (unit vector along relative velocity), where B = m / (Cd A), rho is air density, and v_rel is velocity relative to the rotating atmosphere.
- **Decay rate, near-circular orbit:** da/dt = -(rho / B) sqrt(mu a) (1 - r w_E cos i / v)^2, where a is semi-major axis, mu is Earth's gravitational parameter, w_E is Earth's rotation rate, i is inclination, and the bracketed factor accounts for the atmosphere co-rotating with Earth.
- **Eccentric orbits:** drag is averaged numerically around the orbit. The method and its eccentricity cutoff are recorded in Step 4.
- **Density:** rho = rho(altitude, position, time, F10.7, 81-day mean F10.7, Ap) from an NRLMSIS-family model, version recorded.
- **Forecast:** integrate the decay forward until the object reaches the decay altitude defined in Step 4. The time to reach it is the forecast remaining life.

### 5.2 Where physical uncertainty enters

| Input | Why it is uncertain | How this project handles it |
|---|---|---|
| Atmospheric density model | Empirical model with errors that can grow in disturbed conditions | Two density models compared (Test Plan D) |
| Space-weather forcing | Future F10.7 and Ap are not known at issue time | Three arms: none, realistic, observed (Step 3) |
| Ballistic coefficient | Shape, attitude, tumbling, and drag coefficient are not directly observed and can change during decay | Rolling-window estimate before issue, compared against a hindsight value (Test Plan D) |
| Orbit and eccentricity treatment | Simplified averaging can bias decay rate | Sensitivity test (Step 15) |
| Tracking data | TLEs are fitted estimates with their own noise | Label-noise gate and point-in-time rules (Step 0B) |

**Known degeneracy, stated up front:** the ballistic coefficient is fitted from observed decay using a density model, so density error is absorbed into the fitted value. Density error and ballistic coefficient error cannot be fully separated (Briden 2022; Gondelach 2017; Leonid). Refitting BC after a density swap absorbs the density difference and can make density models look equivalent by construction (see Test Plan D). The error-budget results are reported with this limit stated.

## 6. Prior work and lessons applied

### 6.1 Closest prior work

- **Leonid Space (Shambaugh, arXiv 2601.02453):** 934 deorbited objects, three scenarios that remove hindsight in stages (perfect knowledge, known weather with estimated drag, forecast weather), with probabilistic forecasts scored by CRPS and a calibration score. As I read it, it tests a single 1-year horizon, ends the forecast at a 300 km semi-major axis rather than at decay time, tunes dispersion on the same test set, reports no breakdown by space-weather regime, and keeps its ballistic-coefficient method proprietary.
- **Pardini and Anselmo (2018), IADC reentry test campaigns:** about a +/-20% window was needed for 90% confidence and about +/-30% for 95%. Targets were mostly targets of opportunity.
- **Space-Track operational predictions (TIP messages):** the operational reference. They begin only a few days before decay.
- **Conformal prediction in the space domain:** adaptive conformal inference guarantees long-run coverage under distribution shift, as I read it marginally and not conditional on regime. I found no work applying conformal prediction to reentry timing. The search was limited, so this is not proof of absence.
- **ESA and related density-model studies (Stevenson 2018; Bastida Virgili 2021; Briden 2022):** compared density models by reentry timing and found no consistently superior model near reentry. Briden used 3 objects. I found no regime-resolved comparison. Gondelach (2017) is cited via other papers, not yet read (marked per the rule below as unread until read in full).

Works I have only seen cited in another paper's bibliography are not cited here until I have read them.

### 6.2 What this project does differently

- Horizons of 30 days or less, forecasting to the actual decay time.
- Interval coverage resolved by space-weather regime.
- Density-model comparison by space-weather regime (primary); three-input error budget is supporting only, because BC-density confounding is documented (Briden 2022; Leonid; Gondelach 2017) and two contrasts overlap Leonid.
- Comparison against Space-Track predictions where they exist and against a fixed +/-20% rule.
- An open, point-in-time, reproducible evaluation. This is a supporting contribution only.
- "Space-weather forecast skill is the bottleneck" is not a headline unless this project's own data support it.

### 6.3 Amendments adopted before Step 1 (notebook, 10/30/2026)

1. Working claim narrowed as in 6.2.
2. A fixed +/-20% interval rule added as a baseline alongside Models A, B, and C.
3. Step 0C tests whether space-weather arms 1 and 2 are distinguishable by horizon, because NOAA's outlook beyond about a week relies mainly on 27-day persistence.
4. Step 0B counts Kp of 6 or more events by year and checks whether regime is confounded with solar-cycle phase.
5. Leonid Space is cited as the closest prior work.

### 6.4 A lesson from an earlier project

An earlier project of mine, on Falcon 9 landing reliability versus booster reuse, was stopped at its validation stage. Only 6 landing failures exist in 616 attempts, so the data could not answer the question, even though a feasibility check had passed on raw row counts. The lesson shaped this protocol: Step 0 tests whether the data can answer the question (event counts, effective sample size, statistical power) before any modeling begins.

### 6.5 Amendments adopted 11/03/2026 (post hoc, after the 10/30/2026 literature review)

These amendments were written post hoc on 11/03/2026, following the 10/30/2026 literature review. They are stated plainly as adopted after the review and are not backdated:
1. Replaced RQ2 with density model comparison by regime as the primary research question. Added space-weather value as RQ3 (secondary, overlaps Leonid). Renumbered interval honesty to RQ4. Removed the phrase "how much could better space-weather prediction add" across the document.
2. Added ESA and related density-model studies (Stevenson 2018; Bastida Virgili 2021; Briden 2022) to prior work (Section 6.1), noting Briden used 3 objects and no regime-resolved comparison was found; added Gondelach 2017 as cited via other papers, not yet read.
3. Updated Section 6.2 to make density-model comparison by regime primary; error budget is supporting only due to BC-density confounding (Briden 2022; Leonid; Gondelach 2017) and Leonid overlap, removing novelty claims for the error budget.
4. Updated Section 5.2 to cite BC-density confounding (Briden 2022; Gondelach 2017; Leonid) and noted that refitting BC after a density swap absorbs density differences by construction.
5. Added kill rule to Step 0A and Appendix F Step 0A (drop or narrow if a published study already answers with comparable methods), along with open verification items (Space-Track terms, historical decay messages, TIP window definitions, Leonid 0.1% spread).
6. Tiered Test Plan D contrasts into primary (density model swap by regime with BC refit vs BC frozen variants) and secondary (replication of Leonid at horizons of 30 days or less: space-weather forcing and hindsight BC), with pre-registered interaction as density by disturbed regime.
7. Relabeled Test Plan B as secondary replication of Leonid's staged-hindsight design at short horizons, removing framing of the arm 2 vs arm 3 gap as the main estimate.
8. Added Step 0C power and minimum detectable difference computation for density-by-regime contrast (variants a and b) using disturbed storm sample size. Added decision rule: if power is under 80% for the smallest meaningful difference (pre-stated at 5% in median absolute log error based on operator uncertainty scale), RQ2 is reported as descriptive only in the headline. Preserved locked 15% rule.
9. Added two pre-written headlines in Step 16 for density model differences by regime and null results.
10. Added pre-registration fields in Appendix C for primary contrast, BC-refit vs BC-frozen variants, smallest meaningful density difference, and kill rule text.
11. Updated Appendix F Step 0A requirements (full citation, date read, read-in-full vs bibliography-only, amendment list including +/-20% baseline) and Step 14 requirements (both variants a and b reported).
12. Bumped protocol header version from v3 to v4.

## 7. Design criteria and constraints

Written before any modeling.

**Criteria**
1. **Point accuracy:** median and 90th-percentile absolute error of predicted remaining time to reentry, at each horizon.
2. **Interval calibration:** observed coverage versus nominal (50% and 90%), with confidence intervals, overall and by space-weather regime.
3. **Interval sharpness:** mean interval width in days, and the interval score, which penalizes both intervals that are too wide and intervals that miss.
4. **Physical attribution:** the reduction in median absolute log error obtained by correcting each physical input in turn (density model, space-weather forcing, ballistic coefficient), with confidence intervals.

**Constraints:** public data only, no hardware, compliance with data-provider terms, computation on a laptop.

## 8. Fixed definitions and rules

**Forecast task**
- **Target:** remaining time to reentry in days, from issue time to the official decay time.
- **Horizons:** 30, 14, 7, 3, and 1 days before reentry. Any horizon failing the label-noise gate (Step 0B) is dropped.
- **Requirement:** at least 3 tracking records created in the 14 days before issue.
- **Output:** a median forecast with 50% and 90% intervals.
- **Error scale:** natural log of predicted over actual remaining time (errors grow with horizon), reported alongside absolute days.
- **Reporting:** by actual lead time and by predicted-remaining-life bin, since a real user knows only the prediction. Interval calibration groups use the predicted bin.

**Space-weather regimes (fixed now)**
- Disturbed: at least one 3-hour Kp of 6 or more in the forecast window.
- Moderate: maximum Kp of 5 to under 6.
- Quiet: maximum Kp under 5.
- Regime is recorded both for the 3 days before issue and for the window to decay.
- **Storm event:** a block of 3-hour Kp values of 6 or more, merged when separated by less than 48 hours. Counts are also reported with 12-hour and 24-hour merge windows as a sensitivity check.

**Binding rules**
1. **Point-in-time integrity:** every forecast uses only tracking records published before its issue time, and only space-weather values available at issue time for its arm.
2. **Three-way chronological split:** training, validation, final test. No random split as a primary analysis.
3. **The final test block is opened once.** Any model change afterward is a new development cycle and needs a new untouched period.
4. **No tuning on the final test.**
5. **Pre-commitment:** thresholds, regimes, exclusion rules, metrics, and split are written, dated, and version-tagged before any result that could influence them exists.
6. **Cluster-aware statistics:** confidence intervals use block bootstrap by week. Objects decaying in the same storm are not treated as independent.
7. **Paired comparisons** on identical objects and issue times.
8. **All pre-specified metrics are reported,** including unfavorable ones, with confidence intervals.
9. **Reproducibility:** frozen inputs with checksums, pinned library versions, recorded seeds, and a verified fresh-run reproduction.
10. **Every assumption traces to a sourced value** and is sensitivity-tested.
11. **Oracle inputs are diagnostics only:** perfect-foresight space weather and hindsight ballistic coefficients are labeled as such and never reported as forecast performance.

## 9. Step 0: Feasibility gate

All parts must pass before the project proceeds. Thresholds are written before results are seen. This gate tests whether the data can answer the question, not only whether data exist.

### 0A. Premise and novelty
Review published work on reentry prediction error versus horizon, atmospheric density model error, drag-based decay prediction, uncertainty quantification for reentry, and conformal prediction for time series, including Space-Track's own decay predictions as the operational reference. The review is recorded in the notebook (entry dated 10/30/2026). Its outcome is Section 6: the kill rule was partly triggered and the claim was narrowed to the part not already answered.

Combining reentry forecasting with conformal prediction is not by itself treated as a gap.

Kill rule (adopted 11/03/2026, after the 10/30 review): If a published study already answers a research question using comparable methods (held-out evaluation, calibrated uncertainty, horizon of 30 days or less, forecast to actual decay time), that question is dropped or narrowed to the part the study does not cover. If no part is left that no prior study covers, the project is not pursued in its current form. On 10/30 the first condition was met for the space-weather value question (Leonid) and the density-model comparison (ESA studies, Briden 2022), so the claim was narrowed to the regime-resolved part.
Open verification items: Space-Track redistribution terms; bulk historical decay-message availability; exact TIP window definitions; Leonid's reported 0.1% density-model spread at 28 days.

### 0B. Event counts and label quality
- Pull the object catalog and decay records, tracking history (orbit epoch and creation time), and daily and 3-hourly space-weather indices. Check whether historical NOAA 27-day outlooks are recoverable.
- **Uncontrolled filter,** fixed in advance:
  - Exclude large constellation fleets (Starlink, OneWeb, Iridium, and similar) and active payloads.
  - CubeSat fleets (for example Flock and Lemur) are excluded in the main rule and included in an alternative rule for Test Plan C.
  - Exclude objects with a maneuver signature that drag cannot produce: a sustained rise in semi-major axis, or a change in perigee with apogee roughly constant.
  - Exclude decays reported as controlled.
  - Count every exclusion.
- **Tracking-history requirement is stratified by altitude band,** because a flat requirement biases the sample toward high-altitude, low-drag objects. Three altitude bands are used, measured at each horizon's issue time. Record which objects the requirement removes and state the scope accordingly.
- Report counts by year, object class, altitude band, size, and regime, plus tracking coverage and the number of **distinct storm events** (Section 8). Count Kp of 6 or more events by year from GFZ data and check whether regime is confounded with solar-cycle phase.
- **Label-noise gate:** compare official decay times with the last tracking record. The resolution of a horizon is defined as 20% of that horizon. Drop any horizon where label noise exceeds half its resolution for more than 25% of objects.
- **Provisional thresholds** (justified or revised by 0C, with revisions logged):
  - at least 300 usable decays in total
  - after the three-way split, at least 100 in the final test block
  - at least 40 disturbed decays overall, and at least 15 in the final test block spanning at least 3 independent storms
- **If disturbed thresholds fail,** the storm analysis is reported as descriptive only. **If total counts fail,** narrow to one object class or horizon range, or switch projects.

### 0C. Power by simulation
Using only training-period data:
1. Run a crude empirical baseline and compute its errors.
2. Estimate error variance per horizon and the correlation among objects decaying in the same week. Compute the effective sample size.
3. Simulate paired baseline and candidate errors where the candidate is 10%, 15%, and 25% better, preserving the estimated correlation (also at zero and double the estimate).
4. Run the planned paired test on each simulated dataset.
5. Power is the fraction of simulations that detect the improvement at a 5% significance level.
6. Compute how precisely coverage can be measured in the disturbed regime, and whether 80% can be distinguished from 90%.
7. Test whether arms 1 and 2 are distinguishable at each horizon. If they are not, arm 2 is reported as equivalent to arm 1 at those horizons.
8. Compute the detectable size of each error-budget contrast in Test Plan D.
9. Justify, with sources, why a 15% improvement would matter for reentry forecasting.
10. Compute power and minimum detectable difference for the density-by-regime contrast, in both variants (a) and (b), using the disturbed-regime effective sample size (storms, not objects).
11. Pre-stated smallest meaningful density-model difference: 5% in median absolute log error at any horizon (paired, same objects and issue times), within a regime. Basis: Pardini and Anselmo (2018) needed about a +/-20% window for 90% confidence, so a density-model swap that shifts median error by 5% moves the forecast by a quarter of that operational uncertainty window. A smaller shift is inside the noise operators already budget for. The 5% threshold is my judgment, set before any results exist, and is not taken from a source.

Real held-out errors are never edited to manufacture power.

**Decision rule, fixed in advance:** if power is under 80% for a 15% improvement, first test whether a narrower question (one object class, or short horizons only) is detectable and worthwhile. If none is, the project is not pursued in its current form. If power for the primary density-by-regime contrast is under 80% for the pre-stated smallest meaningful density-model difference (5% in median absolute log error), RQ2 is reported as descriptive only and this is stated in the headline.

### 0D. Walking skeleton
Run the entire pipeline on about 25 objects: data pull, decay label, space-weather join, forecasts, intervals, coverage scoring. All checks must pass:
1. Every forecast uses only records published before its issue time.
2. Deleting outputs and rerunning from frozen inputs reproduces them.
3. Manual inspection of 10 objects finds no controlled objects.
4. Date and time-zone handling is verified.
5. Modeled decay for a few objects is compared against their observed altitude history as a physics sanity check.
6. Runtime is recorded to estimate full-scale cost.

### 0E. Go/no-go record
A dated verdict per part, written before Step 1: threshold, measured value, pass or fail, any narrowing of the claim, and whether the fallback is triggered.

**Fallback:** a launch-cadence simulator for Falcon 9, with its own Step 0 under the same rules. Its limitation is that model-based bottleneck findings cannot be validated as true causes.

## 10. Procedure

### Step 1: Lock the goal, forecast task, and criteria
Record Sections 7 and 8 as final, dated, before any model code.

### Step 2: Pull and freeze the dataset
Sources: Space-Track, GFZ Potsdam, and NOAA outlooks if recoverable. Log each source, query, date, and row count as pulled. Freeze with a snapshot date and checksums. Raw files are never edited. Build a point-in-time table of exactly which records and space-weather values were available for each forecast.

### Step 3: Exclusion rules and space-weather arms
Write each exclusion rule with its reasoning: controlled deorbits, ambiguous decay dates, tracking gaps beyond a set length, maneuvering payloads, fleet membership. Name two alternative rules now for Test Plan C: including CubeSat fleets, and a stricter tracking-gap tolerance.

Three arms, on the same objects and issue times:
1. **No input:** a fixed average atmosphere.
2. **Realistic input:** persistence of recent F10.7 and Ap, or NOAA's 27-day outlook if recoverable.
3. **Observed input,** labeled "perfect foresight." This is an oracle input and an upper bound, not an operational forecast.

### Step 4: Define the models
Each model is written as an equation and parameter table so another person can rebuild it.
- **Model A (empirical):** extrapolates the recent decay rate of orbital altitude from the 10 days before issue. Shows what the physics adds.
- **Model B (physics, no space-weather forcing):** integrates orbit decay under drag using the relations in Section 5.1, with an NRLMSIS-family density model (version recorded) driven by fixed inputs. Specify the orbit-averaging method, eccentricity handling, drag coefficient assumption and its sourced range, decay altitude, and how that altitude maps to the official decay time.
- **Model C (physics with space weather):** identical to B, changing only the F10.7 and Ap inputs according to the arm. B versus C isolates the effect of space weather.
- **Ballistic coefficient:** estimated in a rolling window before issue by fitting the observed decay rate. Window length, minimum record count, and handling of poorly constrained fits are specified. Tumbling can change drag over time, so poor fits are flagged and reported, not hidden.
- **Reference methods:** a fixed +/-20% interval around each model's median forecast (the benchmark conformal intervals must beat on interval score), and Space-Track predictions at horizons where they exist.

### Step 5: Interval method and data split
- **Interval method:** adaptive (rolling) conformal prediction on log-ratio errors. Standard split conformal was considered and rejected because it assumes exchangeable errors, and these errors are correlated within storms and drift with solar activity. The procedure and its assumptions are recorded.
- **Split:** training (develop), validation (compare, diagnose, redesign), final test (locked, with a disturbed period never examined in development, chosen by date and not by model performance). Dates are recorded before fitting.

### Step 6: Fit on training data only
Record the full specification: dataset snapshot and checksum, exclusion rules, split dates, variables, density model version, ballistic-coefficient window, conformal settings, library versions, seeds, and first-pass results as-is.

**Checkpoint:** compare real error variance and correlation with the Step 0C assumptions. If they differ substantially, rerun 0C before continuing.

### Step 7: Validate on the validation block (Test Plan A, Run 1)
All models, arms, and horizons: error, coverage, width, interval score, regime breakdown. Record the gap in full before cleaning anything up. Examine the 10 worst forecasts individually (tumbling, label noise, density error, tracking gaps) and label the likely physical cause of each. *Notebook: Model V1, failure, diagnosis.*

### Step 8: Redesign from the specific failure
Changes are chosen from what Step 7 showed, not decided in advance: ballistic-coefficient window, object-class split, outlier handling, density input, orbit-averaging method, interval method, or a physically justified added variable. Each change is recorded with the finding that motivated it. Refit and re-validate on validation data only, repeating until performance is defensible or a named limitation is reached.

### Step 9: Lock the final model
Freeze features, parameters, interval method, exclusion rules, horizons, and metrics in writing, dated and version-tagged.

### Step 10: Final evaluation
Run the locked model once on the final test block. Report every pre-specified metric with block-bootstrap confidence intervals, including disappointing results.

### Steps 11 to 14: Test Plans A, B, C, D
Run the four test plans in Section 11, three runs each.

### Step 15: Sensitivity analysis
1. **One factor at a time:** exclusion rule, ballistic-coefficient window, drag coefficient assumption, orbit-averaging method, interval method, disturbed-regime threshold, storm merge window.
2. **Selected interactions** chosen in advance, such as density model by disturbed regime.
3. Name the single assumption to which the conclusion is most sensitive.
4. If the data allow, a secondary test that trains on quiet periods and tests on disturbed ones. It is labeled a test of distribution shift, not of the main question.

### Step 16: Report the result
The headline is whichever statement the evidence supports. Pre-written options:
- Correcting [density model / space-weather forcing / ballistic coefficient] removed the most error: median error at horizon H fell by X% (confidence interval Z).
- No single physical input dominated; errors were spread across inputs.
- Space-weather input reduced median error at horizon H by X%, with coverage of Y% (confidence interval Z).
- Median accuracy improved, but intervals were not better calibrated.
- Coverage improved only by widening intervals; the interval score was unchanged.
- Intervals were calibrated in quiet conditions but overconfident in storms.
- Realistic inputs added little, while perfect foresight would help (only if the data support it).
- Density models differed only in [regime], by X% (CI Z), with BC refit [absorbing / not absorbing] the difference.
- No regime-resolved density-model difference detected; smallest detectable difference stated.
- No measurable improvement at this sample size, with the smallest detectable effect stated.

The project is named only after this step.

### Step 17: Application layer
Orbital Watch, my existing web application on orbital debris, displays forecasts and uncertainty bands for a selected object with the three arms side by side. This demonstrates the result. It is not part of the research.

### Step 18: Documents and defense
Research plan, notebook selection, and presentation follow the order: problem, physics, gap, data and exclusions, models, Step 7 failure, Step 8 redesign, locked final result, test plans, error budget, sensitivity, limitations, next steps.

## 11. Test plans (3 runs each)

**Test Plan A: Calibration (design criterion 2).** Three rolling-origin chronological folds on training and validation data, each trained on earlier data and tested on the next block. This gives replication without leaking future information. A random split is deliberately not used, because it hides temporal change.

**Test Plan B: Space-weather contribution (secondary, replication of Leonid's staged-hindsight design at short horizons; design criteria 1 to 3).** Same objects and issue times in three arms: none, realistic, observed. Paired differences in error, coverage, width, and interval score. Evaluates the gap between realistic and observed arms as a diagnostic replication, not as the project's main estimate.

**Test Plan C: Exclusion-rule sensitivity (design criterion 2).** The locked model under the original exclusion rule and the two alternatives named in Step 3. Report how coverage and the space-weather effect change.

**Test Plan D: Physical error budget (supporting; design criterion 4).** Three runs, one on each rolling-origin fold from Test Plan A (development data only; the final test block is used only for the locked model). In each run, contrasts are tiered as follows:

**Primary contrast:**
- **Density model swap, resolved by regime:** replace the primary density model with an alternative model, holding the arm fixed. Run two ways: (a) operational, BC refit after the swap; (b) BC frozen from the primary density model. Report both variants. Variant (a) null with variant (b) non-null means the fit hid the difference.

**Secondary contrasts (replication of Leonid at horizons of 30 days or less, to actual decay time):**
- **Space-weather forcing:** replace realistic input with observed input (arm 2 to arm 3). This is an oracle input and diagnostic upper bound, not an operational forecast.
- **Ballistic coefficient:** replace the rolling pre-issue estimate with a hindsight value fitted over the final tracking arc before decay. This is a diagnostic that uses future data and is never reported as a forecast.

For each contrast, report the reduction in median absolute log error by horizon and by regime, with block-bootstrap confidence intervals. Contrasts are not assumed to add up. The pre-chosen interaction is pre-registered as density by disturbed regime. Because the ballistic coefficient absorbs density error (Section 5.2), the hindsight ballistic coefficient is interpreted as the combined mismatch absorbed by the fitted value, not as a pure ballistic coefficient error.

## 12. Limitations

- Only objects that actually reentered are scored. Objects still in orbit are never evaluated.
- Official decay times carry label noise, especially for small debris.
- TLEs are fitted estimates, not direct measurements, and already absorb drag effects.
- Ballistic coefficient and density errors are partly confounded, so the error budget cannot separate them completely.
- The hindsight ballistic coefficient and the perfect-foresight arm are diagnostics and upper bounds, not operational results.
- Results apply to uncontrolled objects with long enough terminal tracking.
- Conformal coverage guarantees depend on stated assumptions that may fail in rare, extreme storms.
- The literature search was limited, so the gap statement is not proof that no similar work exists.

## 13. Next steps

- Extend to controlled-reentry planning and to objects with sparse tracking.
- Combine forecast reentry times with object mass to bound atmospheric material from reentry, using sourced assumptions and sensitivity testing.
- Add attitude-dependent drag for tumbling objects.
- Evaluate the locked model on a later untouched period as data accumulate.

## 14. Where each requirement is documented

| Requirement | Location |
|---|---|
| Purpose and design criteria clearly stated | Sections 1, 2, 7 |
| Physical basis of the model | Section 5, Step 4 |
| Workable and feasible | Step 0 (0B to 0D) |
| Use of others' work considered | Section 6, Step 0A |
| Testing, redesign, retest | Steps 7, 8, 10; Test Plans A to D |
| Replication and repeated testing | Section 11 (3 runs each) |
| Interpretation supported by data | Sections 8, 11; block-bootstrap intervals |
| Next steps | Section 13 |

---

# Part II: Working Appendix (operating rules and AI context)

This appendix governs how the work is carried out and how AI assistance is used.

## A. Role of AI assistance

AI tools are used for brainstorming, code review, and checking methodology. All design decisions, code execution, analysis, and interpretation are carried out and understood by me. Any AI-suggested content is verified before use.

**Rules for AI assistants working on this project**
1. Never propose using final-test data for tuning, feature choice, threshold choice, or model selection.
2. Never fabricate data, citations, counts, or results. If a number is unknown, say so and give the query or script that would produce it.
3. Always flag possible temporal leakage.
4. Treat objects decaying in the same storm as correlated, not independent.
5. Do not change any locked item. Propose a logged amendment instead.
6. Treat negative and null results as valid. Do not steer toward a headline.
7. Keep the aerospace physics primary. Do not propose replacing the physics model with a black-box model, and treat data science as the method for measuring the physics.
8. Never present oracle inputs (perfect-foresight space weather, hindsight ballistic coefficient) as forecast performance.
9. Check data-provider terms before suggesting redistribution of raw data.
10. State which Step and gate any implementation belongs to.
11. Verify libraries, API field names, and dataset schemas against current documentation.
12. Writing style: plain and direct, concise, no em dashes.

## B. Repository and notebook structure

```
/PROTOCOL.md       this file
/PREREG.md         pre-committed thresholds, rules, metrics, split dates
/CHECKSUMS.txt     SHA-256 for every frozen data file
/data/raw/         gitignored (provider terms)
/data/frozen/      parquet snapshots
/src/              numbered scripts: pull, counts, power simulation,
                   skeleton, models A/B/C, conformal, evaluation,
                   error budget
/results/          one folder per run, with specification JSON
/notebook/         dated entries
```

Git tags: `prereg-v1` (after the Step 1, 3, and 5 rules are written) and `lock-v1` (Step 9).

Notebook entry template:
```
Date:
Step:
What I did:
What I saw (as-is):
Decision and reason:
Deviation from protocol? (Y/N, details):
```

Go/no-go record template (Step 0E):
```
Date:
Part (0A / 0B / 0C / 0D):
Threshold (written before looking):
Measured value:
Pass / Fail / Narrowed claim:
If narrowed, new claim:
Fallback triggered? (Y/N):
Data problems found:
```

## C. Pre-registration fields

Filled and tagged before the step that depends on them.

```
Kill rule text:                             [Step 0A]
Uncontrolled filter, final form (fleets, CubeSats, maneuver signature):  [Step 0B]
Altitude bands and history requirement per band:        [Step 0B]
Regime thresholds (Kp):                     disturbed >= 6, moderate 5 to <6, quiet <5 (locked)
Storm event definition:                     Kp >= 6 blocks merged within 48 h; 12 h and 24 h as sensitivity (locked)
Horizon resolution and label-noise rule:    resolution = 20% of horizon; drop if noise > half of it for > 25% of objects (locked)
Horizons kept after label-noise gate:       [Step 0B]
Thresholds (total / test / disturbed):      300 / 100 / 40, with 15 in test (provisional)
Power rule:                                 >= 80% at 15% effect, else narrow or switch (locked)
Smallest meaningful density difference:     5% in median absolute log error [Step 0C]
Primary test:                               paired, block bootstrap by week, alpha 0.05
Primary contrast definition (density by regime): [Test Plan D]
BC-refit vs BC-frozen variants:             [Test Plan D]
Arm 2 definition and window:                [Step 3]
Exclusion rules and two alternatives:       [Step 3]
Density models (primary and alternative) and versions:      [Step 4]
Drag coefficient assumption and sourced range:              [Step 4]
Orbit-averaging method and eccentricity cutoff:             [Step 4]
Decay altitude and mapping to decay time:   [Step 4]
Ballistic coefficient window / min records / poor-fit rule: [Step 4]
Hindsight ballistic coefficient definition (diagnostic only): [Step 4]
Fixed +/-20% rule definition:               [Step 4]
Conformal procedure and assumptions:        [Step 5]
Split dates (train / validation / test):    [Step 5]
Final model specification:                  [Step 9, tag lock-v1]
```

## D. Stop conditions

Halt and log if any occurs:
- Final test data used before Step 9 is complete.
- A forecast found using a record published after its issue time.
- Controlled or maneuvering objects found in the scored set.
- An oracle input found in a result reported as forecast performance.
- Event-count or power thresholds fail and no narrower worthwhile question exists.
- The Step 6 checkpoint shows error structure far from the Step 0C assumptions (rerun 0C first).
- A frozen-input rerun fails to reproduce.

## E. Interview preparation

- One sentence: "I predict when dead satellites fall, find which piece of the physics limits the forecast, and test whether my error bars are honest."
- Open with the Step 7 failure and what changed in Step 8.
- Be ready to explain: the decay equation and what each term does; why drag changes with space weather; why ballistic coefficient and density are confounded; what the oracle diagnostics are and are not; why a random split was rejected; why same-storm objects are not independent; and what the power analysis would have told me if it had failed.
- Notebook pages to submit: Step 1, the Step 7 failure, one test-plan run, and the Step 15 sensitivity analysis.

## F. Required notebook content by step

Every entry uses the template in Section B and is written when the work happens, dated. Failures and surprises are recorded as seen, before any cleanup. Each entry lists the minimum content. Attach or reference the script, output file, and git commit for anything computed.

**Step 0A: Premise and novelty**
- Sources reviewed: full citation, date read, and read-in-full vs bibliography-only per source, plus one-line takeaway each.
- Closest existing approaches and what each established.
- The specific gap statement.
- Kill rule (adopted 11/03/2026, after the 10/30 review): drop or narrow if a published study already answers with comparable methods; whether it triggered on 10/30, and the narrowed claim.
- Open verification items: Space-Track redistribution terms; bulk historical decay-message availability; exact TIP window definitions; Leonid's reported 0.1% density-model spread at 28 days.
- Amendments adopted, logged before Step 1, including the fixed +/-20% baseline, and post-review amendments.

**Step 0B: Event counts and label quality**
- Each data pull: source, query or endpoint, date, row count.
- Uncontrolled filter in final form, with exclusion counts per rule (fleets, CubeSats, maneuver signature, controlled).
- Count tables by year, object class, altitude band, size, regime; distinct storm events at 12, 24, and 48 hour merge windows; Kp of 6 or more by year; solar-cycle confounding check.
- Altitude-band history requirement and which objects it removed.
- Label-noise measurement per horizon, and which horizons were kept or dropped.
- Each provisional threshold against its measured value, pass or fail, and the fail action taken.
- Whether historical NOAA 27-day outlooks are recoverable, with evidence.

**Step 0C: Power by simulation**
- Baseline used, residual SD per horizon, within-week correlation, effective sample size next to the raw count.
- Simulation design: effect sizes, correlation levels, number of simulations, seed, test used.
- Power table across effect sizes and correlations.
- Coverage precision in the disturbed regime and whether 80% versus 90% is separable.
- Arm 1 versus arm 2 distinguishability by horizon.
- Detectable size of each Test Plan D contrast.
- Sourced justification for why a 15% improvement matters.
- Decision-rule outcome, any narrowed question with its own power result, and any revision to the 0B thresholds with reason.

**Step 0D: Walking skeleton**
- The objects used and how they were chosen.
- Result of each check, pass or fail, with evidence (rerun diff, the 10 inspected objects, modeled versus observed altitude for a few objects).
- Every bug or data problem found and how it was fixed. Runtime and estimated full-scale cost.

**Step 0E: Go/no-go record**
- One filled template per part, dated before Step 1.
- Overall verdict, any narrowed claim, and whether the fallback was triggered.

**Step 1: Lock goal, forecast task, criteria**
- The four design criteria and the constraints, exactly as first drafted, dated.
- Target, horizons, error scale, reporting rules, scope limit, regime and storm definitions.

**Step 2: Pull and freeze**
- Each source logged as pulled: query, date, row count.
- Snapshot date, file list, SHA-256 checksums.
- Point-in-time table description and a spot-check of three objects showing what data each forecast could see.

**Step 3: Exclusion rules and arms**
- Each exclusion rule with its reasoning, dated before Step 6.
- The two alternative rules for Test Plan C and why they are plausible.
- Definition of each space-weather arm, including the persistence window for arm 2.
- Statement that arm 3 is an oracle input and an upper bound.

**Step 4: Define the models**
- Equations and parameter table for Models A, B, C, and the fixed +/-20% rule.
- Density models and versions, orbit-averaging method, eccentricity handling, drag coefficient assumption and sourced range, decay altitude and its mapping to the decay time.
- Ballistic-coefficient method: window length, minimum record count, poor-fit rule, and the hindsight definition used only for Test Plan D.
- What is held identical between B and C.

**Step 5: Interval method and split**
- Conformal procedure, its assumptions, and the rejected alternative with reason.
- Definitions of guaranteed, observed, and expected-future coverage.
- Split rule and exact dates for train, validation, final test, and how the untouched disturbed period was chosen (by date, not performance). Dated before Step 6.

**Step 6: Fit on training only**
- Full reproducibility spec (snapshot and checksum, rules, split, variables, versions, seeds).
- First-pass results as-is, including anything that looks off.
- Checkpoint comparison of real error variance and correlation against 0C assumptions, and whether 0C was rerun.

**Step 7: Validate (Test Plan A, Run 1). The most important entry.**
- Results for every model, arm, and horizon: error, coverage, width, interval score, regime breakdown.
- The calibration gap stated plainly, uncleaned.
- Diagnosis of the 10 worst forecasts, one line each with the likely physical cause.
- Hypothesis for why the model failed and what evidence supports it.

**Step 8: Redesign**
- For each iteration: the specific Step 7 finding, the change made, why it addresses the finding, and the refit and re-validation result.
- Candidate changes considered and rejected.
- Stopping condition: defensible performance or the named limitation reached.
- Confirmation that no final-test data was used.

**Step 9: Lock**
- The frozen specification, dated. Git tag `lock-v1` and commit hash.

**Step 10: Final evaluation**
- Date and time the final test block was opened, and confirmation it was opened once.
- Every pre-specified metric with block-bootstrap confidence intervals, favorable or not.
- Any deviation from the locked spec.

**Step 11: Test Plan A (calibration)**
- Fold boundaries per run. Coverage, width, error per run with confidence intervals.
- Spread across the three runs and what it implies about stability.

**Step 12: Test Plan B (space-weather contribution)**
- Results per arm per run, paired differences with confidence intervals.
- The arm 2 versus arm 3 gap and its interpretation.

**Step 13: Test Plan C (exclusion-rule sensitivity)**
- Object counts under each rule. Coverage and the B versus C gap under each rule.
- Whether the conclusion changed.

**Step 14: Test Plan D (physical error budget)**
- Primary density-model contrast: results reported for both variants (a) BC refit and (b) BC frozen, by horizon and regime, with block-bootstrap confidence intervals.
- Secondary contrasts (space-weather forcing and hindsight ballistic coefficient) by horizon and regime, with block-bootstrap confidence intervals.
- The pre-chosen interaction: density model by disturbed regime.
- Which physical input dominated, how the ballistic coefficient and density confounding limits that reading, and whether variant (a) null with variant (b) non-null shows that BC refit hid the density difference.
- Confirmation that the hindsight ballistic coefficient and arm 3 were used as diagnostics only.

**Step 15: Sensitivity analysis**
- One-factor-at-a-time table: factor, values tried, effect on the main result.
- The pre-chosen interaction tests and their results.
- The single assumption the result is most sensitive to, with evidence.
- Secondary distribution-shift test if run, labeled as such.

**Step 16: Headline**
- Which pre-written headline the evidence supports and the exact numbers.
- A statement of what was not established.
- Project name, with the date of naming (after this step only).

**Step 17: Application layer**
- What the Orbital Watch view shows, how it reads the frozen results, and confirmation it adds no new analysis.

**Step 18: Documents and defense**
- Research plan version and date.
- Notebook pages selected for submission: Step 1, the Step 7 failure, one test-plan run, and Step 15.
- Mock interview log: date, interviewer, questions that stumped me, revised answers.

**Deviations (any step).** Each deviation from this protocol gets its own entry: date, what changed, the reason, and which results it could affect.
