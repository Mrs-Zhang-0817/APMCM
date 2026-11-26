# Reconstructing Converter Flame Spectra and Forecasting Delayed Flue-Gas Measurements

## Summary

Flame spectra and flue-gas measurements describe the same steelmaking process on different time scales. We used records from ten converter heats to reconstruct the observed signals, examine the delay between oxygen supply and gas response, and test whether spectra could forecast gas measurements in a previously unseen heat.

We screened isolated spectral observations against their neighbours in time and wavelength and reconstructed the surface on each heat's native wavelength grid. Across 10,000 withheld interior observations that passed quality screening, the pooled mean absolute error (MAE) was 100.05 W/cm² and the root mean squared error was 153.22 W/cm². For offline process analysis, we reconstructed cumulative oxygen consumption with a monotone piecewise cubic curve and obtained oxygen flow from its derivative. Replacing the original flow estimate shifted the location of 90 of 100 candidate correlation peaks across heat, gas and process groups. The inferred delays depend on the flow reconstruction. The available records do not independently identify gas transport time.

All ten heats were scored by leave-one-heat-out validation using the revised gas labels. With spectra alone, history lowered the ten-heat 10 s forecast MAE for CO from 14.03 to 13.38 m³/s and improved eight heats. CO₂ MAE rose from 4.00 to 4.04 m³/s despite improvements in eight heats. When oxygen-supply and process history were available, the matched comparison scored from 30 s showed a small average CO improvement, from 5.736 to 5.671 m³/s, with improvements in three heats. CO₂ MAE rose from 2.828 to 3.047 m³/s. Paired heat-resampling intervals included zero for all four comparisons. The gains from adding spectra to process history were inconsistent across the ten heats.

**Keywords:** converter steelmaking, spectral reconstruction, flue gas, time delay, leave-one-heat-out validation


## Contents

1. Observations and study design
2. Reconstructing the flame spectrum
3. Reconstructing oxygen supply and estimating gas delay
4. Predicting gas readings in an unseen heat
5. Conclusions
6. Appendix: heat-level results and figures

## 1. Observations and study design

A flame spectrum is available at the converter mouth before the corresponding flue gas can reach the analyzer. Both instruments report at the nominal interval of 0.5 s. This makes the forecasting question precise: given measurements through time t, what analyzer reading can be predicted at t + 10 s in a heat whose gas labels have never been used for training? The forecast horizon is fixed by the evaluation design. The physical transport delay must be assessed separately.

Each attachment supplies a sequence number, 2,047 spectral channels, cumulative oxygen volume and two gas measurements. We assign time zero to the first sample. The four B-series heats cover 340.535–1027.963 nm and the six C-series heats cover 339.390–1023.303 nm. We retain the native axes for reconstruction and use common physical wavelengths for prediction. The gas columns are labelled concentration in the files; we follow the problem's definition of instantaneous volumetric flow in m³/s. Integrating these values gives volume in m³.

The organizer revised the gas readings for heat 6B03205. All 1,479 revised time points pass the label-quality screen. The sequence, wavelengths, spectral intensities and cumulative oxygen readings match the original file exactly. The original file is archived. The process analysis and all current forecast comparisons use the revised ten-heat dataset. Heat 6C02057 spans 387 s under the nominal sampling interval. Its timestamps cannot be independently verified, so it retains its original duration throughout the analysis.

## 2. Reconstructing the flame spectrum

At each interior point we compare intensity with its four nearest neighbours along the time and wavelength axes. A candidate impulse must lie outside the neighbouring range and differ from the neighbour median by more than max(1000, 8 × 1.4826 × MAD), where MAD is the median absolute deviation of the neighbours. We exclude clipped observations from the donor set. A flagged point is interpolated between valid bracketing wavelengths in its own frame, using their measured wavelength coordinates. Where that bracket is unavailable, we seek a temporal bracket in the same channel. The offline screen uses the next frame and is reserved for reconstruction.

