# Manuscript revision proposals

Date: 2026-09-27. These are reviewable proposals, not edits to the authoritative manuscript. The original DOCX remains untouched. Approval of a research decision authorizes technical correction; it does not mean the researcher has accepted this exact manuscript prose. No proposal is marked resolved merely because it is written here.

The manuscript was read directly from `C:/Users/redlo/Downloads/BRPM_Documentation (2).docx`: 292 XML paragraphs including all three tables, references, and eight embedded diagrams. It contains an introductory chapter and Chapter 2; no separate completed results chapter was present. Paragraph IDs below refer to `reconciliation/manuscript_extracted.txt`, not unstable Word page numbers. Text extraction retains table paragraphs; all eight embedded figures were inspected visually and preserved in `reconciliation/manuscript_media/`. The extraction is not a rendered-layout proofread. External literature was not exhaustively authenticated.

Original SHA-256: `420b3e867ad9afe2ba4f1515696c7349bb72406a15ed42194d6cf6c9633a34ce`.

## Exact text proposals

Where an entry covers multiple paragraphs, the replacement is consolidated prose: place it in the primary section and remove or harmonize duplicated claims rather than copying identical paragraphs repeatedly. Original statements below are full extracted paragraphs, so the review remains independently traceable.


### M01: P0003, P0011

**Original P0003:** Time Series Forecasting of Reportable Infectious Disease Trends in Public School Settings Across Antipolo City (2016 – 2025)

**Original P0011:** Time Series Forecasting of Reportable Infectious Disease Trends in Public School Settings Across Antipolo City (2016–2026)

**Proposed replacement:** Time Series Forecasting of Reportable Infectious Disease Case Counts among Individuals Aged 5–19 in Antipolo City: Implications for Public-School Preparedness (Historical Period: 2016–2025)

**Reason:** Distinguishes population and intended benefit from school-acquired cases; resolves title dates. A new title needs author/adviser approval.

**Evidence:** Handoff §§3.1, 3.2; original titles P0003/P0011; workbook period 2016–2025.

**Approval/application status:** Awaiting researcher/adviser decision on title; historical period correction supported by source. Original not changed.


### M02: P0014, P0016, P0033

**Original P0014:** Because these outbreaks tend to follow recognizable seasonal and cyclical patterns rather than occurring at random, they are well-suited to time series forecasting methods. In particular, the Seasonal Autoregressive Integrated Moving Average (SARIMA) model has been shown to be effective in capturing the seasonal and climate-driven behavior of tropical infectious diseases (Warnasekara et al., 2022), including dengue (Olana et al., 2025) and measles (Parreño, 2025) trends in the Philippine setting. This study applies SARIMA and NNAR modeling to ten years (2016–2025) of monthly reported dengue, leptospirosis, and measles cases in Antipolo City, spanning the pre-pandemic, pandemic, and post-pandemic periods, in order to move beyond retrospective case reporting toward a data-driven, predictive approach that can support local health authorities in early outbreak preparedness.

**Original P0016:** Reportable infectious diseases are illnesses that must be reported to health authorities, as required by Republic Act No. 11332, also called the Mandatory Reporting of Notifiable Diseases and Health Events of Public Health Concern Act. This law requires the Department of Health to monitor and respond to reportable diseases, including new or returning infectious diseases and outbreaks, to help identify and treat them early. This study targets the Dengue, Leptospirosis, and Measles affecting children of school age in Antipolo City that are monitored by the Department of Health's surveillance system. Although they spread in different ways, they all tend to increase quickly in areas with problems such as crowded living conditions, poor drainage, and weak community health systems.

**Original P0033:** This study aims to analyze the temporal dynamics in the number of Dengue, Leptospirosis, and Measles affecting children of school age in Antipolo City, from January 2016 to December 2025. Furthermore, the study will create a combined SARIMA-NNAR forecasting model that is embedded in an online epidemiologic dashboard.

**Proposed replacement:** This study proposes city-wide monthly forecasting for individuals aged 5–19 in Antipolo City to inform public-school preparedness. The provisional disease categories are Dengue, Leptospirosis, and Measles-Rubella; final coverage and classification await CHO verification and researcher/adviser approval. Existing all-age surveillance records are retained only for separately labeled technical evaluation and do not establish performance for the approved population.

**Reason:** School age, source eligibility, and provisional disease coverage must be explicit.

**Evidence:** Handoff §§3.1–3.4; DATA_RECONCILIATION.md.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M03: P0035, P0037

**Original P0035:** To develop a hybrid SARIMA-NNAR forecasting model, using 10 years (2016–2025) of historical Antipolo City disease data, that identifies seasonal patterns and predicts Dengue, Leptospirosis, and Measles case spikes up to 12 months ahead, validated against real-world case data.

**Original P0037:** To provide advanced and disease-specific 12-month forecasts through the dashboard that support timely resource and supply mobilization ahead of anticipated case peaks. 

**Proposed replacement:** Develop and evaluate a disease-specific hybrid SARIMA–NNAR forecasting pipeline using eligible historical records. Maintain a provisional 12-month forecast capability while the CHO interview determines the operational usefulness of 1-, 3-, or 12-month horizons. Evaluate forecast error against observed holdout case counts and live SARIMA-only and seasonal-naive benchmarks.

**Reason:** Retains approved horizon capability without prematurely finalizing operational objectives or promising validated accuracy.

**Evidence:** Handoff §§3.7–3.8; pipeline evaluation windows.

**Approval/application status:** Awaiting researcher/adviser approval of objective wording; horizon remains awaiting CHO confirmation. Original not changed.


