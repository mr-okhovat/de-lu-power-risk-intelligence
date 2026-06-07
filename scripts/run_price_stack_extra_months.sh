#!/usr/bin/env bash
set -euo pipefail

python -m src.prices.run_price_stack --start 2024-05-01 --end 2024-05-31
python -m src.prices.run_price_stack --start 2024-07-01 --end 2024-07-31
python -m src.prices.run_price_stack --start 2024-08-01 --end 2024-08-31