The screen repaired 47 points across the ten heats. Figure 1 shows why local structure matters. At 551.5 s and 764.966 nm in 6B03205, the observed intensity of 21,003 exceeded the neighbouring maximum of 19,676; the same-frame estimate was 19,562.83 W/cm². A peak of 21,773 W/cm² at 732.0 s and 588.751 nm had support in adjacent measurements and was retained. Eight heats reached the recorded ceiling of 65,535. True intensities above that ceiling remain unknown.

![Examples of an isolated impulse and a retained peak](../q1_q2/results/spectral_windows.png)

*Figure 1. Local spectral intensity in heat 6B03205 before and after offline screening and repair. The circles mark the isolated observation at 551.5 s and 764.966 nm (top) and the retained peak at 732.0 s and 588.751 nm (bottom). Each row uses identical time and wavelength coordinates and a shared intensity scale in W/cm². Full surfaces are in Appendix 6.2.*

Between consecutive time and wavelength nodes, the reconstructed intensity is the weighted sum of four corner values with weights (1−a)(1−b), (1−a)b, a(1−b) and ab. Here a and b are the fractional positions along time and wavelength. Each surface retains all native nodes; a 121 by 181 display grid keeps the ten figures comparable. Peak heights should be read on the native grid.

For validation, we held out 1,000 screened interior observations per heat using seed 20261126. A row-and-column spacing rule kept held-out points apart. The reconstruction was repeated after masking these values, with the test observations excluded as donors. The pooled errors over 10,000 points were 100.05 W/cm² (MAE) and 153.22 W/cm² (RMSE). These errors quantify interpolation of isolated, otherwise ordinary observations. Extended gaps and true heights of clipped peaks remain untested.

## 3. Reconstructing oxygen supply and estimating gas delay

We screened oxygen and gas records for negative or nonfinite values. A gas impulse was eligible for repair when both neighbouring readings agreed within 0.2 m³/s and the centre differed from both by at least 3 m³/s in the same direction. The screening rules yielded no eligible replacements in the three process series. Repeated cumulative oxygen readings followed by increments made single-step flow estimates sensitive to the recording pattern.

We anchored a monotone piecewise cubic Hermite curve to cumulative oxygen readings at 5.5 s intervals and both endpoints. Its derivative gives the offline lance flow estimate. In 6C02057 the maximum raw single-step flow was 109.82 m³/s; the reconstructed peak on the 0.1 s display grid was 19.78 m³/s. Integrating the quadratic derivative over each segment recovered the observed end-to-start oxygen change to within 4.55 × 10⁻¹³ m³ across heats. Trapezoidal integration on the display grid gave a maximum absolute discrepancy of 0.0398 m³. These checks establish volume closure; independent instantaneous flow measurements were unavailable.

We joined successive gas observations linearly and accumulated their trapezoidal areas from zero at the first observation. The revised 6B03205 record yields cumulative volumes of 9,350.400 m³ of CO₂ and 24,869.075 m³ of CO. The respective ten-heat medians were 9,746.095 m³ and 20,341.269 m³. In 6B03270 the correlations of cumulative oxygen with instantaneous CO₂ and CO were −0.020 and 0.930, respectively. With cumulative CO₂ and CO volumes they were 0.993 and 0.967. Shared growth over time contributes to the latter correlations, limiting their use as evidence of reaction efficiency.

![Measured and reconstructed oxygen supply near the largest cumulative-volume deviation in heat 6C02057](../q1_q2/results/oxygen_window.png)

*Figure 2. Oxygen-supply reconstruction in heat 6C02057 near 376 s. The upper panel compares recorded and reconstructed cumulative oxygen volume (m³). The lower panel compares raw interval differences and the derivative of the fitted curve (m³/s). Both panels use the same time window. The ten full six-panel figures are in Appendix 6.3.*

