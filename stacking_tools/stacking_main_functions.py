import collections
import os,sys,shutil,argparse,time,configparser, glob
import numpy as np
from subprocess import call, check_output
import stacking_utilities
import unwrapping_errors
import aps 
import detrend_atm_topo
import flattentopo_driver
import phasefilt_plot
import sbas
import nsbas
import gps_into_LOS
import Super_Simple_Stack as sss
import netcdf_read_write as rwr
import stack_corr

Params=collections.namedtuple('Params',['config_file','SAT','wavelength','swath','startstage','endstage','ref_swath','ref_loc','ref_idx',
    'ts_type','solve_unwrap_errors','detrend_atm_topo','gacos','aps','sbas_smoothing','nsbas_min_intfs',
    'start_time','end_time','intf_timespan','gps_file','flight_angle','look_angle','skip_file','ref_dir','ts_points_file',
    'ts_parent_dir','ts_output_dir']);

def read_config():
    ################################################
    # Stage 0: Read and check config parameters
    #
    # read command line arguments and parse config file.
    parser = argparse.ArgumentParser(description='Run stack processing. ')
    parser.add_argument('config',type=str,help='supply name of config file to setup processing options. Required.')
    parser.add_argument('--debug',action='store_true',help='Print extra debugging messages (default: false)')
    args = parser.parse_args()

    # read config file
    config=configparser.ConfigParser()
    config.optionxform = str #make the config file case-sensitive
    config.read(args.config)

    # get options from config file
    config_file_orig=args.config;
    SAT=config.get('py-config','satellite')
    wavelength=config.getfloat('py-config','wavelength')
    swath=config.get('py-config','swath') 
    startstage=config.getint('py-config','startstage')
    endstage=config.getint('py-config','endstage')
    ref_swath=config.get('py-config','ref_swath')
    ref_loc=config.get('py-config','ref_loc')
    ref_idx=config.get('py-config','ref_idx')
    ts_type=config.get('py-config','ts_type')
    solve_unwrap_errors = config.getint('py-config','solve_unwrap_errors');
    gacos = config.getint('py-config','gacos');
    aps = config.getint('py-config','aps');
    detrend_atm_topo = config.getint('py-config','detrend_atm_topo');
    nsbas_min_intfs=config.getint('py-config','nsbas_min_intfs');
    sbas_smoothing = config.getfloat('py-config','sbas_smoothing');
    start_time = config.getint('py-config','start_time');
    end_time = config.getint('py-config','end_time');
    intf_timespan = config.get('py-config','intf_timespan');
    gps_file = config.get('py-config','gps_file');
    flight_angle = config.getfloat('py-config','flight_angle');
    look_angle = config.getfloat('py-config','look_angle');
    skip_file = config.get('py-config','skip_file');
    ts_points_file = config.get('py-config','ts_points_file');
    ref_dir = config.get('py-config','ref_dir');
    ts_parent_dir = config.get('py-config','ts_parent_dir');
    ts_output_dir = config.get('py-config','ts_output_dir');

    print("Running velocity and time series processing, starting with stage %d" % startstage);
            
    # enforce startstage <= endstage
    if endstage < startstage:
        print('Warning: endstage is less than startstage. Setting endstage = startstage.')
        endstage = startstage

    config_params=Params(config_file=config_file_orig,SAT=SAT,wavelength=wavelength,swath=swath,startstage=startstage,endstage=endstage,
        ref_swath=ref_swath,ref_loc=ref_loc,ref_idx=ref_idx,ts_type=ts_type,solve_unwrap_errors=solve_unwrap_errors,
        detrend_atm_topo=detrend_atm_topo,gacos=gacos,aps=aps,sbas_smoothing=sbas_smoothing,nsbas_min_intfs=nsbas_min_intfs,
        start_time=start_time,end_time=end_time,intf_timespan=intf_timespan, gps_file=gps_file,flight_angle=flight_angle,look_angle=look_angle,
        skip_file=skip_file,ts_points_file=ts_points_file,ref_dir=ref_dir,ts_parent_dir=ts_parent_dir,ts_output_dir=ts_output_dir);

    return config_params; 


# --------------- STEP 0: Setting up ------------ # 
def set_up_output_directories(config_params):
    if config_params.startstage>0:  
        return;
    if config_params.endstage<0:   
        return;
    call(['mkdir','-p','F'+config_params.swath+'/'+config_params.ts_parent_dir],shell=False);
    call(['mkdir','-p','F'+config_params.swath+'/'+config_params.ref_dir],shell=False);
    call(['mkdir','-p','F'+config_params.swath+'/'+config_params.ts_output_dir],shell=False);
    call(['cp','stacking.config','F'+config_params.swath+'/'+config_params.ts_output_dir],shell=False);
    return;


