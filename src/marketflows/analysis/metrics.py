# tie together all metrics functions: calculate_metrics

#   decide which derivatives to use: part of plot_type_graphs

#   for i in series

#       normalize by time: initialize_plot_data or whatever is done with normalizing by now

#   for i in base_tokens

#       normalize series with base token

#       for j in derivatives

#           for k in moving averages

#               calculate moving averages (see prepare_plot_data)

#   return dict with all combinations and data
