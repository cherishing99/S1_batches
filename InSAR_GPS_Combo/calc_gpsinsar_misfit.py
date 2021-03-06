# August 2020 
# Calculate the misfit between a geocoded InSAR velocity field and a GPS velocity field 
# that has been projected into the Line of Sight
# Also make a 1-to-1 plot of LOS velocities

import numpy as np
import matplotlib.pyplot as plt
import netcdf_read_write
import los_projection_tools


def top_level_driver(gps_los_file, geocoded_insar_file, plotname):
    [gps_los_velfield, xarray, yarray, LOS_array] = inputs(gps_los_file, geocoded_insar_file);
    insar_array, gps_array, rms_misfit = compute(gps_los_velfield, xarray, yarray, LOS_array);
    one_to_one_plot(insar_array, gps_array, rms_misfit, plotname)
    return;


def inputs(gps_los_file, geocoded_insar_file):
    print("Reading files %s and %s for calculating misfit." % (gps_los_file, geocoded_insar_file));
    [gps_los_velfield] = los_projection_tools.input_gps_as_los(gps_los_file);
    [xarray, yarray, LOS_array] = netcdf_read_write.read_netcdf4_xyz(geocoded_insar_file);
    if np.nanmean(xarray) > 180:
        xarray = np.subtract(xarray, 360);  # some files come in with 244 instead of -115.  Fixing that.
    return [gps_los_velfield, xarray, yarray, LOS_array];


def compute(gps_los_velfield, xarray, yarray, LOS_array):
    insar_array, gps_array = los_projection_tools.paired_gps_geocoded_insar(gps_los_velfield, xarray, yarray, LOS_array,
                                                                            window_pixels=15);
    misfit_array = np.subtract(insar_array, gps_array);
    rms_misfit = np.sqrt(np.mean(misfit_array ** 2));
    print("Results: RMS Misfit Between these two fields is %f mm/yr at %d GPS stations \n" % (rms_misfit, len(insar_array)));
    return insar_array, gps_array, rms_misfit;


def one_to_one_plot(insar_array, gps_array, rms_misfit, plotname):
    plt.figure(figsize=(9, 9), dpi=300);
    plt.plot(gps_array, insar_array, '.', markersize=10);
    bottom_level = -5;
    top_level = 35;
    plt.plot([bottom_level, top_level], [bottom_level, top_level], '--k');
    plt.xlim([bottom_level, top_level])
    plt.ylim([bottom_level, top_level])
    plt.grid(True)
    plt.xlabel('GNSS LOS Velocity (mm/yr)', fontsize=18);
    plt.ylabel('InSAR LOS Velocity (mm/yr)', fontsize=18);
    plt.gca().tick_params(axis='both', labelsize=16);
    plt.title('InSAR vs GNSS Velocities, RMS=%.3fmm/yr' % (rms_misfit), fontsize=18);
    plt.savefig(plotname);
    plt.close();
    return;
