"""
Run pipeline to query providers, analyze data, and create graphs.
"""

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
    get_provider_credentials,
    load_and_validate_config,
)
from marketflows.plots.charts import plot_charts
from marketflows.plots.tables import create_category_tables
from marketflows.providers.coingecko import (
    define_frequency_min_and_max_timestamp,
    load_coingecko_data,
)
from marketflows.types import FlowType


def run_pipeline(
    *, secrets_path: Path | None = None, config_path: Path | None = None
) -> None:
    """Run complete pipeline for querying provider, analyzing data, and plotting."""

    if secrets_path is None:
        secrets_path = Path.cwd() / Path("secrets.toml")
    if config_path is None:
        config_path = Path.cwd() / Path("config.toml")

    provider_config, analysis_config, plot_config = load_and_validate_config(
        config_path
    )

    api_key = get_provider_credentials(
        provider_config.provider, secrets_path=secrets_path
    )
    if not api_key:
        raise FileNotFoundError(f"API key was not correctly read from: {secrets_path}.")

    asset_mcs, symbols, narrative_assets = load_coingecko_data(
        api_key=api_key, provider_config=provider_config
    )

    freq, min_timestamp, max_timestamp = define_frequency_min_and_max_timestamp(
        provider_config
    )

    df_master = create_master_df(
        asset_mcs, freq=freq, min_timestamp=min_timestamp, max_timestamp=max_timestamp
    )

    # set df_base with data for base assets except USD
    base_assets_minus_dollar = [
        a for a in provider_config.base_assets if a != "us-dollar"
    ]
    df_base = df_master[base_assets_minus_dollar] if base_assets_minus_dollar else None

    if "narratives" in provider_config.flow_types and provider_config.narratives:
        df_narratives = _analyze_group_data(
            group_assets=narrative_assets,
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
        for group, asset_list in provider_config.asset_groups.items():

            df_assets = _analyze_group_data(
                df_groups=df_master[asset_list],
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
        if not group_assets:
            raise ValueError("Provide df_groups or group_assets.")
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
