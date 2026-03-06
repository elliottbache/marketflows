<!-- docs/technical.md -->
# MarketFlows technical notes (MVP)

This file is meant for repo readers who want the plumbing: what runs where, what gets named, and how range derivatives work.

## Pipeline

Entry point:

- `marketflows.cli:main()`
  - parses `--config`, `--secrets`, `--out-dir`, `--log-level`, `--tutorial`
  - calls `configure_logging(...)`
  - calls `app.run_pipeline(...)`

Orchestrator:

- `marketflows.app:run_pipeline(...)`
  - loads/validates config
  - loads provider data
    - normal mode: reads `secrets.toml` and queries CoinGecko
    - tutorial mode: loads packaged `tutorial/config.toml` + packaged CSV/JSON
  - builds `df_master` (shared datetime index; market caps interpolated onto it)
  - branches by `flow_types`:
    - `narratives`: aggregate narrative assets → metrics → plots/tables
    - `individual_assets`: per-portfolio metrics + plots/tables, and also an aggregate “Portfolios” category
    - `market_cap_ranges`: bucket long-form MC data → bucket sums → range metrics → plots/tables

## Naming scheme

All metric columns follow the same shape:

- `<group>_by_<base_asset>` for normalized market cap (or normalized bucket value)
- optional `_ema<N>` (EMA span) when EMA is applied
- optional `_growth`, `_inflection`, or `_deriv<K>` for derivatives
- optional `_unit` for per-timestep unit normalization

`marketflows._helpers.name_column(...)` is the single place that generates names.

## Master dataframe (`df_master`)

`analysis.aggregates.create_master_df(...)`:

- creates a datetime index from `(min_timestamp, max_timestamp, freq)`
- for each asset, converts chart timestamps to datetime, joins onto master index,
  and interpolates with `method="time"` (`limit_direction="both"`)

This gives a single aligned DataFrame: `df_master[asset_id] -> market cap`.

## Narratives / portfolios metrics

`analysis.metrics.calculate_group_metrics(...)`:

- normalizes each group series by a base asset (or passes through for `us-dollar`)
- normalizes each series by its first valid record time (shared first-valid time)
- applies EMA(s) when configured
- computes derivatives (growth / inflection) and applies smoothing EMA on derivatives
- optionally adds unit-normalized columns per timestep

## Market-cap ranges

Cohort selection (provider side):

- `providers.coingecko._read_mcs_above_limit(min_limit)` builds the cohort once at startup:
  all coins with current market cap above `min_limit`.

Bucketing (analysis side):

- `analysis.aggregates.prepare_cap_ranges(...)` creates a long DataFrame:
  `(Datetime index, asset, market_caps, lower_limit)`
- `lower_limit` is assigned per row as the largest threshold that `market_caps` exceeds.

Aggregation:

- `analysis.aggregates.aggregate_cap_ranges(...)` groups by `(Datetime, lower_limit)` and sums market caps.

Derivatives:

- Growth and inflection use shifted bucket membership per asset:
  - growth uses membership at `(t-1)` vs totals at `t`
  - inflection uses membership at `(t-2, t-1, t)`

This is the MVP approach to avoid “range drift” artifacts when assets cross thresholds.

## Plots

- `plots.charts.plot_charts(...)` writes line charts as PNGs.
- `plots.tables.create_category_tables(...)` writes percent-gain tables as PNGs.
- `matplotlib` is configured to use `Agg` so runs work headless (CI, servers).

## Tutorial mode

`marketflows/tutorial/data.py` loads:
- `coingecko_market_caps.csv` (long form)
- `meta.json` (`symbols`, `narrative_assets`)
- `config.toml`

Tutorial mode exists to prove installation + end-to-end outputs without needing API keys.