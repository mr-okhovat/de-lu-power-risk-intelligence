# Project orchestration

The project checkpoint command rebuilds the controlled review outputs in order.

Run:

    bash scripts/run_project_checkpoint.sh

Optional screenshot refresh:

    bash scripts/run_project_checkpoint_with_screenshots.sh

Default stages:

1. tests
2. dataset registry
3. intake summary
4. reviewer-ready v2

The screenshot stage is optional because it starts Streamlit and a headless browser.

This layer does not change analytics logic. It only controls rebuild order and checkpoint reporting.
