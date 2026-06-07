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
5. artifact manifest

With screenshots enabled:

1. tests
2. dataset registry
3. intake summary
4. reviewer-ready v2
5. dashboard screenshots
6. artifact manifest

The manifest runs after screenshots when screenshots are enabled, so screenshot hashes reflect the refreshed files.

This layer does not change analytics logic. It controls rebuild order and checkpoint reporting.
