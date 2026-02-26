"""
Run pipeline to query providers, analyze data, and create graphs.
"""

import pickle
from pathlib import Path

import pandas as pd

from marketflows.analysis.aggregates import (
    aggregate_cap_ranges,
    aggregate_groups,
    create_master_df,
    prepare_cap_ranges,
)
from marketflows.analysis.metrics import (
    calculate_group_metrics,
    calculate_range_metrics,
)
from marketflows.config import (
    AnalysisConfig,
    PlotConfig,
    ProviderConfig,
    load_and_validate_config,
)
from marketflows.plots.charts import plot_charts
from marketflows.plots.tables import create_category_tables
from marketflows.providers._credentials import read_api_key
from marketflows.providers.coingecko import (
    define_frequency_min_and_max_timestamp,
    load_coingecko_data,
)
from marketflows.types import FlowType

# render_outputs


# run_pipeline
def change_this_name_and_add_docstring() -> None:

    provider_config, analysis_config, plot_config = load_and_validate_config(
        Path("config.toml")
    )

    # REPLACE WITH SECRETS TOML
    api_key_path = Path.cwd() / "PRIVATE" / "api_key.txt"  # ERASE THIS LINE!!!

    api_key = read_api_key(api_key_path)

    # set current time

    # set last time: find_last_time_all

    # list comprehension: for each flow type plot all graphs and tables: render_outputs

    # set now

    # cycle if interval has not passed yet

    # reread config
    if provider_config.provider:
        coin_mcs, symbols, narrative_coins = load_coingecko_data(
            api_key=api_key, provider_config=provider_config
        )
        import pickle

        with open("market_data.pkl", "wb") as f:
            pickle.dump(coin_mcs, f)
            pickle.dump(symbols, f)
            pickle.dump(narrative_coins, f)
    else:
        with open("market_data.pkl", "rb") as f:
            coin_mcs = pickle.load(f)
            symbols = pickle.load(f)
            narrative_coins = pickle.load(f)

    freq, min_timestamp, max_timestamp = define_frequency_min_and_max_timestamp(
        provider_config
    )

    df_master = create_master_df(
        coin_mcs, freq=freq, min_timestamp=min_timestamp, max_timestamp=max_timestamp
    )

    # set df_base with data for base assets except USD
    if provider_config.base_assets:
        base_assets_minus_dollar = provider_config.base_assets.copy()
        if "us-dollar" in base_assets_minus_dollar:
            base_assets_minus_dollar.remove("us-dollar")
        df_base = df_master[base_assets_minus_dollar]
    else:
        df_base = None

    if "narratives" in provider_config.flow_types and provider_config.narratives:
        df_narratives = _analyze_group_data(
            group_assets=narrative_coins,
            df_master=df_master,
            base_assets=provider_config.base_assets,
            df_base=df_base,
            analysis_config=analysis_config,
        )

        _create_plots_and_charts(
            flow_type="narratives",
            category="Narratives",
            groups=provider_config.narratives,
            symbols=symbols,
            base_assets=provider_config.base_assets,
            provider_config=provider_config,
            analysis_config=analysis_config,
            plot_config=plot_config,
            df=df_narratives,
        )

    if (
        "individual_assets" in provider_config.flow_types
        and provider_config.asset_groups
    ):
        # create a chart and table for each group of assets
        # (e.g. one person's portfolio)
        assets_dfs = dict()  # create dict of dfs for each asset group
        for group, asset_list in provider_config.asset_groups.items():
            assets_dfs[group] = df_master[asset_list]

            df_assets = _analyze_group_data(
                df_groups=assets_dfs[group],
                group_assets=None,
                df_master=df_master,
                base_assets=provider_config.base_assets,
                df_base=df_base,
                analysis_config=analysis_config,
            )

            _create_plots_and_charts(
                flow_type="individual_assets",
                category=group,
                groups=provider_config.asset_groups[group],
                symbols=symbols,
                base_assets=provider_config.base_assets,
                provider_config=provider_config,
                analysis_config=analysis_config,
                plot_config=plot_config,
                df=df_assets,
            )

        # create a chart and table for all groups of assets (e.g. stocks vs. metals)
        asset_groups = {  # create dict of sets of assets
            key: set(values) for key, values in provider_config.asset_groups.items()
        }

        df_groups = _analyze_group_data(
            group_assets=asset_groups,
            df_master=df_master,
            base_assets=provider_config.base_assets,
            df_base=df_base,
            analysis_config=analysis_config,
        )

        _create_plots_and_charts(
            flow_type="individual_assets",
            category="Portfolios",
            groups=list(provider_config.asset_groups),
            symbols=symbols,
            base_assets=provider_config.base_assets,
            provider_config=provider_config,
            analysis_config=analysis_config,
            plot_config=plot_config,
            df=df_groups,
        )

    if (
        "market_cap_ranges" in provider_config.flow_types
        and provider_config.range_lower_limits
    ):
        df_ranges_long = prepare_cap_ranges(
            range_lower_limits=provider_config.range_lower_limits, df_master=df_master
        )
        df_ranges = aggregate_cap_ranges(
            df_long=df_ranges_long, bucket_column="lower_limit"
        )

        df_ranges = calculate_range_metrics(
            df_master=df_master,
            df_ranges=df_ranges,
            df_long=df_ranges_long,
            provider_config=provider_config,
            analysis_config=analysis_config,
        )

        _create_plots_and_charts(
            flow_type="market_cap_ranges",
            category="Ranges",
            groups=[str(x) for x in provider_config.range_lower_limits],
            symbols=symbols,
            base_assets=provider_config.base_assets,
            provider_config=provider_config,
            analysis_config=analysis_config,
            plot_config=plot_config,
            df=df_ranges,
        )


def _analyze_group_data(
    *,
    df_groups: pd.DataFrame | None = None,
    group_assets: dict[str, set[str]] | None,
    df_master: pd.DataFrame,
    base_assets: list[str],
    df_base: pd.DataFrame | None = None,
    analysis_config: AnalysisConfig,
) -> pd.DataFrame:
    """Analyze group data."""
    if df_groups is None:
        df_groups = aggregate_groups(group_assets=group_assets, df_master=df_master)
    else:
        df_groups = df_groups.copy()

    df_groups = calculate_group_metrics(
        base_assets=base_assets,
        df_base=df_base,
        df_groups=df_groups,
        analysis_config=analysis_config,
    )

    return df_groups


def _create_plots_and_charts(
    *,
    flow_type: FlowType,
    category: str,
    groups: list[str],
    symbols: dict[str, str],
    base_assets: list[str],
    provider_config: ProviderConfig,
    analysis_config: AnalysisConfig,
    plot_config: PlotConfig,
    df: pd.DataFrame,
) -> None:
    """Create plot and charts for given data."""
    plot_charts(
        flow_type=flow_type,
        category=category,
        groups=groups,
        symbols=symbols,
        base_assets=base_assets,
        analysis_config=analysis_config,
        df=df,
    )

    create_category_tables(
        flow_type=flow_type,
        category=category,
        groups=groups,
        symbols=symbols,
        provider_config=provider_config,
        plot_config=plot_config,
        df=df,
    )
