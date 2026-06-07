from src.prices.run_price_stack import paths


def test_paths() -> None:
    out = paths("2024-06-01", "2024-06-30", "DE-LU")

    assert out["prices"].endswith("hourly_prices_DE-LU_2024-06-01_to_2024-06-30.csv")
    assert out["behavior_report"].endswith("price_risk_behavior_2024-06-01_to_2024-06-30.md")
    assert out["confusion"].endswith("signal_price_confusion_DE-LU_2024-06-01_to_2024-06-30.csv")
