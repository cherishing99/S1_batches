# The purpose of this plot is to read baseline tables
# And give a visual tool to determine which are the best 
# one-year interferograms to make. 

import numpy as np
import matplotlib.pyplot as plt
import sentinel_utilities


def top_level_driver():
    baselinefile = 'baseline_table.dat';
    intf_file = 'intf_initial.in';
    intf_file_out = 'intf_record.in';

    crit_days = 30;  # days
    crit_baseline = 20;  # meters

    [stems, times, baselines, missiondays] = sentinel_utilities.read_baseline_table(baselinefile);
    intf_pairs_initial = sentinel_utilities.read_intf_table(intf_file);
    intf_pairs_initial = list(intf_pairs_initial);

    # Computing new pairs.
    new_intfs = compute_new_pairs(stems, times, baselines, crit_days, crit_baseline);

    # Combining the existing and new interferogram lists.
    all_intfs = intf_pairs_initial + new_intfs;

    # Outputs
    sentinel_utilities.make_network_plot(all_intfs, stems, times, baselines, 'network_plot.png');
    sentinel_utilities.write_intf_table(all_intfs, intf_file_out);
    return;


def compute_new_pairs(stems, times, baselines, crit_days, crit_baseline, num_years=1):
    crit_theta = 2 * np.pi * (crit_days / 365.25);  # days
    count = 0;

    times_dict = {};
    days_dict = {};
    radius_dict = {};
    theta_dict = {};
    color_dict = {};
    r_points = [];
    th_points = [];
    new_intfs = [];
    color_order = 'bgrkc';

    # Build the dictionaries of data
    for i in range(len(times)):
        year = str(times[i])[0:4];
        day = str(times[i])[4:7];
        theta = 2 * np.pi * float(day) / 365.25;
        radius = baselines[i] - min(baselines);

        if year not in days_dict:
            times_dict[year] = [];
            days_dict[year] = [];
            radius_dict[year] = [];
            theta_dict[year] = [];
            color_dict[year] = color_order[len(color_dict)];

        times_dict[year].append(times[i]);
        days_dict[year].append(day);
        radius_dict[year].append(radius);
        theta_dict[year].append(theta);

    # Find candidate interferograms.
    year_list = sorted(set(times_dict));

    for i in range(len(
            year_list) - num_years):  # Looking for interferograms that are close in baseline and time (in the next year)
        this_year = year_list[i];
        next_year = year_list[i + num_years];
        for j in range(len(radius_dict[this_year])):  # for each year
            for k in range(len(radius_dict[next_year])):  # for the next year

                if abs(radius_dict[this_year][j] - radius_dict[next_year][k]) < crit_baseline:
                    if abs(theta_dict[this_year][j] - theta_dict[next_year][k]) < crit_theta:
                        count = count + 1;
                        # print("%f %f %f meters" % (times_dict[this_year][j],times_dict[next_year][k],abs(radius_dict[this_year][j]-radius_dict[next_year][k])) );
                        # We have a close pair.
                        indx1 = np.where(times == times_dict[this_year][j]);
                        indx2 = np.where(times == times_dict[next_year][k]);
                        stem1 = stems[indx1[0][0]];  # oct 2019 added a second [0]
                        stem2 = stems[indx2[0][0]];
                        r_points.append([radius_dict[this_year][j], radius_dict[next_year][k]]);
                        th_points.append([theta_dict[this_year][j], theta_dict[next_year][k]]);
                        new_intf = stem1 + ':' + stem2;
                        new_intfs.append(new_intf);  # FOUND NEW INTERFEROGRAM!

    print("Year-long: Returning %d %d-year-long interferograms within %.1f days and %.1f meters" % (
    count, num_years, crit_days, crit_baseline));

    rose_plot(times_dict, days_dict, radius_dict, theta_dict, color_dict, r_points, th_points);

    return new_intfs;


def rose_plot(times_dict, days_dict, radius_dict, theta_dict, color_dict, r_points, th_points):
    # Make the polar plot.
    plt.figure();
    dots = [];
    for myyear in sorted(radius_dict):
        dots.append(plt.polar(theta_dict[myyear], radius_dict[myyear], '.', color=color_dict[myyear], label=myyear));

    # The new connections we plan to make.
    for i in range(len(r_points)):
        plt.polar(th_points[i], r_points[i], color='black', linewidth=0.4);

    # Optional: A code to put labels on individual days in the rose plot.
    # labelyear='2017';
    # for i in range(len(days_dict[labelyear])):
    # 	plt.annotate(days_dict[labelyear][i],xy=(theta_dict[labelyear][i],radius_dict[labelyear][i]),fontsize=6,color=color_dict[labelyear]);

    plt.legend(loc=4);
    plt.savefig('roseplot.eps');
    return;