### M04: P0026, P0040, P0043, P0079

**Original P0026:** By applying both SARIMA and NNAR to Antipolo City’s past health records, this research shifts the local government's approach from simply reacting to outbreaks to actively anticipating them. Accurate, data-driven forecasts will give the City Health Office valuable lead time to plan. With early warnings, health officials can prepare hospital beds, launch mosquito-control operations, and schedule targeted vaccination drives months before an outbreak peaks. Ultimately, using these predictive models will help reduce the severe impact of infectious diseases on the community.

**Original P0040:** The findings of this study can be used to produce data-driven seasonal disease forecasts, providing health administrators with the information needed to prevent outbreaks from spreading within schools. Furthermore, this study is conducted to benefit the following:

**Original P0043:** For the students and teachers in Antipolo City public schools, the system’s seasonal disease forecast can reduce their risk of exposure to these diseases by giving the school administrators and the health authorities the time and information needed to implement preventive measures for the school ahead of the predicted disease surges.

**Original P0079:** This study will develop a forecasting method using ten years of monthly data for dengue, leptospirosis, and measles in Antipolo City. It then uses that past pattern to estimate what each illness may do in the coming year. This plan is meant to help the Antipolo City Health Office and the people in charge of schools act earlier. They can line up hospital bed needs, plan mosquito control steps, and set up vaccination efforts ahead of any rise in cases. The focus is on getting ready before an outbreak is already in progress.

**Proposed replacement:** The dashboard is intended to support preparedness discussions by displaying forecast monthly case counts. Resource allocation, intervention selection, outbreak prevention, and reductions in exposure are potential downstream uses to be evaluated by health authorities; the prototype does not perform or demonstrate those outcomes.

**Reason:** Operational benefits are intentions, not implemented allocation or measured health outcomes.

**Evidence:** dashboard/ui/layout.py; dashboard/callbacks/view_callbacks.py; handoff §14.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M05: P0041, P0042

**Original P0041:** For the local government of Antipolo City and its Health Office, the system provides seasonal disease forecasts that can anticipate seasonal surges of Dengue, Leptospirosis, and Measles affecting the city's pediatric demographic based on historical disease data. The time series analysis of the seasonal disease trends can be used to produce forecasts and support the local government in planning, making data-driven decisions, providing interventions, and coordinating responses with the health authorities.

**Original P0042:** For school administrators in Antipolo City, the system can provide advance forecasts of possible surges of Dengue, Leptospirosis, and Measles affecting the city's pediatric demographic, which can be used to coordinate with health authorities and implement preparations.

**Proposed replacement:** The intended beneficiaries include the Antipolo City Health Office and school administrators. Eligible forecasts concern the city-wide population aged 5–19, without asserting public-school enrollment or the location of transmission. All-age technical evaluations are labeled separately.

**Reason:** Pediatric terminology is not the approved 5–19 definition; school membership is unavailable.

**Evidence:** Handoff §§3.1–3.2; source reports lack enrollment fields.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M06: P0046

**Original P0046:** The scope of the predictive model is strictly limited to Dengue, Leptospirosis, and Measles disease cases among the school-aged demographic (5-19 years old) in Antipolo City. The primary analytical scope of this study is the application of a hybrid SARIMA-NNAR forecasting approach, in which SARIMA models the linear and seasonal components of each disease's case trajectory, while NNAR captures the nonlinear structure in the residuals. Furthermore, the system will not aggregate these diseases into a single forecast; instead, five (5) distinct, disease-specific SARIMA and NNAR models will be trained to ensure mathematical accuracy for each unique seasonal pattern. It will look at the total number of new cases for each disease every month. SARIMA will be used to capture the linear and seasonal patterns of the diseases, while NNAR will be applied to model the complex, nonlinear epidemic trajectories. The data come from official records collected over ten years (January 2016 to December 2025), provided by the Antipolo City Health Office (CHO) and/or the Department of Health (DOH) through the Philippine Integrated Disease Surveillance and Response (PIDSR) system. This period includes the period before the pandemic, the COVID-19 lockdowns, and the period after the pandemic, when disease cases changed again.

**Proposed replacement:** The approved analytical population is individuals aged 5–19 in Antipolo City, using confirmed cases once eligible records are supplied and verified. One disease-specific SARIMA–NNAR pipeline will be evaluated for each approved disease category, with the SARIMA forecast plus the NNAR residual forecast as the primary output. Dengue, Leptospirosis, and Measles-Rubella are the provisional categories. Historical all-age data for January 2016–December 2025 are retained for a separate evaluation. Disease count and final classification remain pending verification; no combined cross-disease forecast establishes disease-specific performance.

**Reason:** Removes five-model contradiction without prematurely fixing final coverage. NNAR learns residuals, not a separate raw case trajectory.

**Evidence:** Handoff §§3.1–3.5; baseline pipeline.py::run_hybrid_pipeline.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M07: P0047, P0239, P0240

**Original P0047:** For the technical part, this study uses a quantitative time-series design, examining past data. All analysis is done using Python 3.11. The study uses the pandas library to prepare the data and the statsmodels library to build and improve the SARIMA models for each disease. The final result will be an interactive online dashboard made with Plotly Dash. This dashboard will show past disease trends and predict the number of new cases for the next year, helping local health officials plan for the future.

**Original P0239:** Python 3.11 / pandas / statsmodels 

**Original P0240:** The specific computational environment and libraries this study's SARIMA modeling and data-wrangling pipeline is built and constrained by. 

