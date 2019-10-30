# This is in Python

import numpy as np 
import matplotlib.pyplot as plt 
import collections
import glob, sys, math
import datetime as dt 
from subprocess import call
import netcdf_read_write
import sentinel_utilities


# ------------- CONFIGURE ------------ # 
def configure(config_params, staging_directory):

	# Time Series parameters
	smoothing = config_params.sbas_smoothing;  
	out_dir=config_params.ts_output_dir;
	outfile_writer=out_dir+'/velocity_writer';  # a text file where we write nsbas results in case the program crashes. 

	# Setting up the input and output directories. 
	[file_names, intf_pairs]=get_nsbas_intfs(staging_directory, config_params.skip_file);
	call(['mkdir','-p',out_dir],shell=False);

	sentinel_utilities.make_network_plot(intf_pairs, [],[],[], 'Selected_Network_Geometry.eps'); # will read from the raw/baseline_table.dat file. 
	print("Performing NSBAS on %d files in %s " % (len(file_names), staging_directory));

	return [file_names, config_params.nsbas_min_intfs, smoothing, config_params.wavelength, outfile_writer, out_dir];


def get_nsbas_intfs(staging_directory, skip_file):
	# The purpose of this function is to remove the interferograms manually selected for exclusion. 
	# They will be placed in a separate folder called 'noisy'. 
	# First remove interferograms from the manual_remove.txt file. 
	
	intf_pairs=[];
	ifile=open(skip_file,'r');
	for line in ifile:
		intf_pairs.append(line.split()[0]);
	ifile.close();

	# Set up the noisy directory, and move everything inside back into staging dir. 
	noisy_dir=staging_directory+'/noisy';
	call(['mkdir','-p',noisy_dir],shell=False);
	tempfiles = glob.glob(noisy_dir+"/*_*_unwrap.grd");
	for item in tempfiles:
		call(['mv',item,staging_directory],shell=False);

	# Move all noisy files into a noisy directory. 
	file_names_total=glob.glob(staging_directory+"/*_*_unwrap.grd");
	for item in file_names_total:
		for intf in intf_pairs:
			if intf in item:
				call(['mv',item,noisy_dir],shell=False);
				print('mv '+item+' '+noisy_dir);

	file_names_clean=glob.glob(staging_directory+"/*_*_unwrap.grd");
	if len(file_names_clean)==0:
		print("Error! No files matching search pattern within "+staging_directory); sys.exit(1);
	clean_intf_pairs=[];
	for item in file_names_clean:
		imname=item.split('/')[-1];
		im1=imname[0:7]
		im2=imname[8:15]
		clean_intf_pairs.append(im1+':'+im2);
	return [file_names_clean, clean_intf_pairs]; 


# ------------- INPUTS ------------ # 
def inputs(file_names, config_params):

	[xdata,ydata] = netcdf_read_write.read_grd_xy(file_names[0]);
	data_all=[];
	date_pairs=[];
	dates=[];
	start_dt = dt.datetime.strptime(str(config_params.start_time),"%Y%m%d");
	end_dt = dt.datetime.strptime(str(config_params.end_time),"%Y%m%d");

	for ifile in file_names:  # this happens to be in date order on my mac
		pairname=ifile.split('/')[-1][0:15];
		image1=pairname.split('_')[0];
		image2=pairname.split('_')[1];
		image1_dt = dt.datetime.strptime(image1,"%Y%j");
		image2_dt = dt.datetime.strptime(image2,"%Y%j");
		if image1_dt>=start_dt and image1_dt<= end_dt:
			if image2_dt>=start_dt and image2_dt <= end_dt:
				data = netcdf_read_write.read_grd(ifile);
				data_all.append(data);
				date_pairs.append(pairname);  # returning something like '2016292_2016316' for each intf
				dates.append(image1);
				dates.append(image2);
	dates=list(set(dates));
	dates=sorted(dates);
	print(dates);
	print("Reading %d interferograms from %d acquisitions. " % (len(date_pairs), len(dates) ) );
	return [xdata, ydata, data_all, dates, date_pairs];




# ------------ COMPUTE ------------ #
def compute(xdata, ydata, zdata_all, nsbas_good_num, dates, date_pairs, smoothing, wavelength, outfile_writer):
	[zdim, xdim, ydim] = np.shape(zdata_all);
	number_of_datas=np.zeros([xdim, ydim]);
	vel=np.zeros([xdim,ydim]);
	# [number_of_datas] = analyze_coherent_number(zdata_all);  # commented for debugging. 
	number_of_datas=np.zeros([xdim,ydim]);

	vel = analyze_velocity_nsbas(zdata_all, number_of_datas, nsbas_good_num, dates, date_pairs, smoothing, wavelength, outfile_writer);
	return [vel,number_of_datas,zdim];


