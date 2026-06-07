# Project artifact manifest

Version: `13B.1`
Manifest table: `dashboards/project_artifact_manifest.csv`

## Status

- Artifacts tracked: `25`
- Required artifacts: `25`
- Existing artifacts: `25`
- Missing required artifacts: `0`
- All required present: `True`

## Artifacts

| category | path | required | exists | size bytes | sha256 |
|---|---|---:|---:|---:|---|
| project | `README.md` | True | True | 5118 | `a94471cd5af0` |
| orchestration | `scripts/run_project_checkpoint.sh` | True | True | 183 | `4df4ad624c98` |
| orchestration | `src/core/project_orchestrator.py` | True | True | 8048 | `fdfc9f1bdfa0` |
| reviewer | `reports/reviewer_ready_v2.md` | True | True | 2967 | `fea96160e7aa` |
| reviewer | `reports/reviewer_ready_v2.json` | True | True | 3163 | `1342aa5b0f4d` |
| reviewer | `dashboards/reviewer_ready_v2_metrics.csv` | True | True | 736 | `6d6f78fd44a1` |
| intake | `reports/dataset_adapter_registry_run.md` | True | True | 554 | `72ab954cac7b` |
| intake | `reports/dataset_adapter_registry_run.json` | True | True | 6233 | `e78a6d14b3f7` |
| intake | `reports/dataset_intake_summary.md` | True | True | 1463 | `eb945b7880d7` |
| intake | `reports/dataset_intake_summary.json` | True | True | 366 | `e4ee402607e3` |
| intake | `dashboards/dataset_intake_summary.csv` | True | True | 1864 | `162f2832b8ab` |
| lead_time | `reports/lead_time_evaluation_2024-05_to_2024-08.md` | True | True | 1887 | `f0d1a87226e4` |
| lead_time | `dashboards/lead_time_aggregate_DE-LU_2024-05_to_2024-08.csv` | True | True | 1869 | `f99fd55b36a9` |
| visual | `reports/visual_reviewer_pack.md` | True | True | 1124 | `7281ae44fc53` |
| dashboard | `app/streamlit_app.py` | True | True | 18093 | `08d7afe3839a` |
| dashboard | `reports/figures/dashboard/dashboard_overview.png` | True | True | 55494 | `b0188d3a7527` |
| dashboard | `reports/figures/dashboard/dashboard_selected_month.png` | True | True | 130698 | `4d7ded22fc1a` |
| dashboard | `reports/figures/dashboard/dashboard_diagnostics.png` | True | True | 111217 | `1a6730563402` |
| dashboard | `reports/figures/dashboard/dashboard_lead_time.png` | True | True | 98246 | `927d686e09f1` |
| dashboard | `reports/figures/dashboard/dashboard_dataset_intake.png` | True | True | 72433 | `9a599025f375` |
| dashboard | `reports/figures/dashboard/dashboard_reviewer_files.png` | True | True | 80462 | `4e26bd2f1c09` |
| core | `src/core/data_contracts.py` | True | True | 7775 | `9492d5e800e9` |
| core | `src/core/dataset_adapters.py` | True | True | 7420 | `de45cac0f3cd` |
| core | `src/core/adapter_registry.py` | True | True | 7995 | `a4cca01723d1` |
| core | `src/core/intake_summary.py` | True | True | 6553 | `0d9f2fdb7553` |

## Readout

All required checkpoint artifacts are present.

This manifest is for reproducibility and review control. It does not validate market logic by itself.
