"""
Run pipeline to query providers, analyze data, and create graphs.
"""
from marketflows.credentials import read_api_key

# render_outputs

# run_pipeline

    # read config: load_and_validate_config

    # read API key from file: read_api_key
    api_key = read_api_key(api_key_path)

    # set current time

    # set last time: find_last_time_all

    # list comprehension: for each flow type plot all graphs and tables: render_outputs

    # infinite loop

        # set now

        # cycle if interval has not passed yet

        # reread config

        # if is_query: for each type of data series (individual assets, market cap ranges, narratives)

            # query data
                # if Coingecko: store_coingecko_data
                # else: raise

            # analyze data
                # aggregate data: aggregate_data
                # calculate metrics: calculate_metrics

        # list comprehension: for each flow type plot all graphs and tables: render_outputs

        # exit if is_once

        # sleep for 4 hours

        # reset last_time