def analyze_coherent_number(zdata):
	# Analyze the number of coherent acquisitions for each pixel
	print("Analyzing the number of coherent interferograms per pixel.")
	[zdim, xdim, ydim] = np.shape(zdata)
	number_of_datas=np.zeros([xdim,ydim]);
	for k in range(zdim):
		for i in range(xdim):
			for j in range(ydim):
				if not math.isnan(zdata[k][i][j]):
					number_of_datas[i][j]=number_of_datas[i][j]+1;

	plt.figure();
	plt.imshow(number_of_datas);
	plt.savefig('number_of_datas.eps');

	return [number_of_datas];



def analyze_velocity_nsbas(zdata, number_of_datas, nsbas_good_num, dates, date_pairs, smoothing, wavelength, outfile_writer):
	# The point here is to loop through each pixel, determine if there's enough data to use, and then 
	# make an SBAS matrix describing each image that's a real number (not nan). 
	print("Analyzing the nsbas timeseries per pixel.")
	outfile=open(outfile_writer,'w');
	[zdim, xdim, ydim] = np.shape(zdata)
	vel = np.zeros([xdim, ydim]);
	
	nsbas_good_num=-2;  # for debugging. 

	for i in range(xdim):  # A loop through each pixel. 
		for j in range(ydim):

	# for i in range(124,127):
		# for j in range(296,299):
			pixel_value = [zdata[k][i][j] for k in range(zdim)];  # slicing the values of phase for a pixel across the various interferograms
			
			if number_of_datas[i][j] >= nsbas_good_num:  # If we have a pixel that will be analyzed: Do SBAS
				print("%d %d " % (i, j) )

				vel[i][j] = do_nsbas_pixel(pixel_value, dates, date_pairs, smoothing, wavelength); 
				outfile.write("%d %d %f\n" % (i, j, vel[i][j]) );
				# print(vel[i][j]);
				# sys.exit(0)
				# pixel_value: if we have 62 intf, this is a (62,) array of the phase values in each interferogram. 
				# dates: if we have 35 images, this is the date of each image
				# date_pairs: if we have 62 intf, this is a (62) list with the image pairs used in each image
				# This solves Gm = d for the movement of the pixel with smoothing. 

			else:
				vel[i][j]=np.nan;

	outfile.close();

	return vel;



def do_nsbas_pixel(pixel_value, dates, date_pairs, smoothing, wavelength):
	# pixel_value: if we have 62 intf, this is a (62,) array of the phase values in each interferogram. 
	# dates: if we have 35 images, this is the date of each image
	# date_pairs: if we have 62 intf, this is a (62) list with the image pairs used in each image	
	# for x in range(len(dates)-1):

	d = np.array([]);
	dates=sorted(dates);
	date_pairs_used=[];
	for i in range(len(pixel_value)):
		if not math.isnan(pixel_value[i]):
			d = np.append(d, pixel_value[i]);  # removes the nans from the computation. 
			date_pairs_used.append(date_pairs[i]);  # might be a slightly shorter array of which interferograms actually got used. 
	model_num=len(dates)-1;

	G = np.zeros([len(date_pairs_used)+model_num-1, model_num]);  # in one case, 91x35
	# print(np.shape(G));
	
	for i in range(len(d)):  # building G matrix line by line. 
		ith_intf = date_pairs_used[i];
		first_image=ith_intf.split('_')[0]; # in format '2017082'
		second_image=ith_intf.split('_')[1]; # in format '2017094'
		first_index=dates.index(first_image);
		second_index=dates.index(second_image);
		for j in range(second_index-first_index):
			G[i][first_index+j]=1;

	# Building the smoothing matrix with 1, -1 pairs
	for i in range(len(date_pairs_used),len(date_pairs_used)+model_num-1):
		position=i-len(date_pairs_used);
		G[i][position]=1*smoothing;
		G[i][position+1]=-1*smoothing;
		d = np.append(d,0);

	# solving the SBAS linear least squares equation for displacement between each epoch. 
	m = np.linalg.lstsq(G,d)[0];  

	# modeled_data=np.dot(G,m);
	# plt.figure();
	# plt.plot(d,'.b');
	# plt.plot(modeled_data,'.--g');
	# plt.savefig('d_vs_m.eps')
	# plt.close();

	# Adding up all the displacement. 
	m_cumulative=[];
	m_cumulative.append(0);
	for i in range(len(m)):
		m_cumulative.append(np.sum(m[0:i]));  # The cumulative phase from start to finish! 


	# Solving for linear velocity
	x_axis_datetimes=[dt.datetime.strptime(x,"%Y%j") for x in dates];
	x_axis_days=[(x - x_axis_datetimes[0]).days for x in x_axis_datetimes];  # number of days since first acquisition. 

	x=np.zeros([len(x_axis_days),2]);
	y=np.array([]);
	for i in range(len(x_axis_days)):
		x[i][0]=x_axis_days[i];
		x[i][1]=1;  
		y=np.append(y,[m_cumulative[i]]);
	model_slopes = np.linalg.lstsq(x,y)[0];  # units: phase per day. 
	model_line = [model_slopes[1]+ x*model_slopes[0] for x in x_axis_days];

	# Velocity conversion: units in mm / year
	vel=model_slopes[0];  # in radians per day
	vel=vel*wavelength*365.24/2.0/(2*np.pi);

	# plt.figure();
	# plt.plot(x_axis_days[0:-1],m,'b.');
	# plt.plot(x_axis_days,m_cumulative,'g.');
	# plt.plot(x_axis_days, model_line,'--g');
	# plt.xlabel("days");
	# plt.ylabel("cumulative phase");
	# plt.text(0,0,str(vel)+"mm/yr slope");
	# plt.savefig('m_model.eps');
	# plt.close();

	# if vel>1000:
	# 	vel=1000;
	# if vel<-1000:
	# 	vel=-1000;

	return vel;