# --------------- STEP 1: Make corrections ------------ # 
def make_corrections(config_params):
    if config_params.startstage>1:  # if we're starting after, we don't do this. 
        return;
    if config_params.endstage<1:   # if we're ending at intf, we don't do this. 
        return;    
    # This is where we would implement GACOS, detrending, other atmospheric corrections, or unwrapping errors. 
    # Step 3A: Solve or exclude unwrapping errors
    # Step 3B: Try APS-based atmospheric correction
    # Step 3C: Detrend topo-correlated atmosphere   
    # if config_params.solve_unwrap_errors:
    #     #unwrapping_errors.main_function(prior_staging_directory, post_staging_directory, rowref, colref, config_params.start_time, config_params.end_time);
    # if config_params.gacos:
    #     #gacos.main_function(prior_staging_directory, post_staging_directory, rowref, colref, config_params.start_time, config_params.end_time);
    # if config_params.aps:
    #     # aps.main_function(prior_staging_directory, post_staging_directory, rowref, colref, config_params.start_time, config_params.end_time,'');
    # if config_params.detrend_atm_topo:
    #     detrend_atm_topo.main_function(prior_staging_directory, post_staging_directory, rowref, colref, config_params.start_time, config_params.end_time);
    return;


# --------------- STEP 2: Make ref_unwrap.grd ------------ # 

def collect_unwrap_ref(config_params):
    if config_params.startstage>2:  # if we're starting after, we don't do this. 
        return;
    if config_params.endstage<2:   # if we're ending at intf, we don't do this. 
        return;

    # Very general, takes all files and doesn't discriminate. 
    intf_files=stacking_utilities.get_list_of_intf_all(config_params);

    # Here we need to get ref_idx if we don't have it already
    rowref, colref = stacking_utilities.get_ref_index(config_params.ref_swath, config_params.swath, config_params.ref_loc, config_params.ref_idx);

    # Now we coalesce the files and reference them to the right value/pixel
    stacking_utilities.make_referenced_unwrapped(intf_files, config_params.swath, config_params.ref_swath, rowref, colref, config_params.ref_dir);

    return;


# --------------- STEP 3: Velocities and Time Series! ------------ # 
def vels_and_ts(config_params):
    if config_params.startstage>3:  # if we're starting after, we don't do this. 
        return;
    if config_params.endstage<3:   # if we're ending at intf, we don't do this. 
        return;

    # This is where the hand-picking takes place. 
    # Ex: manual excludes, manual selects, long intfs only, ramp-removed, atm-removed, etc. 
    intfs = stacking_utilities.make_selection_of_intfs(config_params);
    
    # We make signal_spread here. Can be commented if you already have it. 
    # stack_corr.drive_signal_spread_calculation(config_params.swath, config_params.ref_dir, intfs, config_params.ts_output_dir);

    if config_params.ts_type=="STACK":
        print("Running velocities by simple stack.")
        sss.drive_velocity_simple_stack(config_params.swath, intfs, config_params.wavelength, config_params.ts_output_dir);
    if config_params.ts_type=="SBAS":
        print("Running velocities and time series by SBAS");
        # sbas.drive_velocity_sbas(config_params.swath, intfs, config_params.sbas_smoothing, config_params.wavelength, config_params.ts_output_dir);
        # sbas.drive_ts_sbas(config_params);
    if config_params.ts_type=="NSBAS":
        # print("Running velocities and time series by NSBAS");
        # nsbas.drive_velocity_nsbas(config_params.swath, intfs, config_params.nsbas_min_intfs, config_params.sbas_smoothing, config_params.wavelength, config_params.ts_output_dir);
        nsbas.drive_ts_nsbas(config_params);

    return; 


# --------------- STEP 4: Geocoding Velocities ------------ # 
def geocode_vels(config_params):
    if config_params.startstage>4:  # if we're starting after, we don't do this. 
        return;
    if config_params.endstage<4:   # if we're ending at intf, we don't do this. 
        return; 

    directory = config_params.ts_output_dir
    vel_name = "velo_nsbas"

    outfile=open("geocoding.txt",'w');
    outfile.write("#!/bin/bash\n");
    outfile.write("# Script to geocode velocities.\n\n");
    outfile.write("cd F"+str(config_params.swath)+"\n");
    outfile.write("geocode_mod.csh "+vel_name+".grd "+vel_name+"_ll.grd "+vel_name+"_ll "+directory+"\n");
    outfile.close();
    print("Ready to call geocoding.txt.")
    call("chmod +x geocoding.txt",shell=True);
    call("./geocoding.txt",shell=True); 
    
    return; 


    # For later plotting, we want to project available GPS into LOS. 
    # gps_into_LOS.top_level_driver(config_params, rowref, colref);