**Proposed replacement:** The recorded local evaluation environment uses Python 3.13.3. Project metadata requires Python 3.12 or later. pandas handles tabular data, statsmodels implements SARIMA and diagnostics, scikit-learn implements the residual neural regressor and scaling, and Plotly Dash provides the interface. Exact installed versions and manifest differences are recorded with each evaluation in TEST_RESULTS.md.

**Reason:** Replaces Python 3.11 and records runtime separately from required minimum and unverified pins.

**Evidence:** python --version directly returned 3.13.3; pyproject.toml:5; requirements.txt; TEST_RESULTS.md.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M08: P0049

**Original P0049:** To set clear limits for the study and ensure it is accurate and practical, the researchers have defined specific boundaries. First, even though the Philippine Integrated Disease Surveillance and Response (PIDSR) system tracks many health problems, this study does not include other diseases like Influenza-Like Illness (ILI), Tuberculosis, Hand, Foot, and Mouth Disease (HFMD), and COVID-19. These diseases were excluded because their patterns are not mainly affected by regular seasonal weather, which is important for SARIMA forecasting.

**Proposed replacement:** The initial research categories are provisional and will be finalized after CHO consultation and data verification. Other disease labels supported by the general upload software are outside the formal research scope unless separately approved. Their exclusion does not establish that they lack seasonality.

**Reason:** Original makes an unsupported blanket seasonal exclusion and conflicts with its own TB seasonal literature discussion P0062.

**Evidence:** P0049 versus P0062; handoff §3.4.

**Approval/application status:** Awaiting adviser approval of delimitation rationale; no scope expansion authorized. Original not changed.


### M09: P0051

**Original P0051:** There are some limits to the data used in this study. The accuracy depends on the PIDSR’s passive reporting system. The model assumes that hospital and clinic records reflect the true trend for the whole city, but that mild or unreported cases are not included.  Also,  the data set includes the raw aggregated case volumes, whether they were suspected or confirmed in the laboratory, and does not adjust for changes in population size over the ten years. Because the model only uses past case data, it cannot separate the effects of outside health actions, like mosquito fogging or vaccination campaigns, done by the local government. The study only uses total monthly case numbers. It does not involve checking individual patients or collecting personal medical records, so it follows the Data Privacy Act of 2012 (Republic Act No. 10173). The forecasts are for the whole city, not for smaller areas like barangays or schools, to avoid problems with months that have no reported cases in those places. 

**Proposed replacement:** The intended final analytical dataset contains confirmed cases among individuals aged 5–19. The supplied weekly reports contain all-age aggregates, and their case-classification status is unverified. Those reports support a separately labeled all-age technical evaluation only. Monthly case counts are not population-adjusted incidence rates; mild, unreported, or delayed reports may affect interpretation. City-wide aggregates do not identify individual patients, school enrollment, or transmission settings, and the prototype does not establish legal compliance or causal effects of interventions.

**Reason:** Original explicitly admits suspected cases and silently treats them as target data; confidentiality cannot alone establish statutory compliance.

**Evidence:** Handoff §§3.1–3.3, 6.3–6.4; DATA_RECONCILIATION.md.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M10: P0052, P0085

**Original P0052:** For the technical part, the online dashboard made by this study is only meant as a sample for academic use and to help plan early warning systems. It will not actually be set up, hosted on the internet, checked for security, or connected to the Antipolo City government’s systems that are not part of this research. Also, the 12-month forecast can only use patterns seen in past data. It cannot predict rare or unusual events, such as very strong typhoons that have not occurred in the last ten years.

**Original P0085:** The output phase produces two key results, namely, the year-ahead forecast for each disease and the set of historical trend and seasonal decomposition visualizations. The results are made available through a web-based epidemiological dashboard created using Python (Dash, Pandas, and Statsmodels), allowing end-users, such as the Antipolo City Health Office and school administrators, to visualize disease trends in past years while at the same time making predictions of disease occurrences in the near future. Lastly, the evaluation phase evaluates the dashboard with respect to the ISO/IEC 25010:2011 (SQuaRE) standard, focusing on dimensions including functional suitability, performance efficiency, reliability, security, and usability.

**Proposed replacement:** The dashboard is an academic prototype. Software behavior can be tested locally, but production deployment, government-system integration, security assurance, formal CHO acceptance, and expert usability evaluation remain separate activities. Any ISO/IEC-based assessment must specify its selected edition, instrument, respondents, criteria, and actual results before quality ratings are claimed.

**Reason:** P0052 excludes security checking while P0085 includes security evaluation. No expert results supplied.

**Evidence:** P0031/P0052/P0085; tests establish software behavior only.

**Approval/application status:** Awaiting researcher/adviser decision on evaluation protocol; CHO acceptance and usability evidence unavailable. Original not changed.


### M11: P0066

**Original P0066:** Parreño (2025) compared SARIMA, Holt-Winters, Echo State Network (ESN), and NNAR models on weekly Philippine measles incidence data spanning January 2017 to October 2023, using Predictive Mean Matching (PMM) to address missing-data gaps. This approach addresses the limitations of missing and pandemic-distorted surveillance data by applying a validated imputation method before model comparison. The study found that NNAR produced the lowest prediction errors across RMSE, MAPE, and MAE, and was judged the most effective model overall, though SARIMA still adequately captured the series' seasonal structure despite pandemic-era outliers. This demonstrates both SARIMA's continued adequacy for seasonal Philippine disease data and a validated missing-data handling method directly applicable to the present study's own administrative dataset.