# ------------ COMPUTE ------------ #
def outputs(xdata, ydata, number_of_datas, zdim, vel, out_dir):
	
	netcdf_read_write.produce_output_netcdf(xdata, ydata, number_of_datas, 'coherent_intfs', out_dir+'/number_of_datas.grd');
	netcdf_read_write.flip_if_necessary(out_dir+'/number_of_datas.grd');
	netcdf_read_write.produce_output_plot(out_dir+'/number_of_datas.grd', "Number of Coherent Intfs (Total = "+str(zdim)+")", out_dir+'/number_of_coherent_intfs.eps', 'intfs');
	geocode(out_dir+'/number_of_datas.grd',out_dir);

	netcdf_read_write.produce_output_netcdf(xdata,ydata, vel, 'mm/yr', out_dir+'/vel.grd');
	netcdf_read_write.flip_if_necessary(out_dir+'/vel.grd');
	geocode(out_dir+'/vel.grd',out_dir);


	# Visualizing the velocity field in a few different ways. 
	zdata2=np.reshape(vel, [len(xdata)*len(ydata), 1])
	zdata2=sentinel_utilities.remove_nans_array(zdata2);
	plt.figure();
	plt.hist(zdata2,bins=80);
	plt.gca().set_yscale('log');
	plt.title('Pixels by Velocity: mean=%.2fmm/yr, sdev=%.2fmm/yr' % (np.mean(zdata2), np.std(zdata2)) )
	plt.ylabel('Number of Pixels');
	plt.xlabel('LOS velocity (mm/yr)')
	plt.grid('on');
	plt.savefig(out_dir+'/velocity_hist_log.png');
	plt.close();

	plt.figure();
	plt.gca().set_yscale('linear');
	plt.title('Pixels by Velocity: mean=%.2fmm/yr, sdev=%.2fmm/yr' % (np.mean(zdata2), np.std(zdata2)) )
	plt.hist(zdata2,bins=80);
	plt.ylabel('Number of Pixels');
	plt.xlabel('LOS velocity (mm/yr)')
	plt.grid('on');
	plt.savefig(out_dir+'/velocity_hist_lin.png');
	plt.close();


	plt.figure(figsize=(8,10));
	plt.imshow(vel,aspect=0.5,cmap='jet',vmin=-30, vmax=30);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([]);
	plt.title("Velocity");
	plt.gca().set_xlabel("Range",fontsize=16);
	plt.gca().set_ylabel("Azimuth",fontsize=16);
	cb = plt.colorbar();
	cb.set_label("mm/yr", size=16);
	plt.savefig(out_dir+"/vel_cutoff.png");
	plt.close();

	plt.figure(figsize=(8,10));
	plt.imshow(vel,aspect=0.5,cmap='jet',vmin=-150, vmax=150);
	plt.gca().invert_yaxis()
	plt.gca().invert_xaxis()
	plt.gca().get_xaxis().set_ticks([]);
	plt.gca().get_yaxis().set_ticks([]);
	plt.title("Velocity");
	plt.gca().set_xlabel("Range",fontsize=16);
	plt.gca().set_ylabel("Azimuth",fontsize=16);
	cb = plt.colorbar();
	cb.set_label("mm/yr", size=16);
	plt.savefig(out_dir+"/vel.png");
	plt.close();


	return;




def geocode(ifile, directory):
	# geocode: needs vel.grd, vel_ll.grd, vel_ll, and directory 
	stem = ifile.split('/')[-1]  # format: vel.grd
	stem = stem.split('.')[0]   # format: vel
	call(['geocode_mod.csh',stem+'.grd',stem+'_ll.grd',stem+"_ll",directory],shell=False);
	return;



# ------------ THE MAIN PROGRAM------------ # 

def do_nsbas(config_params, staging_directory):
	[file_names, nsbas_good_num, smoothing, wavelength, outfile_writer, out_dir] = configure(config_params, staging_directory);
	[xdata, ydata, data_all, dates, date_pairs] = inputs(file_names, config_params);
	[vel, number_of_datas, zdim] = compute(xdata, ydata, data_all, nsbas_good_num, dates, date_pairs, smoothing, wavelength, outfile_writer);
	outputs(xdata, ydata, number_of_datas, zdim, vel, out_dir);
