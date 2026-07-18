# WDW Demand Forecast

Live 30-day forecasts of Walt Disney World crowd levels, built on continuously
collected wait-time data. Sequel to [wdw-ticket-pricing](https://github.com/agentilcore589/wdw-ticket-pricing),
which found that Disney's posted ticket prices are dominated by seasonal
variation (7x swing) rather than day-of-week effects (4.1% weekend premium).
This project asks the follow-up question: **can operational demand be predicted
in advance, and how far ahead does the signal hold?**

## How it works

- **Collection**: GitHub Actions pulls ride-level wait times for all four WDW
  parks every 2 hours (8am-10pm ET) and daily weather for Lake Buena Vista.
- **Target**: daily park-level average posted wait, a proxy for attendance.
- **Features**: calendar structure (day of week, school breaks, holidays,
  special events), weather forecasts, lagged waits, and ticket-price signals
  from the pricing dataset (Disney's own demand expectation, encoded in price).
- **Models**: seasonal naive baseline → ETS → ARIMA with Fourier terms → TSLM
  with holiday regressors, evaluated with rolling-origin cross-validation.

## Roadmap

- [x] Data pipeline live
- [ ] Baseline + ARIMA models with rolling CV (Oct 2026)
- [ ] Public dashboard with live daily forecasts (Nov 2026)
- [ ] **Thanksgiving week 2026 forecast, published in advance** (Nov 2026)
- [ ] Post-mortem: forecast vs. reality (Dec 2026)

## Data sources

Wait times powered by [Queue-Times.com](https://queue-times.com/). Weather from
[Open-Meteo](https://open-meteo.com/). This is an independent analytics project
and is not affiliated with The Walt Disney Company.