**Proposed replacement:** The cited measles study discusses an imputation method in its own setting. The present implementation does not adopt that method: missing months remain unknown and block forecasting until the source is clarified. Any future imputation method requires a separately justified and approved protocol.

**Reason:** Literature method is not automatic authorization to impute local surveillance data.

**Evidence:** pipeline.py::_validate_observation_coverage; handoff §7.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M12: P0080

**Original P0080:** A hybrid SARIMA-NNAR approach was chosen over relying on either model alone. SARIMA was chosen since earlier studies in the Philippines often reported it as a steady and easy-to-explain starting point. It fits patterns that change with the seasons, like dengue and its higher rates during the rainy months. It also matches measles patterns, even when COVID-19 disturbed regular reporting. However, SARIMA alone may not catch the harsher ups and downs in case numbers. Those irregular shifts can come from things such as lockdowns during the pandemic or sudden vaccination pushes. NNAR was added specifically to model these leftover, harder-to-predict patterns that remain in SARIMA's residuals, following the same logic used in other hybrid disease-forecasting studies that combine classical and machine-learning techniques to lower prediction error. Combining the two lets the system keep SARIMA's proven seasonal accuracy while still capturing the nonlinear disruptions unique to a ten-year dataset spanning the pre-, during-, and post-pandemic periods — something neither model could do as well on its own.

**Proposed replacement:** The mandatory hybrid architecture combines a SARIMA case-count forecast with a neural forecast of SARIMA residuals. Its empirical performance is evaluated separately for each eligible disease and population, alongside SARIMA-only and seasonal-naive benchmarks. Hybrid superiority is not assumed, and all unfavorable comparisons are retained.

**Reason:** Original asserts neither model could perform as well alone without evidence; historical adverse results already exist.

**Evidence:** evidence/ historical prediction arrays; THESIS_READINESS.md historical real-data table; MODEL_EVALUATION.md.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M13: P0083

**Original P0083:** Besides, the input phase also includes historical monthly data on dengue, leptospirosis, and measles in Antipolo City from January 2016 to December 2025.  This input data is obtained through the PIDSR, specifically the Antipolo City Health Office (CHO) and/or the Department of Health (DOH), even for the periods that were before the pandemic, during, and after the pandemic.

**Proposed replacement:** The supplied development data are weekly, all-age surveillance tables for 2016–2025 transcribed into a workbook. Monthly aggregation uses the month containing the ISO week’s Thursday, with non-ISO week 53 provisionally assigned to December. The CHO must verify its epidemiological-week convention and supply eligible confirmed-case records for ages 5–19. Arithmetic reconciliation is documented independently of epidemiological completeness.

**Reason:** Source granularity is weekly, not originally monthly; attribution and approval must remain distinct.

**Evidence:** dashboard/data/xlsx_parser.py::epi_week_to_month; DATA_RECONCILIATION.md.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M14: P0084

**Original P0084:** The process phase consists of four parts in order to maintain a systematic workflow. The data preparation phase starts with the purification and coding of the initial case records, filling in blank monthly data, and identifying anomalies from the COVID-19 timeline. The analysis of the time series decomposes the records of each illness into their seasonal, trend, and residual components so that each series is analyzed for stationarity in the pre-, pandemic, and post-pandemic periods. The hybrid forecasting phase implies using the Seasonal Autoregressive Integrated Moving Average (SARIMA) model, which helps to describe linear and seasonal structures of the disease, and the Neural Network Autoregression (NNAR) model that is applied to residual values in order to grasp the nonlinear nature of the previously mentioned model. The model assessment phase involves using RMSE, MAE, and MAPE measures in order to verify the correctness of the forecasting and aims at achieving a MAPE less than 32.22%, which was set as a standard by Olana et al. (2025).

**Proposed replacement:** Preparation validates dates, disease labels, counts, provenance, and observed monthly coverage without inventing missing observations. Seasonal decomposition is a descriptive display, not an input transformation for the forecast pipeline. SARIMA identification uses only each training window, and NNAR models that SARIMA fit’s residuals. Report MAE, RMSE, MAPE with nonzero-actual coverage, and WAPE with zero-denominator handling for the hybrid and its benchmarks. Olana et al. (2025), Table 1, reports a SARIMA test MAPE of 32.22% for national dengue; this external result is historical context, not a universal acceptance threshold or a benchmark computed from Antipolo data.

**Reason:** Corrects imputation, unsupported period-specific stationarity, decomposition inputs, omitted WAPE and misuse of 32.22.

**Evidence:** metrics.py::compute_metrics; publisher Table 1 https://onlinelibrary.wiley.com/doi/10.1155/tbed/7480710; handoff §§10–11.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M15: P0097, P0098

**Original P0097:** The Presentation Tier contains the graphical interface built with Plotly Dash where users can interact with the system through a web browser. Users can select a specific disease (dengue, leptospirosis, or measles) and a date range, then view results that include historical case trends, seasonal decomposition plots, and 12-month-ahead forecasts. The interface also displays model accuracy metrics and provides real-time alerts if data fails to load or a forecast cannot be generated.

**Original P0098:** The Logic Tier contains the Data Preparation Module, the Time Series Analysis Module, the Hybrid Forecasting Module, and the Model Evaluation Module, which processes all the logic in the system. The Data Preparation Module cleans the disease data records, imputes missing values, and flags COVID-related anomalies. The Time Series Analysis Module breaks each disease series into seasonal, trend, and residual components, then checks stationarity per series. The Hybrid Forecasting Module runs two models on this decomposed data: SARIMA models the linear and seasonal patterns in disease cases, and NNAR captures the nonlinear structure left in SARIMA's residuals. The Model Evaluation Module then computes RMSE, MAE, and MAPE on the combined forecast.