For candidate delay estimation we compared 5 s changes in smoothed flow with later gas changes, scanning 0–40 s in 0.5 s steps and maximizing the absolute Pearson correlation. We grouped observations using source-time flow terciles and examined process halves and alternative smoothing windows. Across the ten heats, the trailing-flow estimate gave shorter high-flow delays in eight heats for CO₂ and three for CO. The CO delays tied in one heat. Replacing trailing flow with reconstructed flow shifted 90 of 100 candidate peaks. The reconstructed-flow estimates gave shorter high-flow delays in nine heats for CO₂ and one for CO, with two CO ties. For revised 6B03205 the low- and high-flow CO₂ estimates were 40.0 and 2.5 s, and the CO estimates were 0.0 and 7.5 s (Table A2). The 40.0 s and 0.0 s estimates reach scan boundaries. The direction of the association depends on the gas, and the inferred offsets depend strongly on signal processing.

## 4. Predicting gas readings in an unseen heat

We used leave-one-heat-out validation over all ten scored heats. Each test heat was excluded from training, standardization, ensemble weight selection and lag estimation. The nine remaining heats supplied supervision. Inputs use current and past measurements only. We integrate spectra in 16 bands over 341–1023 nm. Spectral-history features summarize trailing observations. Process-history inputs include elapsed time, cumulative oxygen and backward flow estimates. The ridge-based joint ensemble combines static, historical and lag-augmented fusion. Its weights are chosen for each gas and horizon using only the training heats.

Table 1 scores identical analyzer target times from 10 s for concurrent estimates and 10 s ahead forecasts. MAE is computed within each heat and averaged equally across the ten heats. At the 10 s horizon the joint ensemble achieved MAEs of 3.04 m³/s for CO₂ and 5.50 m³/s for CO. The process-history model achieved 2.80 and 5.54 m³/s.

| Model | Concurrent CO₂ | Concurrent CO | 10 s ahead CO₂ | 10 s ahead CO |
|---|---:|---:|---:|---:|
| Training mean | 3.98 | 16.82 | 3.98 | 16.82 |
| Current spectrum | 4.06 | 14.13 | 4.00 | 14.03 |
| Spectral history | 4.21 | 13.48 | 4.04 | 13.38 |
| Process history | 2.83 | 5.52 | 2.80 | 5.54 |
| Joint ensemble | 3.06 | 5.48 | 3.04 | 5.50 |

*Table 1. Heat-averaged MAE in m³/s on common target timestamps.*

With spectra alone, spectral history lowered the CO MAE by 0.645 m³/s and improved eight heats. For CO₂, eight heats improved, but the heat-averaged error increased by 0.047 m³/s. Heat 6C02058 had the largest CO₂ deterioration, at 3.312 m³/s. This comparison uses two complete predictors whose transformations and ridge penalties differ. In a controlled check from target time 30 s, both models used the same 16-band input and ridge penalty of 10, and the history model also used trailing 5, 10 and 20 s features. CO MAE fell from 13.957 to 12.527 m³/s and CO₂ MAE rose from 3.666 to 3.718 m³/s. Nested selection over history windows and ridge penalties yielded 12.321 m³/s for CO and 3.662 m³/s for CO₂.

The paired process-history comparison uses 12,989 heat–time combinations from 30 s onward. Both models used the same targets, training weights and ridge penalty. Adding spectra reduced the CO MAE from 5.736 to 5.671 m³/s and improved three heats. It increased the CO₂ MAE from 2.828 to 3.047 m³/s and improved seven heats. The 95% percentile intervals from resampling the ten paired heat differences include zero for both gases and both comparisons in Figure 3. These intervals describe sensitivity across the observed heats. They do not establish performance on a new plant.

![Two paired comparisons of heat-averaged MAE for 10 s ahead CO₂ and CO forecasts](figures/forecast_comparisons.png)

*Figure 3. Paired comparisons of 10 s ahead forecasts across ten scored heats. Panel (a) compares current spectra with spectral history at targets from 10 s. Panel (b) compares process history with and without spectra at targets from 30 s. Each connector joins models evaluated on the same targets for that gas. Vertical scales differ between panels. Table A3 reports the differences by heat, and Figure A21 shows the full joint-ensemble forecasts.*

