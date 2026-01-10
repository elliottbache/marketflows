# plot_all_graphs (don't read data, it should be passed in)

    # for i in category

        # if category in which_graphs

            # plot_type_graphs

# plot_type_graphs

    # define orders

    # create filename list: create_filename_list

    # for i in normalizations

        # if i not in which_graphs, continue

        # for j in orders

            # if i, j not in which_graphs, continue

            # define variable to reduce graph time range depending on order: define_graph_origin

            # for k in EMA

                # if i, j, k not in which_graphs, continue

                # for m in series

                    # define label for legend in plot

                    # define marker for series

                    # define column name: define_column_name

                    # make sure that data to be graphed falls within dataframe datetime range

                    # define x: current_plot_data

                    # define y: current_plot_data

                    # save mins and maxes to scale graph

                    # find min and max for last 25% of graph

                    # beautify the x-labels

                    # set max and min y axis