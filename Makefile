.PHONY: test plan sample review status

test:
	python -m pytest

plan:
	python -m src.orchestration.run_all --config config/pipeline_sample.yaml --dry-run

sample:
	bash scripts/run_sample_pipeline.sh

review:
	python -m src.reporting.reviewer_pack --start 2024-06-01 --end 2024-06-03 --market-label DE-LU --smard-region DE --report reports/reviewer_pack_2024-06-01_to_2024-06-03.md --json reports/reviewer_pack_2024-06-01_to_2024-06-03.json

status:
	git status
