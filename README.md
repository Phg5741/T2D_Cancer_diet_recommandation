# T2DCancer

A rule-based food-ranking research prototype for exploring dietary constraints associated with diabetes diagnosis, cancer history, and symptom scenarios.

T2DCancer combines patient attributes with configurable rules to filter and rank foods. Each result includes active conditions, excluded foods, scores, portion estimates, and explanations. The included NHANES and FoodData Central tables let you run the examples and tests without downloading raw data or training a model.

The project demonstrates a public health informatics workflow: turning public datasets and explicit dietary assumptions into software behavior that can be inspected, tested, and revised.

> **Research use only.** This prototype is not a clinical decision system. Its rules include provisional assumptions and research-team decisions, and its food annotations have not been reviewed.

## Contents

- [Public health context](#public-health-context)
- [Features](#features)
- [Installation](#installation)
- [Usage](#usage)
- [How it works](#how-it-works)
- [Data](#data)
- [Project structure](#project-structure)
- [Testing](#testing)
- [Limitations](#limitations)
- [Future public health research](#future-public-health-research)
- [Documentation](#documentation)

## Public health context

Nutrition is relevant to both individual and population health. Healthy dietary patterns help protect against malnutrition and noncommunicable diseases, including diabetes and cancer. Food choices also depend on income, prices, availability, and cultural practices. These factors make nutrition a public health concern as well as an individual decision. [WHO: Healthy diet](https://www.who.int/news-room/fact-sheets/detail/healthy-diet).

Within this broader context, T2DCancer investigates a focused design question: **how should a food-ranking system make its reasoning visible when diabetes-related rules, cancer-history rules, and changing symptom scenarios apply together?** For example, the prototype can expose a conflict between energy-density preferences or show how a swallowing-difficulty scenario changes texture-related rankings. These are inspectable research scenarios, rather than validated dietary prescriptions.

### Public health goals reflected in the design

| Goal | Implementation in this project |
|---|---|
| Examine coexisting health needs | Combine diabetes, cancer-history, symptom, and nutrition-state rules, with explicit handling of conflicting conditions. |
| Make assumptions reviewable | Keep rules in CSV tables and report active conditions, exclusions, and food-level scoring reasons. |
| Preserve uncertainty and provenance | Distinguish observed values, user inputs, scenarios, and unavailable information; report rules skipped because their inputs are unknown. |
| Support reproducible investigation | Include processed data, evaluation personas, baseline comparisons, sensitivity analysis, and unit tests. |

The current contribution is a reproducible way to examine dietary assumptions across patient scenarios. It provides a basis for discussion with public health researchers and nutrition professionals; improvements in diet quality, health outcomes, or service access have not been measured.

## Features

- Apply hard exclusions and soft preferences using editable CSV rule tables.
- Recompute food rankings when patient attributes or symptom scenarios change.
- Track input sources and report rules skipped because inputs are unknown.
- Compare the full rule set with static, diabetes-only, and cancer-only baselines.
- Inspect the conditions and food features behind each ranking.

## Installation

Run all commands from the repository root. The provided Conda environment specifies Python 3.11 and pandas 2.2.

### Conda

```bash
conda env create -f environment.yml
conda activate t2dcancer
```

### pip

Alternatively, activate a Python virtual environment and install the dependencies:

```bash
python -m pip install -r requirements.txt
```

Runtime dependencies are pandas, NumPy, and openpyxl. Tests use Python's built-in `unittest` framework.

## Usage

### Run the example

```bash
python infer.py --input input/patient_input.example.json
```

The example uses a synthetic input record. The command prints the results and writes `output/final_results.txt`, creating the output directory if necessary.

### Use a custom input

Copy [input/patient_input.example.json](input/patient_input.example.json) to `input/patient_input.json`, edit the values, and run:

```bash
python infer.py
```

To use different input and output paths:

```bash
python infer.py --input input/my_patient.json --output output/my_results.txt
```

| Option | Default | Description |
|---|---|---|
| `--input` | `input/patient_input.json` | Path to a patient-input JSON file. |
| `--output` | `output/final_results.txt` | Path for the text report. |

Key JSON fields:

| Field | Description |
|---|---|
| `patient_id` | Identifier assigned to the patient state. |
| `age`, `sex`, `bmi`, `hba1c` | Patient attributes; use `null` for unknown values. |
| `diabetes_dx`, `insulin`, `diabetes_pills` | Boolean values or `null`. |
| `cancers` | A list of names, such as `"colon"`, or NHANES codes, such as `16`. See [cancer_codes.csv](rules/cancer_codes.csv). |
| `poor_appetite`, `dysphagia`, `mouth_sore`, `nausea`, `vomiting`, `malabsorption`, `digestion_problem` | Boolean symptom inputs or `null`. |
| `weight_loss_pct`, `treatment_stage` | Additional state fields. Not every recorded field currently activates a rule. |
| `base_seqn` | Optional SEQN from the included NHANES patient table, used to initialize observed attributes. |
| `top_k` | Number of foods to return; defaults to `10`. Set this in JSON, not as a CLI option. |

Unknown values are not statistically imputed. Rules with unknown triggers remain inactive and are reported as skipped. When `base_seqn` is set, omitted or `null` fields retain the corresponding observed values from that record; explicit values override them. An empty `cancers` list also retains the base record's cancer codes.

Local input files are excluded by `.gitignore`; only the synthetic example is included in the repository.

### Run the demonstration and evaluation

```bash
python main.py
```

This runs the example persona, compares rankings before and after a symptom change, and evaluates four rule configurations: `static`, `diabetes_only`, `cancer_only`, and `full`.

| Generated file | Contents |
|---|---|
| `outputs/milestone_PM_nausea_ranking.csv` | Ranked foods and explanations for the demonstration persona. |
| `outputs/persona_metrics.csv` | Metrics for each persona and rule configuration. |
| `outputs/dynamic_reranking.csv` | Food rankings before and after each evaluated state change. |
| `outputs/dynamic_accuracy.csv` | Agreement with expected directions of rank changes. |

To run the evaluation without the demonstration:

```bash
python -m evaluation.evaluate_personas
```

To inspect the effect of enabling a disabled rule without modifying the rule files:

```bash
python -m evaluation.sensitivity SY-13
```

Evaluation measures rule violations, agreement with expected rankings, and responses to scenario changes. The hard-restriction violation metric uses all annotated foods, including beverages and alcohol, as a stress test. These metrics assess behavior against the project's rules and expectations, not clinical outcomes.

## How it works

```text
Patient input
    -> Patient state and source labels
    -> Active conditions and conflict resolution
    -> Hard exclusions
    -> Soft-condition violation scores
    -> Ranked foods, portion estimates, and explanations
```

For each eligible food, the final score is:

```text
score = 1 - mean(violation across active soft conditions)
```

Each violation ranges from `0` to `1`, and each active soft condition contributes equally. Binary conditions use annotation flags. Numeric conditions use configured thresholds when available; otherwise, they use relative ranks within the candidate pool. With no active soft conditions, the score is `1` for every eligible food.

Candidate food roles, conditions, thresholds, and conflict handling are configured in [rules/](rules/). Under the current configuration, poor appetite scales the default portion by `0.5` without changing the ranking. This factor is a research-team design choice.

## Data

NHANES collects health and nutrition information through interviews, examinations, and laboratory testing. FNDDS supplies nutrient values and portion weights for foods reported in the dietary component of NHANES. T2DCancer uses these complementary resources for patient attributes and food features; it does not infer that a ranked food was consumed by a particular participant. [CDC: NHANES survey content](https://www.cdc.gov/nchs/nhanes/about/survey-content-operations.html), [USDA: FoodData Central documentation](https://fdc.nal.usda.gov/data-documentation/).

The repository includes the following processed tables:

| File | Rows | Description |
|---|---:|---|
| [patients_model.csv](data/processed/patients_model.csv) | 236 | NHANES observations for participants with diabetes diagnosis and cancer history. |
| [foods_model.csv](data/processed/foods_model.csv) | 77 | Selected foods with nutrients and default portions derived from FoodData Central Survey / FNDDS 2021-2023. |
| [food_annotation.csv](data/processed/food_annotation.csv) | 77 | Draft texture, taste, and food-role annotations; all rows have `annotator=claude_draft` and `reviewed=0`. |

The patient table contains observed records, not synthetic patients. Symptom and treatment fields unavailable in the source data remain empty. Evaluation personas combine observed attributes with explicit scenarios or use synthetic records; source labels distinguish these inputs.

Raw datasets are not included. To rebuild the processed tables, obtain the source files separately and place the FNDDS CSVs in `data/raw/fndds/` and the prepared patient CSV in `data/raw/nhanes_csv/patients_final.csv`. See the [data guide](data/README.md) for details before running the build scripts.

Raw data, custom inputs, generated reports, and caches are excluded from Git.

## Project structure

```text
T2DCancer/
|-- data/processed/      # Included patient, food, and annotation tables
|-- docs/                # Project concept document (Lean Canvas PDF)
|-- evaluation/         # Persona metrics and rule-sensitivity analysis
|-- input/              # Synthetic input example
|-- personas/           # Evaluation scenarios and expected rankings
|-- rules/              # Conditions, restrictions, thresholds, and conflicts
|-- scripts/            # Data builders and source-data audits
|-- src/                # Patient state, filtering, scoring, and ranking
|-- tests/              # Unit tests
|-- infer.py            # Single-input inference CLI
|-- main.py             # Demonstration and evaluation entry point
|-- environment.yml     # Conda environment
|-- requirements.txt    # pip dependencies
`-- README.md
```

`output/` and `outputs/` are created at runtime and are not tracked.

## Testing

```bash
python -m unittest discover -s tests -v
```

The suite covers hard exclusions, symptom-dependent ranking changes, portion scaling, missing inputs, cancer-code parsing, NHANES record initialization, evaluation metrics, and cohort counts.

## Limitations

- **Cohort definition:** `diabetes_dx` indicates a diabetes diagnosis, not confirmed type 2 diabetes. Cancer variables describe history, not active disease or treatment status.
- **Population inference:** The 236-record subset is used for prototype development. The current analysis does not use NHANES survey weights or account for its complex sampling design, so its summaries should not be presented as national prevalence estimates. See [CDC's NHANES weighting guidance](https://wwwn.cdc.gov/nchs/nhanes/tutorials/weighting.aspx).
- **Rule evidence:** Rule tables contain provisional rules, team decisions, and items awaiting verification. Evidence and status fields should be reviewed when interpreting results.
- **Annotation quality:** Texture and taste flags are unreviewed drafts, separate from the FNDDS nutrient measurements.
- **Evaluation scope:** Persona tests and rule-based metrics do not establish clinical safety or effectiveness.
- **Recommendation scope:** The system ranks individual foods from a small candidate set. It does not construct a complete diet or establish nutritional adequacy.

## Future public health research

The following are proposed extensions, not implemented or validated capabilities:

1. **Expert review:** Review rule evidence, conflict handling, and food annotations with dietitians and relevant clinical specialists.
2. **Equity and access:** Add food costs, local availability, preparation requirements, and cultural preferences, then examine whether highly ranked options are practical for the intended communities.
3. **Subgroup evaluation:** Compare rule coverage and ranking behavior across age, sex, condition combinations, and levels of missing information. Any population-level estimates would require an appropriate survey analysis design.
4. **Community relevance:** Co-design explanations with intended users and nutrition professionals, adapt food coverage to local dietary patterns, and evaluate usability before studying real-world dietary or health outcomes.

## Documentation

- [Data preparation and provenance](data/README.md) (Korean).
- [Project concept: Lean Canvas - Sugar-Free Plate](docs/Lean%20Canvas%20-%20Sugar-Free%20Plate.pdf) (PDF).
