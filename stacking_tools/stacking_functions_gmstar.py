import sys
from subprocess import call
import stacking_utilities
import sentinel_utilities
import nsbas_accessing
import Super_Simple_Stack as sss
import coseismic_stack
import stack_corr


# --------------- STEP 0: Setting up ------------ # 
def set_up_output_directories(config_params):
    if config_params.startstage > 0:
        return;
    if config_params.endstage < 0:
        return;
    print("\nStart Stage 0 - Setting up output directories");
    call(['mkdir', '-p', config_params.ts_output_dir], shell=False);
    print('calling: mkdir -p %s' % config_params.ts_output_dir);
    call(['cp', 'stacking.config', config_params.ts_output_dir], shell=False);
    print('calling: cp stacking.config %s' % config_params.ts_output_dir);
    call(['cp', config_params.skip_file, config_params.ts_output_dir], shell=False);
    print("End Stage 0 - Setting up output directories (%s) \n" % config_params.ts_output_dir);
    return;


# --------------- STEP 1: Make corrections ------------ # 
def make_corrections(config_params):
    if config_params.startstage > 1:  # if we're starting after, we don't do this.
        return;
    if config_params.endstage < 1:  # if we're ending at intf, we don't do this.
        return;
    print("Start Stage 1 - optional atm corrections");
    # This is where we would implement GACOS, APS, topo-detrending, or unwrapping errors if we had them. 
    print("End Stage 1 - optional atm corrections\n");
    return;


# --------------- STEP 2: Get Reference Pixel ------------ # 

def get_ref(config_params):
    if config_params.startstage > 2:  # if we're starting after, we don't do this.
        return;
    if config_params.endstage < 2:  # if we're ending at intf, we don't do this.
        return;

    print("Start Stage 2 - Finding Files and Reference Pixel");

    # Very general, takes all files and doesn't discriminate. 
    intf_files, _ = stacking_utilities.get_list_of_intf_all(config_params);

    # Here we need to get ref_idx if we don't have it already
    rowref, colref = stacking_utilities.get_ref_index(config_params.ref_loc, config_params.ref_idx,
                                                      config_params.geocoded_intfs, intf_files);

    print("End Stage 2 - Finding Files and Reference Pixel\n");

    return;