**Proposed replacement:** The presentation layer displays historical counts, descriptive seasonal decomposition, forecast case counts, diagnostics, error messages, and the empirical forecast error band. The forecasting logic fits each disease’s observed monthly series and passes aligned SARIMA residuals to NNAR; it does not train on a separately decomposed trend or automatically identify causal COVID-related anomalies. Missing-month validation precedes modeling.

**Reason:** Code does not train on decomposed components, impute, or implement COVID anomaly classifier.

**Evidence:** pipeline.py; view_callbacks.py::_build_decomposition_chart; figures.py::fig_decomposition.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M16: P0100

**Original P0100:** The Data Tier holds three stores. Historical Case Data Storage keeps the cleaned PIDSR/DOH disease records. Model Storage keeps the trained SARIMA and NNAR data. Forecast Output Storage keeps the generated 12-month predictions and decomposition results. The Logic Tier retrieves data from this tier and stores trained models and forecasts back into it.

**Proposed replacement:** The prototype uses browser session storage for active tabular data, upload summaries, and serialized forecast results. Pending uploads remain in memory until explicit disease-catalog confirmation. Fitted SARIMA and neural estimator objects are transient during computation; no database or persistent trained-model repository is implemented.

**Reason:** Three conceptual databases and saved models are not actual stores.

**Evidence:** dashboard/ui/layout.py::build_layout; dashboard/modeling/serialization.py; view_callbacks.py::_get_or_compute_disease.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M17: P0109, P0111

**Original P0109:** In the SARIMA pipeline, stationarity testing is the first step where the Augmented Dickey-Fuller (ADF) test checks whether the raw data series has a stable mean and variance over time. If the series fails the stationarity test, differencing follows, where non-seasonal differencing subtracts each value from the one before it with the formula:

**Original P0111:** where y'[t] is the differenced series at time t, y[t] is the original series at time t, and y[t−1] is the value of the series at the previous time step. This differencing process continues multiple times until stationarity is achieved.

**Proposed replacement:** ADF testing assesses evidence against a unit root in each training series; it does not prove stable variance or all forms of stationarity. Nonseasonal and seasonal differencing are explored within documented finite bounds, with diagnostic limitations retained. Differencing does not continue indefinitely until a desired test result appears.

**Reason:** Corrects ADF interpretation and unbounded differencing claim.

**Evidence:** Revised sarima.py candidate identification; handoff §8; final algorithm details in CHATGPT_RETURN_HANDOFF.md.

**Approval/application status:** Technical wording proposed; final algorithm must be checked against verified implementation. Original not changed.


### M18: P0112, P0113, P0114

**Original P0112:** Once the series is stationary, model identification uses the Autocorrelation Function (ACF) and Partial Autocorrelation Function (PACF) plots of the differenced series to select the remaining orders.

**Original P0113:** Parameter estimation then fits the chosen orders to the data using maximum likelihood estimation, which finds the coefficient values that best explain the observed case counts. Candidate models are compared using Akaike Information Criterion (AIC), and the combination of (p,d,q)(P,D,Q) that minimizes this score is selected for each disease.

**Original P0114:** Diagnostic checking examines the residuals of the fitted model. A Ljung-Box test confirms the residuals behave like white noise, meaning no further autocorrelation remains for the model to capture.

**Proposed replacement:** For each training window, record ADF and ACF/PACF diagnostics, bounded candidate SARIMA orders, convergence and stability checks, AIC values, and residual diagnostics. Select an admissible candidate using the documented procedure without consulting that window’s future observations. A Ljung–Box result is diagnostic evidence about residual autocorrelation, not proof of white noise or forecast accuracy. Preserve candidate failures and disclose any residual concerns.

**Reason:** AIC and residual tests do not prove predictive accuracy. Must match actual selection/rejection procedure.

**Evidence:** Revised sarima.py; MODEL_EVALUATION.md; handoff §§3.6, 8.

**Approval/application status:** Technical wording proposed; implementation and validation status tracked in handoff. Original not changed.


### M19: P0119, P0122, P0123, P0124

**Original P0119:** The Neural Network Autoregression (NNAR) model uses lagged values of a time series as inputs to a neural network. This lets NNAR capture nonlinear patterns that SARIMA cannot represent on its own. The model considers only feed-forward networks with one hidden layer, using the notation:

**Original P0122:** Fitting an NNAR model has three layers which are the input layer, hidden layer, and output layer, which follow a fixed sequence of steps, where lagged input selection is the first step. In the input layer, the model takes the previous p values of the series as its input set to train and learn from. 

**Original P0123:** After taking the previous p values, the hidden layer then processes these inputs, where each lagged value is combined through weighted connections into each hidden node, producing an output value for every node in the layer. 

**Original P0124:** These hidden node outputs are then used by the output layer, which combines them into a single forecasted value: the network's prediction for the residual left over from the SARIMA model at time t, denoted e[t]. Once e[t] is predicted, it is used as a new input to predict e[t+1], and this process iterates for each subsequent step. The final forecast for each disease combines SARIMA's linear prediction with NNAR's predicted residual, producing the hybrid SARIMA-NNAR output.

