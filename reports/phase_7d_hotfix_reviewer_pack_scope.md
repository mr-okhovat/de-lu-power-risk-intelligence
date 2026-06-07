# Phase 7D hotfix — reviewer pack scope

Reviewer pack no longer requires the pipeline summary during pipeline execution.

Reason: the pipeline summary is written after all pipeline steps finish, so it cannot be a blocking input for a step inside the same pipeline.