# --------------- STEP 3: Velocities and Time Series! ------------ # 
def vels_and_ts(config_params):
    if config_params.startstage > 3:  # if we're starting after, we don't do this.
        return;
    if config_params.endstage < 3:  # if we're ending at intf, we don't do this.
        return;

    print("Start Stage 3 - Velocities and Time Series");
    call(['cp', 'stacking.config', config_params.ts_output_dir], shell=False);

    # This is where the hand-picking takes place: manual excludes, long intfs only, ramp-removed, atm-removed, etc.
    intf_files, corr_files = stacking_utilities.make_selection_of_intfs(config_params);
    stacking_utilities.make_igram_plot(config_params, intf_files);

    # Plumbing stuff
    rowref = int(config_params.ref_idx.split('/')[0]);
    colref = int(config_params.ref_idx.split('/')[1]);

    # Make signal_spread here. Should do this for real, now that excludes have taken place
    # stack_corr.drive_signal_spread_calculation(corr_files, 0.1, config_params.ts_output_dir, config_params.signal_spread_filename);
    # stack_corr.dummy_signal_spread(intf_files, config_params.ts_output_dir, config_params.signal_spread_filename);

    # If we're using DEM error, then we pass in the baseline table. Otherwise we pass None.
    baseline_file = None;
    if config_params.dem_error:
        baseline_file=config_params.baseline_file;

    if config_params.ts_type == "STACK":
        print("\nRunning velocities by simple stack.")
        sss.drive_velocity_simple_stack(intf_files, config_params.wavelength, rowref, colref,
                                        config_params.ts_output_dir);
    if config_params.ts_type == "COSEISMIC":
        print("\nMaking a simple coseismic stack");
        coseismic_stack.drive_coseismic_stack_gmtsar(intf_files, config_params.wavelength, rowref, colref,
                                                     config_params.ts_output_dir);
    if config_params.ts_type == "SBAS":
        print("\nRunning velocities and time series by SBAS: SBAS currently broken. ");
    if config_params.ts_type == "NSBAS":
        print("\nRunning velocities and time series by NSBAS");
        # nsbas_accessing.drive_velocity_gmtsar(intf_files, config_params.nsbas_min_intfs, config_params.sbas_smoothing,
        #                                       config_params.wavelength, rowref, colref, config_params.ts_output_dir,
        #                                       config_params.signal_spread_filename, baseline_file=baseline_file);
        # nsbas_accessing.drive_point_ts_gmtsar(intf_files, config_params.ts_points_file, config_params.sbas_smoothing,
        #                                       config_params.wavelength, rowref, colref, config_params.ts_output_dir,
        #                                       baseline_file=baseline_file, geocoded_flag=config_params.geocoded_intfs);
        # nsbas_accessing.drive_full_TS_gmtsar(intf_files, config_params.nsbas_min_intfs, config_params.sbas_smoothing,
        #                                      config_params.wavelength, rowref, colref, config_params.ts_output_dir,
        #                                      config_params.signal_spread_filename, baseline_file=baseline_file);
        nsbas_accessing.make_vels_from_ts_grids(config_params.ts_output_dir, geocoded=config_params.geocoded_intfs);
    if config_params.ts_type == "WNSBAS":
        print("\nRunning velocities and time series by WNSBAS");
        # nsbas_accessing.drive_velocity_gmtsar(intf_files, config_params.nsbas_min_intfs, config_params.sbas_smoothing,
        #                                       config_params.wavelength, rowref, colref, config_params.ts_output_dir,
        #                                       config_params.signal_spread_filename, coh_files=corr_files);
        nsbas_accessing.drive_point_ts_gmtsar(intf_files, config_params.ts_points_file, config_params.sbas_smoothing,
                                              config_params.wavelength, rowref, colref, config_params.ts_output_dir,
                                              coh_files=coh_files);
        # nsbas_accessing.drive_full_TS_gmtsar(intf_files, config_params.nsbas_min_intfs, config_params.sbas_smoothing,
        #                                      config_params.wavelength, rowref, colref, config_params.ts_output_dir,
        #                                      config_params.signal_spread_filename, coh_files=corr_files);

    print("End Stage 3 - Velocities and Time Series\n");
    return;


# --------------- STEP 4: Geocoding Velocities ------------ # 
def geocode_vels(config_params):
    if config_params.startstage > 4:  # if we're starting after, we don't do this.
        return;
    if config_params.endstage < 4:  # if we're ending at intf, we don't do this.
        return;

    print("Start Stage 4 - Geocoding");

    directory = config_params.ts_output_dir

    # vel_name = "velo_nsbas"
    # outfile=open("geocoding.txt",'w');
    # outfile.write("#!/bin/bash\n");
    # outfile.write("# Script to geocode velocities.\n\n");
    # outfile.write("cd F"+str(config_params.swath)+"\n");
    # outfile.write("geocode_mod.csh "+vel_name+".grd "+vel_name+"_ll.grd "+vel_name+"_ll "+directory+"\n");
    # outfile.close();
    # print("Ready to call geocoding.txt.")
    # call("chmod +x geocoding.txt",shell=True);
    # call("./geocoding.txt",shell=True); 

    # Then, quickly geocode all the time series files. 
    # Call from the processing directory
    # filelist = glob.glob("/Volumes/Ironwolf/Track_71/stacking/no_smoothing_shortintfs/combined/*.grd");
    # datestrs = get_datestrs();
    # for i in range(len(datestrs)):
    #     call(["quick_geocode.csh", "stacking/no_smoothing_shortintfs/combined", "merged", datestrs[i] + ".grd",
    #           datestrs[i] + "_ll"], shell=False);

    print("End Stage 4 - Geocoding");
    return;

    # For later plotting, we want to project available GPS into LOS. 
    # gps_into_LOS.top_level_driver(config_params, rowref, colref);