**Proposed replacement:** The residual NNAR implementation is a scikit-learn MLPRegressor using three lagged SARIMA residuals, one hidden layer with four ReLU units, L2 alpha=10.0, L-BFGS optimization, max_iter=2000, and random_state=42. StandardScaler is fitted to training lag features only; targets remain in residual units. Forecasts recurse through predicted residuals. The primary point forecast is max(0, SARIMA forecast + NNAR residual forecast). Convergence warnings and component failures are retained; failed neural fitting must not masquerade as a successful zero correction.

**Reason:** Makes implementation reproducible and distinguishes actual architecture from conceptual diagram.

**Evidence:** config.py NNAR constants; nnar.py::run_nnar; metrics.py::hybrid_forecast; handoff §9.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M20: P0163, P0191, P0197, P0207

**Original P0163:** Linear structure cannot capture nonlinear residual patterns on its own (Needs a Neural Network Model Algorithm)

**Original P0191:** Easier interpretability and better prediction than a standard ANN as a nonlinear autoregressive model

**Original P0197:** Underperforms on smaller series without data augmentation or transfer learning

**Original P0207:** Underperforms when compared to the LSTM model

**Proposed replacement:** Comparative model properties are context-dependent findings from their cited studies. They do not establish an intrinsic need for a neural model, universal interpretability, or a fixed performance ranking on Antipolo data. Report the experimental setting for each comparison and assess local performance on the same untouched holdout.

**Reason:** Tables 1–2 contain universal performance claims; SARIMA need not always require NNAR and RF/LSTM rankings vary.

**Evidence:** Manuscript Tables 1–2; historical local adverse results.

**Approval/application status:** Awaiting adviser review of literature claims and primary-source citation checking. Original not changed.


### M21: P0218

**Original P0218:** The base time-series model this study builds on before adding seasonal terms, used to establish whether disease incidence retains an autocorrelative structure across the 2015–2025 dataset. 

**Proposed replacement:** ARIMA is a nonseasonal autoregressive integrated moving-average model; SARIMA adds seasonal terms. This study uses the historical period January 2016–December 2025, subject to verified eligible data availability.

**Reason:** Glossary unexpectedly uses 2015–2025.

**Evidence:** P0027/P0033/P0046 versus P0218; source workbook years.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M22: P0224, P0242, P0246, P0250

**Original P0224:** The preprocessing step applied in this study to separate each disease's raw incidence series into trend, seasonal, and residual components before SARIMA modeling. 

**Original P0242:** The leftover component of a disease's decomposed time series in this study, checked during diagnostic testing to confirm the SARIMA model has captured all systematic patterns. 

**Original P0246:** The recurring yearly pattern this study expects to find in each target disease's incidence for example, wet-season peaks in vector-borne diseases extracted through decomposition. 

**Original P0250:** The long-term directional component this study isolates during decomposition, separate from each disease's seasonal and residual components. 

**Proposed replacement:** Seasonal decomposition is a descriptive visualization separating trend, seasonal, and remainder components. SARIMA residuals used by NNAR are observed counts minus aligned SARIMA fitted values within the training window; they are distinct from the decomposition remainder. Seasonal patterns are assessed from the data rather than assumed for every disease.

**Reason:** Avoids conflating two residual definitions and claiming decomposition is model preprocessing.

**Evidence:** pipeline.py::_run_backtest_leg; view_callbacks.py::_build_decomposition_chart; figures.py::fig_decomposition.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M23: P0226, P0238

**Original P0226:** The practical output this study aims to produce  a SARIMA-based tool that gives DepEd and the City Health Office month-ahead notice of expected incidence peaks. 

**Original P0238:** The specific software framework used in this study to build the interactive dashboard that displays trend visualizations, seasonal overlays, and outbreak alerts to school health officers. 

**Proposed replacement:** The prototype displays provisional forecast case counts and data/model error feedback. It does not implement a validated outbreak-detection threshold, automated notification service, or surveillance response workflow.

**Reason:** Forecasts and input error messages are not operational outbreak alerts; glossary changes horizon to month-ahead.

**Evidence:** view_callbacks.py and layout.py; handoff §§3.7, 14.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M24: P0234

**Original P0234:** The six specific disease categories this study tracks, each of which schools are required to report to DepEd and the City Health Office under existing surveillance mandates. 

**Proposed replacement:** Reportable disease categories are defined by the applicable surveillance source and approved research scope. Dengue, Leptospirosis, and Measles-Rubella are the provisional research categories pending CHO and adviser verification.

**Reason:** Glossary says six categories despite three provisional categories; school reporting-law claim requires separate primary legal support.

**Evidence:** P0046/P0049/P0234; handoff §3.4.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M25: P0248

**Original P0248:** The core data structure this entire study is organized around is monthly disease incidence counts recorded sequentially per school from 2016 to 2025. 

**Proposed replacement:** The modeled time series consists of city-wide monthly disease case counts, in chronological order. The approved population is ages 5–19 with confirmed cases once eligible data are obtained; current all-age results are separate. School-level observations are not supplied.

**Reason:** Glossary claims per-school records whereas source is city-wide.

**Evidence:** P0051; source PDFs; handoff §§3.1–3.3.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M26: P0044

**Original P0044:** For future researchers, this study can serve as a foundational reference for infectious disease forecasting in the Philippines. The methodology and dataset used can be extended to cover other reportable infectious diseases and applied to other cities in the Philippines. This study also demonstrates an application of SARIMA modeling in a public health setting.

**Proposed replacement:** This study documents a reproducible SARIMA–NNAR prototype and its benchmarks, data limitations, and evaluation results. Applying it to other diseases or locations requires separate source verification and evaluation.