Within-frame interpolation of clipped channels changed every heat-level gas MAE by less than 0.00018 m³/s. For the lag comparison, at least two training heats had to support a candidate offset, and the estimated offset had to exceed 10 s to add an earlier spectral feature. CO₂ triggered the rule in all ten folds, with training-only offsets of 30, 32 or 34 s. Its MAE rose from 3.047 to 3.064 m³/s. CO never met the support rule and used the unadjusted predictor in all ten folds.

For a separate check on heat 6B03205, we scored the joint-ensemble predictions saved before the revised gas labels were released. On 1,459 target times from 10 s, the frozen forecasts gave MAEs of 3.194 m³/s for CO₂ and 9.157 m³/s for CO. These scores are reported separately from the ten-heat refit.

## 5. Conclusions

Spectral history lowered the average CO forecast error when only spectra were available. The CO₂ average did not improve, even though most heats showed a small reduction. When oxygen-supply and process history were available, adding spectra produced a small average CO gain concentrated in three heats and a higher average CO₂ error. Weak and processing-sensitive correlation peaks limit the interpretation of candidate delays. The results quantify prediction of delayed analyzer readings in this dataset. Clipped peak heights, in-bath gas composition and transfer to other plants require independent measurements.

## 6. Appendix: heat-level results and figures

### 6.1 Heat-level tables

Table A1 links each native-grid reconstruction and six-panel process figure to its heat-specific holdout errors. Intensities follow the units stated in the problem.

| Heat | Held-out points | MAE (W/cm²) | RMSE (W/cm²) | Spectrum | Process |
|---|---:|---:|---:|---|---|
| 6B03205 | 1000 | 65.89 | 96.90 | [Surface](../q1_q2/results/spectra/6B03205.png) | [Six signals](../q1_q2/results/process/6B03205.png) |
| 6B03206 | 1000 | 96.09 | 141.25 | [Surface](../q1_q2/results/spectra/6B03206.png) | [Six signals](../q1_q2/results/process/6B03206.png) |
| 6B03270 | 1000 | 78.16 | 117.31 | [Surface](../q1_q2/results/spectra/6B03270.png) | [Six signals](../q1_q2/results/process/6B03270.png) |
| 6B03271 | 1000 | 84.98 | 127.73 | [Surface](../q1_q2/results/spectra/6B03271.png) | [Six signals](../q1_q2/results/process/6B03271.png) |
| 6C02057 | 1000 | 119.18 | 181.19 | [Surface](../q1_q2/results/spectra/6C02057.png) | [Six signals](../q1_q2/results/process/6C02057.png) |
| 6C02058 | 1000 | 92.89 | 148.91 | [Surface](../q1_q2/results/spectra/6C02058.png) | [Six signals](../q1_q2/results/process/6C02058.png) |
| 6C02059 | 1000 | 112.13 | 168.77 | [Surface](../q1_q2/results/spectra/6C02059.png) | [Six signals](../q1_q2/results/process/6C02059.png) |
| 6C02060 | 1000 | 111.77 | 167.08 | [Surface](../q1_q2/results/spectra/6C02060.png) | [Six signals](../q1_q2/results/process/6C02060.png) |
| 6C02107 | 1000 | 116.96 | 176.16 | [Surface](../q1_q2/results/spectra/6C02107.png) | [Six signals](../q1_q2/results/process/6C02107.png) |
| 6C02108 | 1000 | 122.45 | 181.41 | [Surface](../q1_q2/results/spectra/6C02108.png) | [Six signals](../q1_q2/results/process/6C02108.png) |

*Table A1. Heat-level spectral interpolation errors at 1,000 withheld interior observations per heat.*

Table A2 gives candidate delays (seconds) for the low and high flow groups using the reconstructed flow. Positive offsets place the analyzer response later than its source. Peaks at 0 and 40 s reach the scan boundaries.

