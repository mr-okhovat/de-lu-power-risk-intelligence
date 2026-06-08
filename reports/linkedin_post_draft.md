# LinkedIn post draft

Over the past weeks, I have been building a reproducible DE-LU power-market risk-intelligence prototype using public market data.

The project is not a live trading system, and I am not presenting it as a P&L or alpha model. My goal was to build a clean analytics workflow that reflects how I approach power-market data, market risk signals, price-event behaviour, and reviewer-ready reporting.

The current version includes:

- public-data ingestion and validation,
- clean hourly market tables,
- load, renewable, residual-load and price-risk features,
- transparent rule-based risk signals,
- same-hour and forward-window price-event evaluation,
- four monthly DE-LU runs from May to August 2024,
- a market/month run catalog,
- an active run selection layer,
- automated tests and checkpoint rebuilding,
- reviewer-ready reports,
- a Streamlit dashboard.

What I mainly wanted to demonstrate was not a trading claim, but a disciplined analytics process: reproducibility, auditability, signal transparency, and the ability to communicate market behaviour clearly.

This is still a portfolio-grade prototype. To become professional trading analytics infrastructure, it would need longer history, stronger calibration, additional market layers, and more robust forecast-style validation.

For now, I see it as a practical demonstration of my work around power-market analytics, market risk, and trading-analytics support.

I would be happy to hear feedback from people working in energy trading, power analytics, market risk, or portfolio optimisation.