**Reason:** Includes NNAR and avoids treating transferability as demonstrated.

**Evidence:** Mandatory hybrid decision; historical adverse results.

**Approval/application status:** Author decision supports correction; exact manuscript wording awaiting researcher/adviser acceptance. Original not changed.


### M27: P0257, P0283, P0286, P0290

**Original P0257:** Castro, M. C., et al. (2024). The impact of COVID-19 mobility restrictions on dengue transmission in urban areas. PLOS Neglected Tropical Diseases, 18(5), e0012644. https://doi.org/10.1371/journal.pntd.0012644 

**Original P0283:** Plaza, G. C., Servillon, R. J., Alempang, H., Boquia, Y. B. S., Gonzales, K. A., Japitan, K., Parba, S. G., & Hinay, A., Jr. (2024). Epidemiology forecasting analysis of dengue cases with seasonal autoregressive integrated moving average in Davao City, Philippines. Research Square. https://www.researchsquare.com/article/rs-4440701/latest 

**Original P0286:** Servillon, R. J. T. (2024). Epidemiology forecasting analysis of dengue cases with seasonal autoregressive integrated moving average in Davao City, Philippines. Research Square (preprint). https://doi.org/10.21203/rs.3.rs-4440701/v1 

**Original P0290:** Warnasekara, J., Koralegedara, I., Siriwardana, J., & Agampodi, S. (2022). SARIMA and ARDL models for predicting leptospirosis in Anuradhapura district, Sri Lanka. PLOS ONE, 17(10), e0275447. https://doi.org/10.1371/journal.pone.0275447 

**Proposed replacement:** Verify each bibliographic record against the primary publication before submission. Retain one correctly attributed entry per publication/version, distinguish preprints from reviewed articles, and make in-text authors and years match the verified reference record.

**Reason:** Plaza and Servillon entries appear to refer to the same preprint; Warnasekara author lists differ between table and bibliography. Other literature claims were not exhaustively source-authenticated in this audit.

**Evidence:** P0165/P0209/P0290; P0067/P0283/P0286.

**Approval/application status:** Awaiting adviser/researcher bibliographic verification; no unverified corrections applied. Original not changed.

## Embedded diagrams: exact label replacements

These diagram proposals are not applied to the original images. Their research requirements are established; revised drawing layout awaits researcher/adviser acceptance.

| ID / location | Original statement or label | Proposed exact replacement / flow | Reason and evidence | Status |
|---|---|---|---|---|
| M28, Figure 1 IPO, image7.png | “HISTORICAL DISEASE DATASET (2016-2026)” and output title “(2016–2026)” | “Historical observations: 2016–2025; provisional forecast year after complete history: 2026” | Observation and forecast years differ; workbook ends 2025. | Proposed, unapplied |
| M29, Figure 1 | “PYTHON 3.14.7 OR LATEST” | “Recorded runtime: Python 3.13.3; project requirement: Python >=3.12; exact package versions in test report” | Direct interpreter check and pyproject.toml:5; no claim that latest was tested. | Proposed, unapplied |
| M30, Figure 1 | “TARGET MAPE BELOW 32.22%, AS SET BY OLAN ET AL. (2025)” | “Historical external reference: SARIMA test MAPE 32.22%, Olana et al. (2025), Table 1; not an Antipolo acceptance threshold” | Primary publisher Table 1 directly verifies provenance; author's surname is Olana. | Provenance verified; wording proposed |
| M31, Figures 1–2, image7.png/image5.png | “IMPUTE MISSING MONTHLY VALUES”; “flagging COVID-anomalies” | “Validate missing and invalid observations; block incomplete forecast inputs; retain source reporting limitations” | No approved imputation or causal anomaly classification; pipeline coverage validation. | Proposed, unapplied |
| M32, Figures 1–2 | “DISPLAYED CONFIDENCE INTERVALS”; “Displays confidence intervals” | “Display historical maximum-absolute-error band; no validated coverage probability” | pipeline.py::_historical_error_band; no calibrated 95% hybrid coverage established. | Proposed, unapplied |
| M33, Figure 2 Data Tier, image5.png | “Model Storage”; “Stores SARIMA and NNAR data” | “Transient model fitting in process; browser session stores data and serialized result arrays, not fitted model objects” | ui/layout.py::build_layout; modeling/serialization.py. | Proposed, unapplied |
| M34, Figure 4 NNAR, image4.png | Three input nodes and three hidden nodes | Draw 3 residual-lag input nodes, 4 ReLU hidden nodes, and 1 residual output node; caption “Implemented residual MLP architecture (3,4,1)” | config.py NNAR_LAGS=3, NNAR_HIDDEN=(4,); nnar.py. | Proposed, unapplied |
| M35, Figure 5 main flow, image2.png | “Validation passed?” → “Dataset storage” | “Validation passed?” → “Show complete upload disease catalog” → “Explicit user confirmation?” → “Activate uploaded dataset and invalidate cached results” | data_callbacks.py::transition_data_session; existing catalog confirmation workflow. | Proposed, unapplied |
| M36, Figure 7 data storage, image8.png | “Any tracked disease missing from real data?” → “Mock data” → “Store combined dataset” | Remove supplementation branch. “Activate confirmed upload as authoritative dataset; never add synthetic observations. Reset to sample is a separate explicit action.” | combine.py::prepare_uploaded_data; handoff §6.1. Original figure contradicts even preserved baseline. | Proposed, unapplied |
| M37, Figure 8 training, image6.png | “Hybrid scores better than SARIMA on test months?”; “Select SARIMA only as final model”; “Retrain winning model” | “Fit SARIMA candidate and residual NNAR using training observations; if a component fails, try another valid SARIMA candidate, otherwise report explicit hybrid unavailable. Evaluate hybrid and benchmarks on matching periods. Refit mandatory hybrid on available history after evaluation.” | Author mandatory hybrid decision supersedes diagram's conditional model selection. | Proposed, final code status in handoff |
| M38, Figures 3 and 8 | Stationarity/differencing loop; simple train/test branch | Add finite candidate bounds, recorded diagnostics, separate earlier evaluation folds and final untouched holdout; retain failure exit rather than endless differencing. | handoff §§8–10; revised sarima.py/pipeline.py. | Proposed, final algorithm verification required |