| Heat | CO₂ low | CO₂ high | CO low | CO high |
|---|---:|---:|---:|---:|
| 6B03205 | 40.0 | 2.5 | 0.0 | 7.5 |
| 6B03206 | 40.0 | 29.5 | 1.5 | 29.5 |
| 6B03270 | 40.0 | 0.0 | 0.0 | 40.0 |
| 6B03271 | 40.0 | 39.5 | 31.5 | 36.0 |
| 6C02057 | 39.0 | 4.0 | 40.0 | 30.0 |
| 6C02058 | 40.0 | 7.5 | 1.5 | 2.0 |
| 6C02059 | 0.0 | 5.0 | 0.0 | 5.0 |
| 6C02060 | 40.0 | 2.0 | 0.0 | 0.0 |
| 6C02107 | 40.0 | 7.5 | 0.0 | 0.0 |
| 6C02108 | 36.0 | 14.0 | 22.0 | 28.0 |

*Table A2. Heat-level candidate delays by source-time flow group, in seconds.*

Table A3 reports the two comparisons shown in Figure 3 for each scored heat. Each difference is the MAE of the augmented model minus the MAE of its paired baseline. Negative values indicate lower error. Within each comparison, both models use the same target times and the count applies to each gas.

| Heat | Targets from 10 s | Spectral history ΔMAE, CO₂ | Spectral history ΔMAE, CO | Targets from 30 s | Added spectra ΔMAE, CO₂ | Added spectra ΔMAE, CO |
|---|---:|---:|---:|---:|---:|---:|
| 6B03205 | 1459 | +0.26 | +0.58 | 1419 | −0.179 | +0.596 |
| 6B03206 | 1291 | −0.46 | −0.44 | 1251 | −0.192 | +0.776 |
| 6B03270 | 1393 | −0.32 | −2.22 | 1353 | −0.042 | +0.517 |
| 6B03271 | 1400 | −0.03 | −0.50 | 1360 | +0.175 | +0.226 |
| 6C02057 | 755 | −0.62 | −0.65 | 715 | +2.056 | −3.275 |
| 6C02058 | 1323 | +3.31 | +2.74 | 1283 | +1.613 | +0.808 |
| 6C02059 | 1535 | −0.53 | −2.30 | 1495 | −0.447 | −0.075 |
| 6C02060 | 1353 | −0.34 | −2.63 | 1313 | −0.087 | +0.326 |
| 6C02107 | 1439 | −0.35 | −0.32 | 1399 | −0.124 | +0.206 |
| 6C02108 | 1441 | −0.45 | −0.72 | 1401 | −0.584 | −0.753 |

*Table A3. Paired differences in 10 s ahead MAE (m³/s). Spectral history is compared with the current spectrum. Added spectra are compared with process history alone.*

| Heat | Forecast targets | Scored targets | CO₂ MAE (m³/s) | CO MAE (m³/s) |
|---|---:|---:|---:|---:|
| 6B03205 | 1459 | 1459 | 3.19 | 9.16 |
| 6B03206 | 1291 | 1291 | 1.94 | 5.63 |
| 6B03270 | 1393 | 1393 | 2.43 | 5.73 |
| 6B03271 | 1400 | 1400 | 2.04 | 4.79 |
| 6C02057 | 755 | 755 | 9.46 | 9.69 |
| 6C02058 | 1323 | 1323 | 4.41 | 3.59 |
| 6C02059 | 1535 | 1535 | 2.06 | 4.76 |
| 6C02060 | 1353 | 1353 | 1.54 | 3.40 |
| 6C02107 | 1439 | 1439 | 2.01 | 2.95 |
| 6C02108 | 1441 | 1441 | 1.27 | 5.32 |

*Table A4. Joint-ensemble 10 s ahead forecasts and MAEs at target times from 10 s. Counts apply to each gas.*

### 6.2 Full spectral surfaces

Figures A1–A10 show each surface over its recorded time and wavelength ranges. The display grid samples the native-grid reconstruction at 121 time positions and 181 wavelengths. All panels use the same intensity range, 0–65,535 W/cm².

![Reconstructed flame spectrum for heat 6B03205](../q1_q2/results/spectra/6B03205.png)

*Figure A1. Reconstructed flame spectrum for heat 6B03205.*

![Reconstructed flame spectrum for heat 6B03206](../q1_q2/results/spectra/6B03206.png)

*Figure A2. Reconstructed flame spectrum for heat 6B03206.*