## Required methodological additions (no corresponding complete original statement)

**M39 — Evaluation protocol, proposed insertion:** “For a complete January 2016–December 2025 monthly series, use training through December 2022 to evaluate 2023 and training through December 2023 to evaluate 2024. Reserve January–December 2025 as the final holdout after training through December 2024. Perform parameter identification independently within each training window. The holdout does not determine architecture, candidate bounds, or neural settings. After evaluation, refit the approved hybrid using all available history to forecast 2026. Because previous development has already examined the 2025 outcomes, document that historical exposure: an algorithmically excluded holdout is not newly unseen evidence to the research team.” Evidence: historical THESIS_READINESS.md, pipeline evaluation windows, handoff §10. Status: proposed clarification; author/adviser must assess validity of previously observed holdout and decide whether prospective evaluation is additionally required.

**M40 — Metrics, proposed insertion:** “For n matched holdout observations, error e_i=y_i−ŷ_i, MAE=Σ|e_i|/n and RMSE=sqrt(Σe_i²/n). MAPE=100·mean(|e_i|/|y_i|) over nonzero actual observations only; disclose that count and report N/A if none exist. WAPE=100·Σ|e_i|/Σ|y_i|; report N/A when the actual denominator is zero. Report hybrid, SARIMA-only, and seasonal-naive results separately on identical periods; never average synthetic and real populations.” Evidence: metrics.py::compute_metrics. Status: author-required technical correction; proposed manuscript insertion.

**M41 — Source reconciliation, proposed insertion:** “For Dengue 2024, the printed PDF annual total is 4,516 and the sum of weekly observations is 4,588, a difference of 72. The workbook follows weekly observations. Both values and their origins are preserved pending CHO correction; arithmetic consistency does not establish case completeness. Blank cells are distinguished from explicit zero counts, and the weekly calendar remains provisional.” Evidence: DATA_RECONCILIATION.md and preserved original reports. Status: awaiting CHO confirmation; proposed disclosure.

**M42 — Error band, proposed insertion:** “The displayed band adds and subtracts a historical maximum absolute forecasting error from the production point forecast, with the lower limit constrained to nonnegative counts. The calibration window and errors are recorded with the result. No prospective coverage guarantee or validated 95% prediction interval is claimed.” Evidence: pipeline.py::_historical_error_band and result interval_method. Status: proposed; precise calibration-window wording must be checked against final implementation.

**M43 — Historical and revised findings, proposed insertion:** “The prior conditional-selection implementation reported all-age holdout WAPE of 25.17% for Dengue, 67.08% for Leptospirosis, and 162.58% for the category then labeled Measles, against seasonal-naive WAPE of 34.90%, 55.86%, and 50.00%. These are historical results from the earlier implementation, not revised mandatory-hybrid results. The source category is Measles-Rubella. Revised results, failure states, prediction arrays, environment and warnings are reported separately in MODEL_EVALUATION.md.” Evidence: historical THESIS_READINESS.md and evidence artifacts; must not substitute these values for fresh runs. Status: approved transparency requirement; insertion pending manuscript acceptance.

**M44 — Source-population handling, proposed insertion:** “Synthetic demonstration observations, original all-age surveillance, unverified uploads, and verified ages 5–19 confirmed-case records are distinct dataset classes. An upload label or user declaration does not verify eligibility. Analyses must retain source file identity and population/classification metadata. Until the eligible extract is supplied, the approved population evaluation remains unavailable.” Evidence: handoff §§3.1–3.3, 6.1. Status: author-required separation, actual enforcement status in handoff.

## Verified historical-reference provenance

Checked 2026-09-27 against the primary [Olana et al. publisher article, Table 1](https://onlinelibrary.wiley.com/doi/10.1155/tbed/7480710). The table attributes 32.22 to SARIMA testing MAPE. Training covers January 2017–December 2023; testing covers January–December 2024 for nationwide dengue. Thus the number's source is verified, while using it as an acceptance criterion for Antipolo, ages 5–19, other diseases, or a hybrid is not justified by that source. The same paper reports lower testing MAPE for NNAR. Keep the fixed reference separate from the active-dataset benchmark. This is a provenance finding, not reproduction of the paper's experiment.

## Coverage and limits

Reviewed title/front matter; introduction/background; objectives; significance; scope/delimitations; Chapter 2 literature/design concept; all architecture explanations; Figures 1–8; comparative Tables 1–2; definitions Table 3; and all bibliography entries. Additional chronology, citation attribution, and causal claims remain candidates for adviser-led primary literature checking. The displayed November 10, 2026 cover date is later than this audit and should be confirmed as the intended submission date rather than silently changed. No CHO interview, expert usability assessment, clinical evaluation, ethics approval, or school-specific transmission study was supplied or inferred.