![Reconstructed flame spectrum for heat 6B03270](../q1_q2/results/spectra/6B03270.png)

*Figure A3. Reconstructed flame spectrum for heat 6B03270.*

![Reconstructed flame spectrum for heat 6B03271](../q1_q2/results/spectra/6B03271.png)

*Figure A4. Reconstructed flame spectrum for heat 6B03271.*

![Reconstructed flame spectrum for heat 6C02057](../q1_q2/results/spectra/6C02057.png)

*Figure A5. Reconstructed flame spectrum for heat 6C02057.*

![Reconstructed flame spectrum for heat 6C02058](../q1_q2/results/spectra/6C02058.png)

*Figure A6. Reconstructed flame spectrum for heat 6C02058.*

![Reconstructed flame spectrum for heat 6C02059](../q1_q2/results/spectra/6C02059.png)

*Figure A7. Reconstructed flame spectrum for heat 6C02059.*

![Reconstructed flame spectrum for heat 6C02060](../q1_q2/results/spectra/6C02060.png)

*Figure A8. Reconstructed flame spectrum for heat 6C02060.*

![Reconstructed flame spectrum for heat 6C02107](../q1_q2/results/spectra/6C02107.png)

*Figure A9. Reconstructed flame spectrum for heat 6C02107.*

![Reconstructed flame spectrum for heat 6C02108](../q1_q2/results/spectra/6C02108.png)

*Figure A10. Reconstructed flame spectrum for heat 6C02108.*

### 6.3 Full process curves

Figures A11–A20 show lance flow, cumulative oxygen volume, CO₂ and CO flows, and their cumulative volumes. Flow is in m³/s and volume is in m³. Time zero marks the first recorded observation. Each panel extends to the end of its own heat. Vertical limits vary by heat and signal.

![Six reconstructed process signals for heat 6B03205](../q1_q2/results/process/6B03205.png)

*Figure A11. Reconstructed process curves for heat 6B03205 using the organizer's revised CO₂ and CO measurements.*

![Six reconstructed process signals for heat 6B03206](../q1_q2/results/process/6B03206.png)

*Figure A12. Reconstructed process curves for heat 6B03206.*

![Six reconstructed process signals for heat 6B03270](../q1_q2/results/process/6B03270.png)

*Figure A13. Reconstructed process curves for heat 6B03270.*

![Six reconstructed process signals for heat 6B03271](../q1_q2/results/process/6B03271.png)

*Figure A14. Reconstructed process curves for heat 6B03271.*

![Six reconstructed process signals for heat 6C02057](../q1_q2/results/process/6C02057.png)

*Figure A15. Reconstructed process curves for heat 6C02057. The observed record spans 387 s.*

![Six reconstructed process signals for heat 6C02058](../q1_q2/results/process/6C02058.png)

*Figure A16. Reconstructed process curves for heat 6C02058.*

![Six reconstructed process signals for heat 6C02059](../q1_q2/results/process/6C02059.png)

*Figure A17. Reconstructed process curves for heat 6C02059.*

![Six reconstructed process signals for heat 6C02060](../q1_q2/results/process/6C02060.png)

*Figure A18. Reconstructed process curves for heat 6C02060.*

![Six reconstructed process signals for heat 6C02107](../q1_q2/results/process/6C02107.png)

*Figure A19. Reconstructed process curves for heat 6C02107.*

![Six reconstructed process signals for heat 6C02108](../q1_q2/results/process/6C02108.png)

*Figure A20. Reconstructed process curves for heat 6C02108.*

### 6.4 Full joint-ensemble forecast traces

![Analyzer readings and 10 s ahead joint-ensemble forecasts for all ten held-out heats](../q3/results/predictions_10s.png)

*Figure A21. Analyzer readings and 10 s ahead joint-ensemble forecasts for all ten revised heats. The horizontal axis shows analyzer target time and the vertical axis shows volumetric gas flow (m³/s). Each column uses a common vertical scale across heats. Heat 6B03205 is scored using the revised measurements. Table A4 reports the heat-level errors.*
