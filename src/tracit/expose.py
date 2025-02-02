#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Created on Tue Jun 29 16:30:38 2021

@author: emil

.. todo::
	* Look at autocorrelation plot.

	* Where should autocorr, chains, and corner be?

	* GP in orbit plot -- should also be shown/subtracted from other plots
		
"""
# =============================================================================
# tracit modules
# =============================================================================

from .business import lc_model, rv_model, ls_model, ls_model2, localRV_model, get_binned, Gauss, RM_path, inv2Gauss
cyfy = 0
if cyfy:
	from .cdynamic import *#time2phase, total_duration
else:
	from .dynamics import *#time2phase, total_duration

# =============================================================================
# external modules
# =============================================================================
import matplotlib.pyplot as plt
from matplotlib.gridspec import GridSpec
from matplotlib.ticker import MultipleLocator

import numpy as np
import lmfit
#import celerite

from scipy import interpolate
from scipy.optimize import curve_fit
from scipy.signal import savgol_filter

from astropy.timeseries import LombScargle

def time2phase(time,per,T0):
	'''Convert time to phase.

	Phase centered on the reference time, i.e., from -0.5 to 0.5.

	:param time: Times to convert.
	:type time: array
	:param per: Period.
	:type per: float
	:param T0: Reference time (mid-transit time).
	:type T0: float

	:return: Phase.
	:rtype: array

	'''
	phase = ((time-T0)%per)/per
	for ii in range(len(phase)):
		if phase[ii] > 0.5: phase[ii] = phase[ii] - 1
	return phase



# def run_exp():
# #def run_exp(tex=True):
# 	#global plot_tex

# 	#plot_tex = tex

# 	global colors
# 	colors = {
# 		'b' : 'C3',
# 		'c' : 'C4',
# 		'd' : 'C5',
# 		'e' : 'C0',
# 		'f' : 'C1',
# 		'g' : 'C2',
# 		'h' : 'C6',
# 		'i' : 'C8'
# 	}


# =============================================================================
# Radial velocity curve
# =============================================================================

#def plot_orbit(param_fname,data_fname,updated_pars=None,
def plot_orbit(parameters,data,updated_pars=None,
	savefig=False,path='',save_res=False,OC_rv=True,n_pars=0,usetex=False,**kwargs):
	'''Plot the radial velocity curve.

	:param parameters: The parameters. See :py:class:`tracit.structure.par_struct`.
	:type parameters: dict

	:param data: The data. See :py:class:`tracit.structure.dat_struct`.
	:type data: dict

	:param savefig: Whether to save the figure. Default ``True``.
	:type savefig: bool, optional

	:param path: Where to save the figure. Default ''.
	:type path: str, optional

	:param best_fit: Whether to use best-fit as opposed to median from MCMC. Default ``True``.
	:type best_fit: bool, optional

	:param n_pars: Number of fitting parameters to use for reduced chi-squared calculation. Default 0. If 0 they will be grabbed from **updated_pars**.
	:type n_pars: int, optional

	'''
	plt.rc('text',usetex=usetex)

	font = 15
	plt.rc('xtick',labelsize=3*font/4)
	plt.rc('ytick',labelsize=3*font/4)


	bms = 6.0 # background markersize
	fms = 4.0 # foreground markersize
	RM_path()
	#business.data_structure(data_fname)
	#business.params_structure(param_fname)

	# if updated_pars is not None:
	# 	pars = parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	idx = 1
	# 	if (updated_pars.shape[0] > 3) & best_fit: idx = 4
	# 	for par in pars:
	# 		print(parameters[par]['Value'])
	# 		try:
	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass
	if n_pars == 0: n_pars = len(parameters['FPs'])
	n_rv = data['RVs']
	pls = parameters['Planets']


	if n_rv >= 1:
		aa = [parameters['a{}'.format(ii)]['Value'] for ii in range(1,3)]
		fig = plt.figure(figsize=(12,6))
		ax = fig.add_subplot(211)
		axoc = fig.add_subplot(212)


		times, rvs, rv_errs = np.array([]), np.array([]), np.array([])
		for nn in range(1,n_rv+1):
			arr = data['RV_{}'.format(nn)]
			time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
			times, rvs, rv_errs = np.append(times,time), np.append(rvs,rv), np.append(rv_errs,rv_err)

		zp = np.amin(times)

		RMs = []
		m_rvs = np.array([])
		for nn in range(1,n_rv+1):
			plot_gp = data['GP RV_{}'.format(nn)]
			if plot_gp: ntimes = np.linspace(min(time),max(time),500)
			label = data['RV_label_{}'.format(nn)]
			arr = data['RV_{}'.format(nn)]
			time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
			v0 = parameters['RVsys_{}'.format(nn)]['Value']
			rv -= v0
			jitter = parameters['RVsigma_{}'.format(nn)]['Value']
			jitter_err = np.sqrt(rv_err**2 + jitter**2)
			
			#chi2scale = data['Chi2 RV_{}'.format(nn)]
			#jitter_err *= chi2scale

			drift = aa[1]*(time-zp)**2 + aa[0]*(time-zp)
			if plot_gp: gp_drift = aa[1]*(ntimes-zp)**2 + aa[0]*(ntimes-zp)
			RM = data['RM RV_{}'.format(nn)]
			RMs.append(RM)
			mnrv = np.zeros(len(time))
			if plot_gp: gp_mnrv = np.zeros(len(ntimes))
			for pl in pls: 
				mnrv += rv_model(time,n_planet=pl,n_rv=nn,RM=RM)
				if plot_gp: 
					gp_mnrv += rv_model(ntimes,n_planet=pl,n_rv=nn,RM=RM)




			ax.errorbar(time,rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
			ax.errorbar(time,rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
			axoc.errorbar(time,rv-drift-mnrv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
			axoc.errorbar(time,rv-drift-mnrv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
			if save_res: 
				rarr = np.zeros(shape=(len(time),3))
				rarr[:,0] = time
				rarr[:,1] = rv-drift-mnrv
				rarr[:,2] = rv_err
				np.savetxt(path+'RV{}_res.txt'.format(nn),rarr)

			if plot_gp:
				#time = time.copy()*24*3600
				gp_fig = plt.figure(figsize=(12,6))
				ax_gp = gp_fig.add_subplot(111)
				
				gp_list = []
				gp_type = data['GP type RV_{}'.format(nn)]
				if gp_type == 'SHO':
					pass
				else:
					loga = parameters['RV_{}_GP_log_a'.format(nn)]['Value']
					logc = parameters['RV_{}_GP_log_c'.format(nn)]['Value']
					gp_list = [loga,logc]

				jitter = 1
				if jitter:
					gp_list.append(parameters['RVlogsigma_{}'.format(nn)]['Value'])

				# gp = data['RV_{} GP'.format(nn)]
				# gp_pars = parameters['GP pars RV_{}'.format(nn)]
				# gp_list = []

				# for gpar in gp_pars:
				# 	gp_list.append(parameters[gpar]['Value'])
				print(gp_list)
				gp = data['RV_{} GP'.format(nn)]
				gp.set_parameter_vector(np.array(gp_list))
				gp.compute(time,rv_err)
				#print(gp.get_parameter_vector())
				#print(gp.get_parameter_vector())

				#gp = data['RV_{} GP'.format(nn)]
				#gp_pars = parameters['GP pars RV_{}'.format(nn)]
				#gp_list = []

				#for gpar in gp_pars:
				#	gp_list.append(parameters[gpar]['Value'])


				#print(gp_list)
				#gp.set_parameter_vector(np.array(gp_list))
				#gp.compute(time-min(time),jitter_err)

				res_rv = rv-drift-mnrv

				#ax_gp.errorbar(time-min(time),res_rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
				#ax_gp.errorbar(time-min(time),res_rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
				
				ax_gp.errorbar(time,res_rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
				ax_gp.errorbar(time,res_rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))


				off = 0.0

				#t_poor = np.linspace(0.0,max(time)-min(time),500)
				t_poor = np.linspace(min(time),max(time),500)
				mup, varp = gp.predict(res_rv, t_poor, return_var=True)
				ax_gp.plot(t_poor,mup+off,color='k',lw=2.0,zorder=7,alpha=0.2)


				gap = 0.3#/(24*3600)
				dls = np.where(np.diff(time) > gap)[0]
				start = 0
				for dl in dls:
					#t_lin = np.linspace(min(time[start:int(dl+1)])-min(time)-gap/2,max(time[start:int(dl+1)])-min(time)+gap/2,500)
					t_lin = np.linspace(min(time[start:int(dl+1)])-gap/2,max(time[start:int(dl+1)])+gap/2,500)
					mu, var = gp.predict(res_rv, t_lin, return_var=True)
					std = np.sqrt(var)
					#ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=6.0,color='k',linestyle='none')
					#ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')
					# gp_mnrv = np.zeros(len(t_lin))
					# for pl in pls: 
					# 	gp_mnrv += rv_model(t_lin,n_planet=pl,n_rv=nn,RM=RM)
					# gp_drift = aa[1]*(t_lin-zp)**2 + aa[0]*(t_lin-zp)
					# #print(gp_mnrv)
					# off = gp_drift+gp_mnrv

					ax_gp.fill_between(t_lin, mu+std+off, mu-std+off, color='C7', alpha=0.9, edgecolor="none",zorder=6)
					ax_gp.plot(t_lin,mu+off,color='k',lw=2.0,zorder=7)
					ax_gp.plot(t_lin,mu+off,color='w',lw=1.0,zorder=7)

					#ax_gp.plot(t_lin,off,color='k',linestyle='--')
					#ax_gp.plot(t_lin,mu,color='k',linestyle='--')

					#murv, v = gp.predict(res_rv, time[start:int(dl+1)]-min(time), return_var=True)
					murv, v = gp.predict(res_rv, time[start:int(dl+1)], return_var=True)
					rv[start:int(dl+1)] -= murv
					# if any(~np.isfinite(murv)):
					# 	ax_gp.plot(t_lin,mu+off,color='r',lw=2.0,zorder=7)
					# 	#ax_gp.plot(t_lin,mu+off,color='r',marker='*',markersize=50)
					# 	print(murv,len(time[start:int(dl+1)]))

					start = int(dl + 1)
				#t_lin = np.linspace(min(time[start:])-min(time),max(time[start:])-min(time),500)
				t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
				mu, var = gp.predict(res_rv, t_lin, return_var=True)
				std = np.sqrt(var)
				
				murv, v = gp.predict(res_rv, time[start:], return_var=True)
				#murv, v = gp.predict(res_rv, time[start:]-min(time), return_var=True)
				rv[start:] -= murv

				# gptime = time.copy()*24*3600
				# gp_fig = plt.figure(figsize=(12,6))
				# ax_gp = gp_fig.add_subplot(111)



				# gp = data['RV_{} GP'.format(nn)]
				# gp_pars = parameters['GP pars RV_{}'.format(nn)]
				# gp_list = []

				# for gpar in gp_pars:
				# 	gp_list.append(parameters[gpar]['Value'])


				# print(gp_list)
				# gp.set_parameter_vector(np.array(gp_list))
				# gp.compute(gptime-min(gptime),jitter_err)

				# res_rv = rv-drift-mnrv

				# ax_gp.errorbar(gptime-min(gptime),res_rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
				# ax_gp.errorbar(gptime-min(gptime),res_rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
				#-min(time)
				# t_poor = np.linspace(0.0,max(gptime)-min(gptime),500)
				# mup, varp = gp.predict(res_rv, t_poor, return_var=True)
				# ax_gp.plot(t_poor,mup+off,color='k',lw=2.0,zorder=7,alpha=0.2)


				# gap = 0.3#/(24*3600)
				# dls = np.where(np.diff(time) > gap)[0]
				# start = 0
				# for dl in dls:
				# 	t_lin = np.linspace(min(gptime[start:int(dl+1)])-min(gptime)-gap/2,max(gptime[start:int(dl+1)])-min(gptime)+gap/2,500)
				# 	mu, var = gp.predict(res_rv, t_lin, return_var=True)
				# 	std = np.sqrt(var)
				# 	#ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=6.0,color='k',linestyle='none')
				# 	#ax_gp.plot(time[start:i[-7, -0.7, -30]nt(dl+1)],fl[start:int(dl+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')
				# 	# gp_mnrv = np.zeros(len(t_lin))
				# 	# for pl in pls: 
				# 	# 	gp_mnrv += rv_model(t_lin,n_planet=pl,n_rv=nn,RM=RM)
				# 	# gp_drift = aa[1]*(t_lin-zp)**2 + aa[0]*(t_lin-zp)
				# 	# #print(gp_mnrv)
				# 	# off = gp_drift+gp_mnrv

				# 	ax_gp.fill_between(t_lin, mu+std+off, mu-std+off, color='C7', alpha=0.9, edgecolor="none",zorder=6)
				# 	ax_gp.plot(t_lin,mu+off,color='k',lw=2.0,zorder=7)
				# 	ax_gp.plot(t_lin,mu+off,color='w',lw=1.0,zorder=7)

				# 	#ax_gp.plot(t_lin,off,color='k',linestyle='--')
				# 	#ax_gp.plot(t_lin,mu,color='k',linestyle='--')

				# 	murv, v = gp.predict(res_rv, gptime[start:int(dl+1)]-min(gptime), return_var=True)
				# 	rv[start:int(dl+1)] -= murv
				# 	# if any(~np.isfinite(murv)):
				# 	# 	ax_gp.plot(t_lin,mu+off,color='r',lw=2.0,zorder=7)
				# 	# 	#ax_gp.plot(t_lin,mu+off,color='r',marker='*',markersize=50)
				# 	# 	print(murv,len(time[start:int(dl+1)]))

				# 	start = int(dl + 1)
				# t_lin = np.linspace(min(gptime[start:])-min(gptime),max(gptime[start:])-min(gptime),500)
				# mu, var = gp.predict(res_rv, t_lin, return_var=True)
				# std = np.sqrt(var)
				
				# murv, v = gp.predict(res_rv, gptime[start:]-min(gptime), return_var=True)
				# rv[start:] -= murv
				#print(any(~np.isfinite(murv)))

				# freq = np.linspace(0, 10, 200)#*1e-6
				# freq = np.append(freq,np.linspace(10, 1500, 2000))#*1e-6
				# omega = freq*2*np.pi*1e-6
				# figw = plt.figure()
				# axw = figw.add_subplot(111)
				# #axr = figw.add_subplot(212)
				# axw.loglog(frf, PSDf,color='C1',zorder=-10)
				# axw.loglog(fr, PSD,zorder=-1,color='C7')
				
				# lc = make_lc('gamCep2',time,res_rv)
				# psd = ps2.powerspectrum(lc,weights=rv_err)
				# fr2, PSD2 = psd.powerspectrum()
				# PSD2 *= 1e6
				# axw.loglog(fr2, PSD2,color='k')
				# axw.loglog(freq, gp.kernel.get_psd(omega),color='k',lw=3.0)
				# axw.loglog(freq, gp.kernel.get_psd(omega),color='w',lw=2.0)
				# for n, term in enumerate(gp.kernel.terms):
				# 	axw.loglog(freq, term.get_psd(omega))

				#axr.plot(time,rv,ls='none')
				# gp_mnrv = np.zeros(len(t_lin))
				# for pl in pls: 
				# 	gp_mnrv += rv_model(t_lin,n_planet=pl,n_rv=nn,RM=RM)
				# gp_drift = aa[1]*(t_lin-zp)**2 + aa[0]*(t_lin-zp)
				# off = gp_drift+gp_mnrv

				ax_gp.fill_between(t_lin, mu+std+off, mu-std+off, color='C7', alpha=0.9, edgecolor="none",zorder=6)
				ax_gp.plot(t_lin,mu+off,color='k',lw=2.0,zorder=7)
				ax_gp.plot(t_lin,mu+off,color='w',lw=1.0,zorder=7)



				ax_gp.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
				ax_gp.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)

				if savefig: gp_fig.savefig(path+'rv_{}_GP.pdf'.format(nn))

			#print(mnrv,rv)
			print('## Spectroscopic system {}/{} ##:'.format(nn,label))
			red_chi2 = np.sum((rv-drift-mnrv)**2/jitter_err**2)/(len(rv)-n_pars)
			print('\nReduced chi-squared for the radial velocity curve is:\n\t {:.03f}'.format(red_chi2))
			#print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
			print('Number of data points: {}'.format(len(rv)))
			print('Number of fitting parameters: {}'.format(n_pars))
			print('#########################'.format(nn))

		calc_RM = any(RMs)

		npoints = 50000
		unp_m = np.linspace(min(times)-10.,max(times)+10.,npoints)

		step = 100
		ivals = [(n,n+step) for n in np.arange(0,npoints,step)]
		rv_m_unp = np.zeros(len(unp_m))
		for ival in ivals:
			tt = unp_m[ival[0]:ival[1]]
			for pl in pls: 
				rv_m_unp[ival[0]:ival[1]] += rv_model(tt,n_planet=pl,n_rv=nn,RM=calc_RM)
				rv_m_unp[ival[0]:ival[1]] += aa[1]*(tt-zp)**2 + aa[0]*(tt-zp)

		ax.errorbar(unp_m,rv_m_unp,color='k',lw=1.)
		ax.errorbar(unp_m,rv_m_unp,color='C7',lw=0.5)
		ax.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
		axoc.axhline(0.0,linestyle='--',color='C7',zorder=-2)
		axoc.set_ylabel(r'$\rm O-C \ (m/s)$',fontsize=font)
		axoc.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)
		ax.set_xticks([])
		ax.legend(bbox_to_anchor=(0, 1.2, 1, 0),ncol=n_rv)
		axoc.set_xlim(ax.get_xlim())
		fig.subplots_adjust(hspace=0.0)
		if savefig: fig.savefig(path+'rv_unphased.pdf',bbox_inches='tight')

		rv_TTV = data['RV_{} TTVs'.format(nn)]
		for pl in pls:

			pl_TTV = 0
			if pl in parameters['TTVs']:
				pl_TTV = 1

			#print(pl_TTV,pl)
			if pl_TTV & rv_TTV:
				t0_storage = parameters['T0_{}'.format(pl)]['Value']
				#t0 = parameters['T0_{}'.format(pl)]['Value']
				## HARDCODED FIX THIS
				## Will probably not work for data sets spanning 'multiple epochs'
				ns, nus = data['RV_{}_{}_n'.format(pl,nn)]#data['LC_{}_n'.format(nn)] ## all ns and unique ns
				for nu in nus:
					t0 = parameters['T0_{}_{}'.format(pl,nu)]['Value']# + parameters['TTV_{}:T0_{}'.format(pl,nu)]['Value']
					parameters['T0_{}'.format(pl)]['Value'] = t0
					per = parameters['P_{}'.format(pl)]['Value']
					#t0 = parameters['T0_{}'.format(pl)]['Value']
					aR = parameters['a_Rs_{}'.format(pl)]['Value']
					rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
					inc = parameters['inc_{}'.format(pl)]['Value']
					ecc = parameters['e_{}'.format(pl)]['Value']
					ww = parameters['w_{}'.format(pl)]['Value']
					K = parameters['K_{}'.format(pl)]['Value']
					dur = total_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)*24
					if np.isfinite(dur): x1, x2 = -1*dur/2-1.0,dur/2+1.0
					else: x1, x2 = -3.0,3.0



					RMs = []
					for nn in range(1,n_rv+1):
						RM = data['RM RV_{}'.format(nn)]
						RMs.append(RM)
					calc_RM = any(RMs)
					if calc_RM and np.isfinite(dur):
						figrm = plt.figure()
						axrm = figrm.add_subplot(211)
						axrm_oc = figrm.add_subplot(212)
					elif K == 0.0:
						continue

					figpl = plt.figure()
					axpl = figpl.add_subplot(211)
					axpl_oc = figpl.add_subplot(212)


					rmoc_maxys = np.array([])
					rmoc_minys = np.array([])
					for nn in range(1,n_rv+1):
						try:
							t0n = parameters['Spec_{}:T0_{}'.format(nn,pl)]['Value']
							parameters['T0_{}'.format(pl)]['Value'] = t0n				
						except KeyError:
							#parameters['T0_{}'.format(pl)]['Value'] = t0
							pass
						label = data['RV_label_{}'.format(nn)]
						arr = data['RV_{}'.format(nn)]
						time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
						v0 = parameters['RVsys_{}'.format(nn)]['Value']
						rv -= v0
						jitter = parameters['RVsigma_{}'.format(nn)]['Value']
						#jitter = np.exp(log_jitter)
						#jitter = log_jitter
						jitter_err = np.sqrt(rv_err**2 + jitter**2)


						drift = aa[1]*(time-zp)**2 + aa[0]*(time-zp)			
						RM = data['RM RV_{}'.format(nn)]
						for pl2 in pls: 
							if pl != pl2:			
								try:
									t0n = parameters['Spec_{}:T0_{}'.format(nn,pl2)]
									parameters['T0_{}'.format(pl)]['Value'] = t0n				
								except KeyError:
									pass
								rv -= rv_model(time,n_planet=pl2,n_rv=nn,RM=RM)
						

						rv -= drift
						#rv2 = rv.copy()
						pp = time2phase(time,per,t0)
						plo = rv_model(time,n_planet=pl,n_rv=nn,RM=RM)
						#axpl.errorbar(pp,rv,yerr=jitter_err,marker='o',markersize=bms,color='C3',linestyle='none',zorder=4)
						#plo = rv_model(time,n_planet=pl,n_rv=nn,RM=RM)
						plot_gp = data['GP RV_{}'.format(nn)]
						if plot_gp:
							#gp_fig = plt.figure(figsize=(12,6))
							#ax_gp = gp_fig.add_subplot(111)
							gp_list = []
							gp_type = data['GP type RV_{}'.format(nn)]
							if gp_type == 'SHO':
								pass
							else:
								loga = parameters['RV_{}_GP_log_a'.format(nn)]['Value']
								logc = parameters['RV_{}_GP_log_c'.format(nn)]['Value']
								gp_list = [loga,logc]

							jitter = 1
							if jitter:
								gp_list.append(parameters['RVlogsigma_{}'.format(nn)]['Value'])

							# gp = data['RV_{} GP'.format(nn)]
							# #gp_type = data['GP type RV_{}'.format(nn)]


							# gp = data['RV_{} GP'.format(nn)]
							# gp_pars = parameters['GP pars RV_{}'.format(nn)]
							# gp_list = []
							# for gpar in gp_pars:
							# 	gp_list.append(parameters[gpar]['Value'])

							gp.set_parameter_vector(np.array(gp_list))
							gp.compute(time-min(time),jitter_err)


							res_rv = rv-plo

							gap = 0.3
							#print(len(off))
							dls = np.where(np.diff(time) > gap)[0]
							start = 0
							#mus = np.array([])
							for dl in dls:
								mu, var = gp.predict(res_rv, time[start:int(dl+1)]-min(time), return_var=True)
								rv[start:int(dl+1)] -= mu

								start = int(dl + 1)
							
							mu, var = gp.predict(res_rv, time[start:]-min(time), return_var=True)
							std = np.sqrt(var)
							#print(rv[start:])
							rv[start:] -= mu

							# #gp_fig = plt.figure(figsize=(12,6))
							# #ax_gp = gp_fig.add_subplot(111)
							# gp = data['RV_{} GP'.format(nn)]
							# #gp_type = data['GP type RV_{}'.format(nn)]


							# gp = data['RV_{} GP'.format(nn)]
							# gp_pars = parameters['GP pars RV_{}'.format(nn)]
							# gp_list = []
							# for gpar in gp_pars:
							# 	gp_list.append(parameters[gpar]['Value'])

							# gp.set_parameter_vector(np.array(gp_list))
							# gp.compute(gptime-min(gptime),jitter_err)



							# res_rv = rv-plo

							# gap = 0.3
							# #print(len(off))
							# dls = np.where(np.diff(time) > gap)[0]
							# start = 0
							# #mus = np.array([])
							# for dl in dls:
							# 	mu, var = gp.predict(res_rv, gptime[start:int(dl+1)]-min(gptime), return_var=True)
							# 	rv[start:int(dl+1)] -= mu

							# 	start = int(dl + 1)
							
							# mu, var = gp.predict(res_rv, gptime[start:]-min(gptime), return_var=True)
							# std = np.sqrt(var)
							# #print(rv[start:])
							# rv[start:] -= mu
						axpl.errorbar(pp,rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
						#axpl.errorbar(pp,rv,yerr=rv_err,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
						axpl.errorbar(pp,rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
						
						axpl_oc.errorbar(pp,rv-plo,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
						#axpl_oc.errorbar(pp,rv-plo,yerr=rv_err,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
						axpl_oc.errorbar(pp,rv-plo,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
						



						if calc_RM and np.isfinite(dur):
							plot = (pp*per*24 > x1) & (pp*per*24 < x2)
							try:

								rv_o = rv_model(time[plot],n_planet=pl,n_rv=nn,RM=False)
								axrm.errorbar(pp[plot]*per*24,rv[plot]-rv_o,yerr=jitter_err[plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
								axrm.errorbar(pp[plot]*per*24,rv[plot]-rv_o,yerr=rv_err[plot],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
								axrm_oc.errorbar(pp[plot]*per*24,rv[plot]-plo[plot],yerr=jitter_err[plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
								axrm_oc.errorbar(pp[plot]*per*24,rv[plot]-plo[plot],yerr=rv_err[plot],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
								rm_maxy = max(rv[plot]-rv_o) + max(jitter_err[plot])
								rm_miny = min(rv[plot]-rv_o) - max(jitter_err[plot])
								rms = np.std(rv[plot]-drift[plot]-plo[plot])
								#print(rms)
								#axrm_oc.text(1.1,13,r'$\rm rms={:0.1f} \ m/s $'.format(rms),bbox=dict(boxstyle="round",
								#															ec='k',fc='none',))


								rmoc_maxy = max(rv[plot]-plo[plot]) + max(jitter_err[plot])
								rmoc_maxys = np.append(rmoc_maxys,rmoc_maxy)
								rmoc_miny = min(rv[plot]-plo[plot]) - max(jitter_err[plot])
								rmoc_minys = np.append(rmoc_minys,rmoc_miny)

								if any(~plot):
									rv_out = rv_model(time[~plot],n_planet=pl,n_rv=nn,RM=False)
									axrm.errorbar(pp[~plot]*per*24,rv[~plot]-drift[~plot]-rv_out,yerr=jitter_err[~plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
									axrm_oc.errorbar(pp[~plot]*per*24,rv[~plot]-drift[~plot]-plo[~plot],yerr=jitter_err[~plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)


							except ValueError:
								#figrm.close()
								calc_RM = False



						
					model_time = np.linspace(t0-0.1,t0+per+0.1,2000)
					model_pp = time2phase(model_time,per,t0)
					rv_m = rv_model(model_time,n_planet=pl,n_rv=nn,RM=calc_RM)
					rv_m_only = rv_model(model_time,n_planet=pl,n_rv=nn,RM=False)

					ss = np.argsort(model_pp)
					axpl.plot(model_pp[ss],rv_m[ss],linestyle='-',color='k',lw=1.5,zorder=6)
					axpl.plot(model_pp[ss],rv_m[ss],linestyle='-',color='C7',lw=1.0,zorder=7)


					axpl_oc.axhline(0.0,linestyle='--',color='C7',zorder=-2)
					axpl_oc.set_xlabel(r'$\rm Orbital \ Phase$',fontsize=font)
					axpl_oc.set_ylabel(r'$\rm O-C \ (m/s)$',fontsize=font)
					axpl.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
					axpl.legend(bbox_to_anchor=(0, 1.2, 1, 0),ncol=n_rv)
					axpl_oc.set_xlim(axpl.get_xlim())
					figpl.subplots_adjust(hspace=0.0)
					if savefig: figpl.savefig(path+'rv_{}_folded_ephemeris_{}.pdf'.format(pl,nu))


					if calc_RM and np.isfinite(dur):

						axrm.plot(model_pp[ss]*per*24,rv_m[ss]-rv_m_only[ss],linestyle='-',color='k',lw=1.5,zorder=6)
						axrm.plot(model_pp[ss]*per*24,rv_m[ss]-rv_m_only[ss],linestyle='-',color='C7',lw=1.0,zorder=7)

						max_model = max(rv_m[ss]-rv_m_only[ss])
						min_model = min(rv_m[ss]-rv_m_only[ss])
						if max_model > rm_maxy: rm_maxy = max_model + 5
						if min_model < rm_miny: rm_miny = min_model - 5


						axrm_oc.axhline(0.0,linestyle='--',color='C7',zorder=-2)
						axrm_oc.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)
						axrm_oc.set_ylabel(r'$\rm O-C \ (m/s)$',fontsize=font)
						axrm.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
						axrm.set_xlim(x1,x2)
						axrm_oc.set_xlim(x1,x2)
						axrm.set_ylim(rm_miny,rm_maxy)
						rmoc_maxy = max(rmoc_maxys)
						rmoc_miny = min(rmoc_minys)
						axrm_oc.set_ylim(rmoc_miny,rmoc_maxy)
						figrm.subplots_adjust(hspace=0.0)
						if savefig: figrm.savefig(path+'rm_{}_transit_{}.pdf'.format(pl,nu))
				parameters['T0_{}'.format(pl)]['Value'] = t0_storage
			else:
				per = parameters['P_{}'.format(pl)]['Value']
				t0 = parameters['T0_{}'.format(pl)]['Value']
				aR = parameters['a_Rs_{}'.format(pl)]['Value']
				rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
				inc = parameters['inc_{}'.format(pl)]['Value']
				ecc = parameters['e_{}'.format(pl)]['Value']
				ww = parameters['w_{}'.format(pl)]['Value']
				K = parameters['K_{}'.format(pl)]['Value']
				dur = total_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)*24
				if np.isfinite(dur): x1, x2 = -1*dur/2-1.0,dur/2+1.0
				else: x1, x2 = -3.0,3.0



				RMs = []
				for nn in range(1,n_rv+1):
					RM = data['RM RV_{}'.format(nn)]
					RMs.append(RM)
				calc_RM = any(RMs)
				if calc_RM and np.isfinite(dur):
					figrm = plt.figure()
					axrm = figrm.add_subplot(211)
					axrm_oc = figrm.add_subplot(212)
				elif K == 0.0:
					continue

				figpl = plt.figure()
				axpl = figpl.add_subplot(211)
				axpl_oc = figpl.add_subplot(212)


				rmoc_maxys = np.array([])
				rmoc_minys = np.array([])
				for nn in range(1,n_rv+1):
					try:
						t0n = parameters['Spec_{}:T0_{}'.format(nn,pl)]['Value']
						parameters['T0_{}'.format(pl)]['Value'] = t0n				
					except KeyError:
						#parameters['T0_{}'.format(pl)]['Value'] = t0
						pass
					label = data['RV_label_{}'.format(nn)]
					arr = data['RV_{}'.format(nn)]
					time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
					v0 = parameters['RVsys_{}'.format(nn)]['Value']
					rv -= v0
					jitter = parameters['RVsigma_{}'.format(nn)]['Value']
					#jitter = np.exp(log_jitter)
					#jitter = log_jitter
					jitter_err = np.sqrt(rv_err**2 + jitter**2)



					drift = aa[1]*(time-zp)**2 + aa[0]*(time-zp)			
					RM = data['RM RV_{}'.format(nn)]
					for pl2 in pls: 
						if pl != pl2:			
							try:
								t0n = parameters['Spec_{}:T0_{}'.format(nn,pl2)]
								parameters['T0_{}'.format(pl)]['Value'] = t0n				
							except KeyError:
								pass
							rv -= rv_model(time,n_planet=pl2,n_rv=nn,RM=RM)
					

					rv -= drift
					#rv2 = rv.copy()
					pp = time2phase(time,per,t0)
					plo = rv_model(time,n_planet=pl,n_rv=nn,RM=RM)
					#axpl.errorbar(pp,rv,yerr=jitter_err,marker='o',markersize=bms,color='C3',linestyle='none',zorder=4)
					#plo = rv_model(time,n_planet=pl,n_rv=nn,RM=RM)
					plot_gp = data['GP RV_{}'.format(nn)]
					if plot_gp:
						#gp_fig = plt.figure(figsize=(12,6))
						#ax_gp = gp_fig.add_subplot(111)
						# gp = data['RV_{} GP'.format(nn)]
						# #gp_type = data['GP type RV_{}'.format(nn)]


						# gp = data['RV_{} GP'.format(nn)]
						# gp_pars = parameters['GP pars RV_{}'.format(nn)]
						# gp_list = []
						# for gpar in gp_pars:
						# 	gp_list.append(parameters[gpar]['Value'])
						# if gp_type == 'SHO':
						# 	#sigma = parameters['RV_{}_GP_sigma'.format(nn)]['Value']
						# 	#tau = parameters['RV_{}_GP_tau'.format(nn)]['Value']
						# 	#rho = parameters['RV_{}_GP_rho'.format(nn)]['Value']
						# 	#gp_list = [sigma,tau,rho]
						# 	S0 = parameters['RV_{}_GP_S0'.format(nn)]['Value']
						# 	Q = parameters['RV_{}_GP_Q'.format(nn)]['Value']
						# 	w0 = parameters['RV_{}_GP_w0'.format(nn)]['Value']


						# 	P = 2*np.pi/(90*24*3600)
						# 	#P = 1000
						# 	a = 8
						# 	#term2 = terms.RealTerm(a=a, c=P)

						# 	P3 = 2*np.pi/(2*24*3600)
						# 	#P = 1000
						# 	a3 = 8
				
						# 	#gp_list = [np.log(S0),np.log(Q),np.log(w0)]
						# 	gp_list = [np.log(S0),np.log(Q),np.log(w0),np.log(a),np.log(P),np.log(a3),np.log(P3)]
						# elif gp_type == 'logSHO':
						# 	log_S0 = parameters['RV_{}_GP_log_S0'.format(nn)]['Value']
						# 	log_Q = parameters['RV_{}_GP_log_Q'.format(nn)]['Value']
						# 	log_w0 = parameters['RV_{}_GP_log_w0'.format(nn)]['Value']
						
						# 	gp_list = [log_S0,log_Q,log_w0]
						# else:
						# 	loga = parameters['RV_{}_GP_log_a'.format(nn)]['Value']
						# 	logc = parameters['RV_{}_GP_log_c'.format(nn)]['Value']
						# 	gp_list = [loga,logc]

						# # gp_types = data['GP type RV_{}'.format(nn)]
						# # gp_list = []
						# # nsho = 1
						# # nlogsho = 1
						# # nreal = 1
						# # for gp_type in gp_types:
						# # 	if gp_type == 'SHO':
						# # 		sigma = parameters['RV_{}_GP_sigma_{}'.format(nn,nsho)]['Value']
						# # 		tau = parameters['RV_{}_GP_tau_{}'.format(nn,nsho)]['Value']
						# # 		rho = parameters['RV_{}_GP_rho_{}'.format(nn,nsho)]['Value']
								
						# # 		gp_list.extend([sigma,tau,rho])
						# # 	elif gp_type == 'logSHO':
						# # 		log_S0 = parameters['RV_{}_GP_log_S0_{}'.format(nn,nlogsho)]['Value']
						# # 		log_Q = parameters['RV_{}_GP_log_Q_{}'.format(nn,nlogsho)]['Value']
						# # 		log_w0 = parameters['RV_{}_GP_log_w0_{}'.format(nn,nlogsho)]['Value']
						# # 		#sigma = np.sqrt(w0*np.exp(log_S0)*Q)
						# # 		#rho = 2*np.pi/w0
						# # 		#tau = 2*Q/w0
						# # 		#gp_list = [log_S0,log_Q,log_w0]
						# # 		gp_list.extend([log_S0,log_Q,log_w0])
						# # 		#gp_list.extend([sigma,rho,tau])
						# # 		#gp.kernel = terms.SHOTerm(sigma=sigma,rho=rho,tau=tau)
						# # 	else:
						# # 		loga = parameters['RV_{}_GP_log_a_{}'.format(nn,nreal)]['Value']
						# # 		logc = parameters['RV_{}_GP_log_c_{}'.format(nn,nreal)]['Value']
						# # 		#gp_list = [loga,logc]
						# # 		gp_list.extend([loga,logc])

						gp_list = []
						gp_type = data['GP type RV_{}'.format(nn)]
						if gp_type == 'SHO':
							pass
						else:
							loga = parameters['RV_{}_GP_log_a'.format(nn)]['Value']
							logc = parameters['RV_{}_GP_log_c'.format(nn)]['Value']
							gp_list = [loga,logc]

						jitter = 1
						if jitter:
							gp_list.append(parameters['RVlogsigma_{}'.format(nn)]['Value'])

						gp.set_parameter_vector(np.array(gp_list))
						gp.compute(time-min(time),jitter_err)



						res_rv = rv-plo

						gap = 0.3
						#print(len(off))
						dls = np.where(np.diff(time) > gap)[0]
						start = 0
						#mus = np.array([])
						for dl in dls:
							mu, var = gp.predict(res_rv, time[start:int(dl+1)]-min(time), return_var=True)
							rv[start:int(dl+1)] -= mu
							#mus = np.append(mus,mu)
							#axpl.plot(pp[start:int(dl+1)],mu)
							#print(time[start:int(dl+1)],start,int(dl+1))
							# t_lin = np.linspace(min(time[start:int(dl+1)]),max(time[start:int(dl+1)]),500)
							# mu, var = gp.predict(res_rv, t_lin, return_var=True)
							# std = np.sqrt(var)
							# #ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=6.0,color='k',linestyle='none')
							# #ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')
							# gp_mnrv = np.zeros(len(t_lin))
							# for pl in pls: 
							# 	gp_mnrv += rv_model(t_lin,n_planet=pl,n_rv=nn,RM=RM)
							# gp_drift = aa[1]*(t_lin-zp)**2 + aa[0]*(t_lin-zp)
							# #print(gp_mnrv)
							# off = gp_drift+gp_mnrv

							# ax_gp.fill_between(t_lin, mu+std+off, mu-std+off, color='C7', alpha=0.9, edgecolor="none",zorder=6)
							# ax_gp.plot(t_lin,mu+off,color='k',lw=2.0,zorder=7)
							# ax_gp.plot(t_lin,mu+off,color='w',lw=1.0,zorder=7)
							
							start = int(dl + 1)
						
						#t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
						#t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
						mu, var = gp.predict(res_rv, time[start:]-min(time), return_var=True)
						std = np.sqrt(var)
						#print(rv[start:])
						rv[start:] -= mu

						# gap = 0.3
						# #print(len(off))
						# dls = np.where(np.diff(time) > gap)[0]
						# start = 0
						# #mus = np.array([])
						# for dl in dls:
						# 	mu, var = gp.predict(res_rv, gptime[start:int(dl+1)]-min(gptime), return_var=True)
						# 	rv[start:int(dl+1)] -= mu
						# 	#mus = np.append(mus,mu)
						# 	#axpl.plot(pp[start:int(dl+1)],mu)
						# 	#print(time[start:int(dl+1)],start,int(dl+1))
						# 	# t_lin = np.linspace(min(time[start:int(dl+1)]),max(time[start:int(dl+1)]),500)
						# 	# mu, var = gp.predict(res_rv, t_lin, return_var=True)
						# 	# std = np.sqrt(var)
						# 	# #ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=6.0,color='k',linestyle='none')
						# 	# #ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')
						# 	# gp_mnrv = np.zeros(len(t_lin))
						# 	# for pl in pls: 
						# 	# 	gp_mnrv += rv_model(t_lin,n_planet=pl,n_rv=nn,RM=RM)
						# 	# gp_drift = aa[1]*(t_lin-zp)**2 + aa[0]*(t_lin-zp)
						# 	# #print(gp_mnrv)
						# 	# off = gp_drift+gp_mnrv

						# 	# ax_gp.fill_between(t_lin, mu+std+off, mu-std+off, color='C7', alpha=0.9, edgecolor="none",zorder=6)
						# 	# ax_gp.plot(t_lin,mu+off,color='k',lw=2.0,zorder=7)
						# 	# ax_gp.plot(t_lin,mu+off,color='w',lw=1.0,zorder=7)
							
						# 	start = int(dl + 1)
						
						# #t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
						# #t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
						# mu, var = gp.predict(res_rv, gptime[start:]-min(gptime), return_var=True)
						# std = np.sqrt(var)
						# #print(rv[start:])
						# rv[start:] -= mu
						#mus = np.append(mus,mu)
						#print(rv[start:])
						#axpl.plot(pp,mus)
						#axpl.plot(pp[start:],mu)
						#mu, var = gp.predict(res_rv, time, return_var=True)
						#rv -= mu
						
						#std = np.sqrt(var)
						#print(mu)
						#rv += plo


					#axpl.errorbar(pp,rv2,yerr=jitter_err,marker='o',markersize=bms,color='C2',linestyle='none',zorder=4)
					#axpl.errorbar(pp,rv-mus,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
					axpl.errorbar(pp,rv,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
					#axpl.errorbar(pp,rv,yerr=rv_err,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
					axpl.errorbar(pp,rv,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
					
					axpl_oc.errorbar(pp,rv-plo,yerr=jitter_err,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
					#axpl_oc.errorbar(pp,rv-plo,yerr=rv_err,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
					axpl_oc.errorbar(pp,rv-plo,yerr=rv_err,marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
					



					if calc_RM and np.isfinite(dur):
						plot = (pp*per*24 > x1) & (pp*per*24 < x2)
						try:

							rv_o = rv_model(time[plot],n_planet=pl,n_rv=nn,RM=False)
							axrm.errorbar(pp[plot]*per*24,rv[plot]-rv_o,yerr=jitter_err[plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
							axrm.errorbar(pp[plot]*per*24,rv[plot]-rv_o,yerr=rv_err[plot],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
							axrm_oc.errorbar(pp[plot]*per*24,rv[plot]-plo[plot],yerr=jitter_err[plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
							axrm_oc.errorbar(pp[plot]*per*24,rv[plot]-plo[plot],yerr=rv_err[plot],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
							rm_maxy = max(rv[plot]-rv_o) + max(jitter_err[plot])
							rm_miny = min(rv[plot]-rv_o) - max(jitter_err[plot])
							rms = np.std(rv[plot]-drift[plot]-plo[plot])
							#print(rms)
							#axrm_oc.text(1.1,13,r'$\rm rms={:0.1f} \ m/s $'.format(rms),bbox=dict(boxstyle="round",
							#															ec='k',fc='none',))


							rmoc_maxy = max(rv[plot]-plo[plot]) + max(jitter_err[plot])
							rmoc_maxys = np.append(rmoc_maxys,rmoc_maxy)
							rmoc_miny = min(rv[plot]-plo[plot]) - max(jitter_err[plot])
							rmoc_minys = np.append(rmoc_minys,rmoc_miny)

							if any(~plot):
								rv_out = rv_model(time[~plot],n_planet=pl,n_rv=nn,RM=False)
								axrm.errorbar(pp[~plot]*per*24,rv[~plot]-drift[~plot]-rv_out,yerr=jitter_err[~plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
								axrm_oc.errorbar(pp[~plot]*per*24,rv[~plot]-drift[~plot]-plo[~plot],yerr=jitter_err[~plot],marker='o',markersize=bms,color='k',linestyle='none',zorder=4)


						except ValueError:
							#figrm.close()
							calc_RM = False



					
				model_time = np.linspace(t0-0.1,t0+per+0.1,2000)
				model_pp = time2phase(model_time,per,t0)
				rv_m = rv_model(model_time,n_planet=pl,n_rv=nn,RM=calc_RM)
				rv_m_only = rv_model(model_time,n_planet=pl,n_rv=nn,RM=False)

				ss = np.argsort(model_pp)
				axpl.plot(model_pp[ss],rv_m[ss],linestyle='-',color='k',lw=1.5,zorder=6)
				axpl.plot(model_pp[ss],rv_m[ss],linestyle='-',color='C7',lw=1.0,zorder=7)


				axpl_oc.axhline(0.0,linestyle='--',color='C7',zorder=-2)
				axpl_oc.set_xlabel(r'$\rm Orbital \ Phase$',fontsize=font)
				axpl_oc.set_ylabel(r'$\rm O-C \ (m/s)$',fontsize=font)
				axpl.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
				axpl.legend(bbox_to_anchor=(0, 1.2, 1, 0),ncol=n_rv)
				axpl_oc.set_xlim(axpl.get_xlim())
				figpl.subplots_adjust(hspace=0.0)
				if savefig: figpl.savefig(path+'rv_{}.pdf'.format(pl),bbox_inches='tight')


				if calc_RM and np.isfinite(dur):

					axrm.plot(model_pp[ss]*per*24,rv_m[ss]-rv_m_only[ss],linestyle='-',color='k',lw=1.5,zorder=6)
					axrm.plot(model_pp[ss]*per*24,rv_m[ss]-rv_m_only[ss],linestyle='-',color='C7',lw=1.0,zorder=7)

					max_model = max(rv_m[ss]-rv_m_only[ss])
					min_model = min(rv_m[ss]-rv_m_only[ss])
					if max_model > rm_maxy: rm_maxy = max_model + 5
					if min_model < rm_miny: rm_miny = min_model - 5


					axrm_oc.axhline(0.0,linestyle='--',color='C7',zorder=-2)
					axrm_oc.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)
					axrm_oc.set_ylabel(r'$\rm O-C \ (m/s)$',fontsize=font)
					axrm.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
					axrm.set_xlim(x1,x2)
					axrm_oc.set_xlim(x1,x2)
					axrm.set_ylim(rm_miny,rm_maxy)
					rmoc_maxy = max(rmoc_maxys)
					rmoc_miny = min(rmoc_minys)
					axrm_oc.set_ylim(rmoc_miny,rmoc_maxy)
					figrm.subplots_adjust(hspace=0.0)
					if savefig: figrm.savefig(path+'rm_{}.pdf'.format(pl),bbox_inches='tight')


# =============================================================================
# Light curve
# =============================================================================


#def plot_lightcurve(param_fname,data_fname,updated_pars=None,savefig=False,
def plot_lightcurve(parameters,data,savefig=False,
	path='',n_pars=0,errorbar=True,best_fit=True,usetex=False,**kwargs):
	'''Plot the light curve.

	Function to plot a light curve
	
	More thorough description

	:param parameters: The parameters. See :py:class:`tracit.structure.par_struct`.
	:type parameters: dict

	:param data: The data. See :py:class:`tracit.structure.dat_struct`.
	:type data: dict

	:param savefig: Whether to save the figure. Default ``True``.
	:type savefig: bool, optional

	:param path: Where to save the figure. Default ''.
	:type path: str, optional

	:param best_fit: Whether to use best-fit as opposed to median from MCMC. Default ``True``.
	:type best_fit: bool, optional

	:param n_pars: Number of fitting parameters to use for reduced chi-squared calculation. Default 0. If 0 they will be grabbed from **updated_pars**.
	:type n_pars: int, optional

	.. todo::
		* The duration check is not working properly for high impact systems (no total duration)
	'''

	plt.rc('text',usetex=usetex)

	font = 15
	plt.rc('xtick',labelsize=3*font/4)
	plt.rc('ytick',labelsize=3*font/4)


	if n_pars == 0: n_pars = len(parameters['FPs'])
	n_phot = data['LCs']
	pls = parameters['Planets']


	if n_phot >= 1:

		npoints = 100000
		fig = plt.figure(figsize=(12,6))
		ax = fig.add_subplot(111)
		#axoc = fig.add_subplot(212)#,sharex=ax)

		time_range = []
		flux_range = []
		for nn in range(1,n_phot+1):
			arr = data['LC_{}'.format(nn)]
			time_range.append(min(arr[:,0]))
			time_range.append(max(arr[:,0]))
			flux_range.append(min(arr[:,1]))
			flux_range.append(max(arr[:,1]))

		times = np.linspace(min(time_range)-3./24.,max(time_range)+3./24.,npoints)
		max_fl = max(flux_range)
		min_fl = min(flux_range)
		off = 0.
		for nn in range(1,n_phot+1):
			arr = data['LC_{}'.format(nn)]
			label = data['LC_label_{}'.format(nn)]
			time, fl, fl_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
			ofactor = data['OF LC_{}'.format(nn)]
			exp = data['Exp. LC_{}'.format(nn)]
			
			log_jitter = parameters['LCsigma_{}'.format(nn)]['Value']
			jitter_err = np.sqrt(fl_err**2 + np.exp(log_jitter)**2)

			deltamag = parameters['LCblend_{}'.format(nn)]['Value']
			dilution = 10**(-deltamag/2.5)	

			flux_m = np.ones(len(times))
			flux_m_pls = {}
			flux_oc = np.ones(len(time))

			in_transit = np.array([],dtype=int)
			#in_transit_model = np.array([],dtype=int)

			lc_TTV = data['LC_{} TTVs'.format(nn)]
			fl_TTVmodel = {}
			fl_TTVoc = {}
			#print(pls)
			#print(parameters['TTVs'])
			for pl in pls:
				per = parameters['P_{}'.format(pl)]['Value']
				aR = parameters['a_Rs_{}'.format(pl)]['Value']
				rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
				inc = parameters['inc_{}'.format(pl)]['Value']
				ecc = parameters['e_{}'.format(pl)]['Value']
				ww = parameters['w_{}'.format(pl)]['Value']
				dur = total_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)*24
				if not np.isfinite(dur): continue
				#print(dur,per,rp,aR,inc,ecc,ww)
				try:
					t0n = parameters['Phot_{}:T0_{}'.format(nn,pl)]['Value']
				except KeyError:
					pass
				
				pl_TTV = 0
				if pl in parameters['TTVs']:
					pl_TTV = 1

				if pl_TTV & lc_TTV:
					
					fl_TTVmodel['LC_{} pl_{}'.format(nn,pl)] = {}#np.ones(len(time))
					fl_TTVoc['LC_{} pl_{}'.format(nn,pl)] = {}#np.ones(len(time))

					t0_storage = parameters['T0_{}'.format(pl)]['Value']
					flux_oc_pl = np.ones(len(time))

					flux_model = np.array([])#np.ones(len(times))

					times = np.array([])#np.ones(len(times))

					#ns, nus = data['LC_{}_n'.format(nn)] ## all ns and unique ns
					ns, nus = data['LC_{}_{}_n'.format(pl,nn)]
					for nu in nus:
						ind = np.where(ns == nu)[0]
						#times = time[ind]

						t0n = parameters['T0_{}_{}'.format(pl,nu)]['Value']# + parameters['TTV_{}:T0_{}'.format(pl,nu)]['Value']
						parameters['T0_{}'.format(pl)]['Value'] = t0n

						#ph = time2phase(time[ind],per,t0n)*per*24						
						ph = time2phase(time,per,t0n)*per*24						
						#intransit = np.where((ph < dur + 3) & (ph > -dur - 3))[0]
						indxs = np.where((ph < (dur/2 + 6)) & (ph > (-dur/2 - 6)))[0]
						
						#print(ns,nu)
						#print(time[ind])
						#print(ind,indxs)
						idx = np.intersect1d(ind,indxs)
						if not len(idx): continue
						in_transit = np.append(in_transit,indxs)
						#print(idx)

						#t0_storage = parameters['T0_b_{}'.format(pl)]['Value']

						flux_oc_pl[idx] = lc_model(time[idx],n_planet=pl,n_phot=nn,
												supersample_factor=ofactor,exp_time=exp)
						# if deltamag > 0.0:
						# 	flux_oc_pl[idx] = flux_oc_pl[idx]/(1 + dilution) + dilution/(1+dilution)



						n_times = np.linspace(min(time[idx])-3./24.,max(time[idx])+3./24.,1000)
						#n_times = np.linspace(min(time[idx])+3/24.,max(time[idx])-3./24.,1000)
						times = np.append(times,n_times)
						#flux_model = np.append(flux_model,lc_model(n_times,n_planet=pl,n_phot=nn))
						fl_model = lc_model(n_times,n_planet=pl,n_phot=nn,
												supersample_factor=ofactor,exp_time=exp)

						if deltamag > 0.0:
							flux_oc_pl[idx] = flux_oc_pl[idx]/(1 + dilution) + dilution/(1+dilution)
							fl_model = fl_model/(1 + dilution) + dilution/(1+dilution)						
						
						fl_TTVoc['LC_{} pl_{}'.format(nn,pl)][nu] = flux_oc_pl[idx]
						n_ph = time2phase(n_times,per,t0n)*per*24
						ss = np.argsort(n_ph)

						fl_TTVmodel['LC_{} pl_{}'.format(nn,pl)][nu] = (n_ph[ss],fl_model[ss])

						flux_model = np.append(flux_model,fl_model)



					# if deltamag > 0.0:
					# 	flux_oc_pl = flux_oc_pl/(1 + dilution) + dilution/(1+dilution)
					# 	flux_model = flux_model/(1 + dilution) + dilution/(1+dilution)
					
					flux_oc -= (1 - flux_oc_pl)
					#print(pl)
					#figd = plt.figure()
					#axd = figd.add_subplot(111)
					#axd.plot(time,flux_oc_pl,'.')
					#plt.savefig('flux_oc_pl_{}_{}.png'.format(nn,pl))
					## dubious
					flux_m = flux_model
					flux_m_pls[pl] = flux_model
					
					flux_m_trend = flux_m.copy()

					parameters['T0_{}'.format(pl)]['Value'] = t0_storage

					#ph = time2phase(time,per,t0)*per*24
					#ph_model = time2phase(times,per,t0)*per*24

					#pass


				else:
					# aR = parameters['a_Rs_{}'.format(pl)]['Value']
					# rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
					# inc = parameters['inc_{}'.format(pl)]['Value']
					# ecc = parameters['e_{}'.format(pl)]['Value']
					# ww = parameters['w_{}'.format(pl)]['Value']
					# print(per,rp,aR,inc,ecc,ww)
					#q1, q2 = parameters['LC1_q1']['Value'], parameters['LC1_q2']['Value']
					#print(q1,q2)
					flux_oc_pl = lc_model(time,n_planet=pl,n_phot=nn,
												supersample_factor=ofactor,exp_time=exp)

					if deltamag > 0.0:
						flux_oc_pl = flux_oc_pl/(1 + dilution) + dilution/(1+dilution)


					flux_oc -= (1 - flux_oc_pl)
					#return flux_oc
					flux_model = lc_model(times,n_planet=pl,n_phot=nn,
												supersample_factor=ofactor,exp_time=exp)
					if deltamag > 0.0:
						flux_model = flux_model/(1 + dilution) + dilution/(1+dilution)
					

					flux_m -= 1 - flux_model  
					flux_m_pls[pl] = np.ones(len(flux_m))
					flux_m_pls[pl] -= 1 - flux_model  

					#per, t0 = parameters['P_{}'.format(pl)]['Value'],parameters['T0_{}'.format(pl)]['Value']
					t0 = parameters['T0_{}'.format(pl)]['Value']#,parameters['T0_{}'.format(pl)]['Value']
					ph = time2phase(time,per,t0)*per*24
					#ph_model = time2phase(times,per,t0)*per*24

					# aR = parameters['a_Rs_{}'.format(pl)]['Value']
					# rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
					# inc = parameters['inc_{}'.format(pl)]['Value']
					# ecc = parameters['e_{}'.format(pl)]['Value']
					# ww = parameters['w_{}'.format(pl)]['Value']
					# dur = total_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)*24
					#print(pl,t0,per)
					#print(dur)
					indxs = np.where((ph < (dur/2 + 6)) & (ph > (-dur/2 - 6)))[0]
					in_transit = np.append(in_transit,indxs)


					#indxs_model = np.where((ph_model < (dur/2 + 6)) & (ph_model > (-dur/2 - 6)))[0]
					#in_transit_model = np.append(in_transit_model,indxs_model)
					flux_m_trend = flux_m.copy()





			trend = data['Detrend LC_{}'.format(nn)]
			plot_gp = data['GP LC_{}'.format(nn)]
			if (trend == 'poly') or (trend == True) or (trend == 'savitzky') or plot_gp:
				ax.plot(time,fl+off,marker='.',markersize=6.0,color='C7',linestyle='none',alpha=0.5,label=r'$\rm {} \ w/o \ detrending$'.format(label))
			if (trend == 'poly') or (trend == True):
				tr_fig = plt.figure(figsize=(12,6))
				ax_tr = tr_fig.add_subplot(111)

				deg_w = data['Poly LC_{}'.format(nn)]

				ns = data['LC_{}_n'.format(nn)]
				gaps = data['LC_{}_gaps'.format(nn)]
				temp_fl = fl - flux_oc + 1
				start = 0
				for gap in gaps:
					idxs = ns[start:int(gap+1)]
					t = time[idxs]
					tfl = temp_fl[idxs]

					ax_tr.plot(time[start:int(gap+1)],fl[start:int(gap+1)],marker='.',markersize=6.0,color='k',linestyle='none')
					ax_tr.plot(time[start:int(gap+1)],fl[start:int(gap+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')

					poly_pars = np.polyfit(t,tfl,deg_w)
					slope = np.zeros(len(t))
					for dd, pp in enumerate(poly_pars):
						slope += pp*t**(deg_w-dd)
					ax_tr.plot(t,slope,'-',color='k',lw=2.0,zorder=7)
					ax_tr.plot(t,slope,'-',color='w',lw=1.0,zorder=7)
					fl[idxs] /= slope
					

					start = int(gap + 1)

				idxs = ns[start:]
				ax_tr.plot(time[start:],fl[start:],marker='.',markersize=6.0,color='k',linestyle='none')
				ax_tr.plot(time[start:],fl[start:],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')

				t = time[idxs]
				tfl = temp_fl[idxs]
				poly_pars = np.polyfit(t,tfl,deg_w)
				slope = np.zeros(len(t))
				for dd, pp in enumerate(poly_pars):
					slope += pp*t**(deg_w-dd)
				fl[idxs] /= slope
				ax_tr.plot(t,slope,'-',color='k',lw=2.0,zorder=7)
				ax_tr.plot(t,slope,'-',color='w',lw=1.0,zorder=7)
				ax_tr.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)
				ax_tr.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)
				if savefig: tr_fig.savefig(path+'lc_{}_Polynomial-deg{}.pdf'.format(nn,deg_w))

				# tr_fig = plt.figure(figsize=(12,6))
				# ax_tr = tr_fig.add_subplot(111)

				# deg_w = data['Poly LC_{}'.format(nn)]
				# in_transit.sort()
				# in_transit = np.unique(in_transit)
				
				# dgaps = np.where(np.diff(time[in_transit]) > 1)[0]
				# start = 0
				# temp_fl = fl - flux_oc + 1
				# for dgap in dgaps:
						
				# 	idxs = in_transit[start:int(dgap+1)]
				# 	t = time[idxs]
				# 	tfl = temp_fl[idxs]

				# 	ax_tr.plot(time[start:int(dgap+1)],fl[start:int(dgap+1)],marker='.',markersize=6.0,color='k',linestyle='none')
				# 	ax_tr.plot(time[start:int(dgap+1)],fl[start:int(dgap+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')

				# 	poly_pars = np.polyfit(t,tfl,deg_w)
				# 	slope = np.zeros(len(t))
				# 	for dd, pp in enumerate(poly_pars):
				# 		slope += pp*t**(deg_w-dd)
				# 	ax_tr.plot(t,slope,'-',color='k',lw=2.0,zorder=7)
				# 	ax_tr.plot(t,slope,'-',color='w',lw=1.0,zorder=7)
				# 	fl[idxs] /= slope
					

				# 	start = int(dgap + 1)

				# idxs = in_transit[start:]
				# ax_tr.plot(time[start:],fl[start:],marker='.',markersize=6.0,color='k',linestyle='none')
				# ax_tr.plot(time[start:],fl[start:],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')

				# t = time[idxs]
				# tfl = temp_fl[idxs]
				# poly_pars = np.polyfit(t,tfl,deg_w)
				# slope = np.zeros(len(t))
				# for dd, pp in enumerate(poly_pars):
				# 	slope += pp*t**(deg_w-dd)
				# fl[idxs] /= slope
				# ax_tr.plot(t,slope,'-',color='k',lw=2.0,zorder=7)
				# ax_tr.plot(t,slope,'-',color='w',lw=1.0,zorder=7)
				# ax_tr.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)
				# ax_tr.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)
				# if savefig: tr_fig.savefig(path+'lc_{}_Polynomial-deg{}.pdf'.format(nn,deg_w))

			elif (trend == 'savitzky'):
				sg_fig = plt.figure(figsize=(12,6))
				ax_sg = sg_fig.add_subplot(111)

				temp_fl = fl - flux_oc + 1
				window = data['FW LC_{}'.format(nn)]

				gap = 0.5

				dls = np.where(np.diff(time) > gap)[0]
				sav_arr = np.array([])
				start = 0
				for dl in dls:						
					sav_fil = savgol_filter(temp_fl[start:int(dl+1)],window,2)
		
					ax_sg.plot(time[start:int(dl+1)],temp_fl[start:int(dl+1)],'.',markersize=6.0,color='k')
					ax_sg.plot(time[start:int(dl+1)],temp_fl[start:int(dl+1)],'.',markersize=4.0,color='C{}'.format(nn-1))
					
					ax_sg.plot(time[start:int(dl+1)],sav_fil,color='k',lw=2.0,zorder=7)
					ax_sg.plot(time[start:int(dl+1)],sav_fil,color='w',lw=1.0,zorder=7)
					sav_arr = np.append(sav_arr,sav_fil)
					start = int(dl + 1)

				sav_fil = savgol_filter(temp_fl[start:],window,2)
				sav_arr = np.append(sav_arr,sav_fil)
				
				ax_sg.plot(time[start:],temp_fl[start:],'.',markersize=6.0,color='k')
				ax_sg.plot(time[start:],temp_fl[start:],'.',markersize=4.0,color='C{}'.format(nn-1))
				ax_sg.plot(time[start:],sav_fil,color='k',lw=2.0,zorder=7)
				ax_sg.plot(time[start:],sav_fil,color='w',lw=1.0,zorder=7)

				ax_sg.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)
				ax_sg.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)

				if savefig: sg_fig.savefig(path+'lc_{}_Savitzky-Golay.pdf'.format(nn))

				fl /= sav_arr

			elif plot_gp:
				gp_fig = plt.figure(figsize=(12,6))
				ax_gp = gp_fig.add_subplot(111)
				gp = data['LC_{} GP'.format(nn)]
				gp_type = data['GP type LC_{}'.format(nn)]
				if gp_type == 'SHO':
					log_S0 = parameters['LC_{}_log_S0'.format(nn)]['Value']
					log_Q = parameters['LC_{}_log_Q'.format(nn)]['Value']
					log_w0 = parameters['LC_{}_log_w0'.format(nn)]['Value']
				
					gp_list = [log_S0,log_Q,log_w0]
				elif gp_type == 'mix':
					log_Q = parameters['LC_{}_GP_log_Q'.format(nn)]['Value']
					log_P = parameters['LC_{}_GP_log_P'.format(nn)]['Value']
					dQ = parameters['LC_{}_GP_log_dQ'.format(nn)]['Value']
					log_sig = parameters['LC_{}_GP_log_sig'.format(nn)]['Value']
					f = parameters['LC_{}_GP_f'.format(nn)]['Value']


					P = np.exp(log_P)
					Q0 = np.exp(log_Q)
					Q1 = 0.5 + Q0 + np.exp(dQ)
					w1 = 4*np.pi*Q1/(np.sqrt(4*Q1**2-1)*P)
					sig = np.exp(log_sig)
					S1 = sig**2/(w1*Q1*(1+f))

					Q2 = 0.5 + Q0
					w2 = 2*w1
					S2 = f*sig**2/(w2*Q2*(1+f)) 



					gp_list = [np.log(S1),np.log(Q1),np.log(w1),np.log(S2),np.log(Q2),np.log(w2)]


				else:
					loga = parameters['LC_{}_GP_log_a'.format(nn)]['Value']
					logc = parameters['LC_{}_GP_log_c'.format(nn)]['Value']
					gp_list = [loga,logc]
				
				jitter = 1
				if jitter:
					gp_list.append(parameters['LClogsigma_{}'.format(nn)]['Value'])	

				gp.set_parameter_vector(np.array(gp_list))
				gp.compute(time,jitter_err)

				ax_gp.plot(time,flux_oc,'k-',zorder=17)
				res_flux = fl - flux_oc


				gap = 0.5

				dls = np.where(np.diff(time) > gap)[0]
				start = 0
				for dl in dls:
					t_lin = np.linspace(min(time[start:int(dl+1)]),max(time[start:int(dl+1)]),500)
					mu, var = gp.predict(res_flux, t_lin, return_var=True)
					std = np.sqrt(var)
					ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=6.0,color='k',linestyle='none')
					ax_gp.plot(time[start:int(dl+1)],fl[start:int(dl+1)],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')

					ax_gp.fill_between(t_lin, mu+std+1, mu-std+1, color='C7', alpha=0.9, edgecolor="none",zorder=6)
					ax_gp.plot(t_lin,mu+1,color='k',lw=2.0,zorder=7)
					ax_gp.plot(t_lin,mu+1,color='w',lw=1.0,zorder=7)
					
					start = int(dl + 1)
				
				t_lin = np.linspace(min(time[start:]),max(time[start:]),500)
				mu, var = gp.predict(res_flux, t_lin, return_var=True)
				std = np.sqrt(var)
				ax_gp.plot(time[start:],fl[start:],marker='.',markersize=6.0,color='k',linestyle='none')
				ax_gp.plot(time[start:],fl[start:],marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none')
				ax_gp.fill_between(t_lin, mu+std+1, mu-std+1, color='C7', alpha=0.9, edgecolor="none",zorder=6)
				ax_gp.plot(t_lin,mu+1,color='k',lw=2.0,zorder=7)
				ax_gp.plot(t_lin,mu+1,color='w',lw=1.0,zorder=7)
				ax_gp.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)
				ax_gp.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)

				if savefig: gp_fig.savefig(path+'lc_{}_GP.pdf'.format(nn))


				in_transit.sort()
				in_transit = np.unique(in_transit)
				#print(in_transit)
				
				#in_transit_model.sort()
				#in_transit_model = np.unique(in_transit_model)

				dgaps = np.where(np.diff(in_transit) > 1)[0]
				start = 0
				for dgap in dgaps:						
					idxs = in_transit[start:int(dgap+1)]
					t = time[idxs]
					mu, var = gp.predict(res_flux, t, return_var=True)
					std = np.sqrt(var)
					fl[idxs] -= mu
					ax_gp.plot(t,fl[idxs],marker='.',markersize=6.0,color='C7',linestyle='none')

					start = int(dgap + 1)

				idxs = in_transit[start:]
				t = time[idxs]
				mu, var = gp.predict(res_flux, t, return_var=True)
				std = np.sqrt(var)
				fl[idxs] -= mu
				ax_gp.plot(t,fl[idxs],marker='.',markersize=6.0,color='k',linestyle='none')


			ax.plot(time,fl+off,marker='.',markersize=6.0,color='k',linestyle='none')
			ax.plot(time,fl+off,marker='.',markersize=4.0,color='C{}'.format(nn-1),linestyle='none',label=r'$\rm {}$'.format(label))




			for ii, pl in enumerate(pls):
				per, t0 = parameters['P_{}'.format(pl)]['Value'],parameters['T0_{}'.format(pl)]['Value']
				try:
					t0n = parameters['Phot_{}:T0_{}'.format(nn,pl)]['Value']
					parameters['T0_{}'.format(pl)]['Value'] = t0n				
				except KeyError:
					pass				
				aR = parameters['a_Rs_{}'.format(pl)]['Value']
				rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
				inc = parameters['inc_{}'.format(pl)]['Value']
				ecc = parameters['e_{}'.format(pl)]['Value']
				ww = parameters['w_{}'.format(pl)]['Value']
				#dur = duration(per,rp,aR,inc)
				#print(per,rp,aR,inc)
				dur = total_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)
				#full = dynamics.full_duration(per,rp,aR,inc*np.pi/180.,ecc,ww*np.pi/180.)
				if np.isfinite(dur):
					dur *= 24
					pl_TTV = 0
					if pl in parameters['TTVs']:
						pl_TTV = 1


					if pl_TTV & lc_TTV:
						#ns, nus = data['LC_{}_n'.format(nn)] ## all ns and unique ns
						ns, nus = data['LC_{}_{}_n'.format(pl,nn)]
						for nu in nus:
							ind = np.where(ns == nu)[0]
							#times = time[ind]

							t0n = parameters['T0_{}_{}'.format(pl,nu)]['Value']# + parameters['TTV_{}:T0_{}'.format(pl,nu)]['Value']
							#parameters['T0_{}'.format(pl)]['Value'] = t0n
							
							ph = time2phase(time,per,t0n)*per*24						
							#intransit = np.where((ph < dur + 3) & (ph > -dur - 3))[0]
							indxs = np.where((ph < (dur/2 + 6)) & (ph > (-dur/2 - 6)))[0]

							idx = np.intersect1d(ind,indxs)
							if not len(idx): continue
							in_transit = np.append(in_transit,indxs)

							flo = fl_TTVoc['LC_{} pl_{}'.format(nn,pl)][nu]	

							nt, nf = fl_TTVmodel['LC_{} pl_{}'.format(nn,pl)][nu]	

							phn = time2phase(time[idx],per,t0n)*per*24

							figttv = plt.figure()
							axttv = figttv.add_subplot(211)
							axttv_oc = figttv.add_subplot(212,sharex=axttv)
							axttv.plot(nt,nf,color='k',lw=2.0,zorder=7)#,markersize=0.1,color='k') 
							axttv.plot(nt,nf,color='C7',lw=1.0,zorder=8)#,markersize=0.1,color='k') 
							


							if errorbar:
								axttv.errorbar(phn,fl[idx],yerr=jitter_err[idx],linestyle='none',marker='.',markersize=0.1,color='k')
								axttv.errorbar(phn,fl[idx],yerr=fl_err[idx],linestyle='none',color='C{}'.format(nn-1))
								
								axttv_oc.errorbar(phn,fl[idx]-flo,yerr=jitter_err[idx],linestyle='none',marker='.',markersize=0.1,color='k')
								axttv_oc.errorbar(phn,fl[idx]-flo,yerr=fl_err[idx],linestyle='none',color='C{}'.format(nn-1))

							axttv.plot(phn,fl[idx],'.',markersize=6.0,color='k')
							axttv.plot(phn,fl[idx],'.',markersize=4.0,color='C{}'.format(nn-1))
							
							axttv_oc.plot(phn,fl[idx]-flo,'.',markersize=6.0,color='k')
							axttv_oc.plot(phn,fl[idx]-flo,'.',markersize=4.0,color='C{}'.format(nn-1))

							axttv.set_xlim(-1*dur/2-2.5,dur/2+2.5)
							axttv.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)

							axttv_oc.set_ylabel(r'$\rm Residuals$',fontsize=font)
							axttv_oc.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)

							axttv_oc.axhline(0.0,linestyle='--',color='C7',zorder=-10)

							figttv.subplots_adjust(hspace=0.0)
							if savefig: plt.savefig(path+'lc_{}_pl_{}_transit_{}.pdf'.format(nn,pl,nu))


						#pass
					else:
						figpl = plt.figure()
						#if OC_lc:
						#figpl.title(r'$\rm Planet \ {}$'.format(pl))
						axpl = figpl.add_subplot(211)
						axocpl = figpl.add_subplot(212,sharex=axpl)
						#axpl.title(r'$\rm Planet \ {}$'.format(pl))

						tt = time2phase(times,per,t0)*24*per#(time%per - t0%per)/per
						ss = np.argsort(tt)

						#print(flux_m_pls)
						axpl.plot(tt[ss],flux_m_pls[pl][ss],color='k',lw=2.0,zorder=7)
						axpl.plot(tt[ss],flux_m_pls[pl][ss],color='C7',lw=1.0,zorder=8)


						phase = time2phase(time,per,t0)*24*per


						if errorbar:
							axpl.errorbar(phase,fl,yerr=jitter_err,linestyle='none',marker='.',markersize=0.1,color='k')
							axpl.errorbar(phase,fl,yerr=fl_err,linestyle='none',color='C{}'.format(nn-1))

						axpl.plot(phase,fl,'.',markersize=6.0,color='k')
						axpl.plot(phase,fl,'.',markersize=4.0,color='C{}'.format(nn-1))
						
						xlim = dur/2+2.5
						within = (phase < xlim) & (phase > -xlim)
						ymax = np.max(fl[within]+np.median(fl_err[within]))
						ymin = np.min(fl[within]-np.median(fl_err[within]))

						axpl.set_xlim(-1*xlim,xlim)
						axpl.set_ylim(ymin,ymax)
						axpl.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)

						axocpl.axhline(0.0,linestyle='--',color='C7')
						if errorbar:
							axocpl.errorbar(phase,fl - flux_oc,yerr=jitter_err,linestyle='none',marker='.',markersize=0.1,color='k')
							axocpl.errorbar(phase,fl - flux_oc,yerr=fl_err,linestyle='none',marker='.',markersize=0.1,color='C{}'.format(nn-1))
						axocpl.plot(phase,fl - flux_oc,'.',markersize=6.0,color='k')
						axocpl.plot(phase,fl - flux_oc,'.',markersize=4.0,color='C{}'.format(nn-1))



						ymaxoc = np.max(fl[within] - flux_oc[within]+np.median(fl_err[within]))
						yminoc = np.min(fl[within] - flux_oc[within]-np.median(fl_err[within]))
						axocpl.set_ylim(yminoc,ymaxoc)
						axocpl.set_ylabel(r'$\rm Residuals$',fontsize=font)
						axocpl.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)

						figpl.subplots_adjust(hspace=0.0)
						if savefig: plt.savefig(path+'lc_{}_pl_{}.pdf'.format(nn,pl))



			print('## Photometric system {}/{} ##:'.format(nn,label))
			red_chi2 = np.sum((fl - flux_oc)**2/jitter_err**2)/(len(fl)-n_pars)
			print('\nReduced chi-squared for the light curve is:\n\t {:.03f}'.format(red_chi2))
			#print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
			print('Number of data points: {}'.format(len(fl)))
			print('Number of fitting parameters: {}'.format(n_pars))
			print('#########################'.format(nn))


			ax.plot(times,flux_m_trend+off,color='k',lw=2.0)
			ax.plot(times,flux_m_trend+off,color='C7',lw=1.0)	


			off += 1 - min_fl + 0.001
		
		ax.legend(bbox_to_anchor=(0, 1, 1, 0),ncol=int(n_phot))
		ax.set_xlim(min(time_range)-12./24.,max(time_range)+12./24.)
		ax.set_ylabel(r'$\rm Relative \ Brightness$',fontsize=font)
		ax.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)

		if savefig: fig.savefig(path+'lc_unphased.pdf',bbox_inches='tight')

# =============================================================================
# Shadow plot
# =============================================================================

def create_shadow(phase,vel,shadow,exp_phase,per,
	savefig=False,fname='shadow',zmin=None,zmax=None,
	xlims=[],contour=False,ncont=3,vsini=None,cmap='bone_r',
	ax=None,colorbar=True,cbar_pos='right',vsini_zero=True,
	font=12,tickfontsize=10,diff_cmap=None,its=[],usetex=False,**kwargs):
	'''Shadow plot.

	Creates the planetary shadow.
	
	:param vel: Velocity vector.
	:type vel: array 

	:param phase: Orbital phase.
	:type phase: array

	:param shadow: Shahow vector (out-of-transit absline minus in-transit absline).
	:type shadow: array
	
	:param exp_phase: Exposure time in phase units.
	:type exp_phase: array
	
	:param per: Orbital period (days).
	:type per: array 

	'''
	if not fname.lower().endswith(('.png','.pdf')): 
		ext = '.pdf'
		fname = fname.split('.')[0] + ext
	
	from matplotlib.colors import ListedColormap
	import matplotlib.colors as clr
	plt.rc('text',usetex=usetex)
	plt.rc('xtick',labelsize=3*font/4)
	plt.rc('ytick',labelsize=3*font/4)	
	## sort in phase
	sp = np.argsort(phase)
	shadow = shadow[sp]
	if zmin == None: zmin = np.min(shadow)
	if zmax == None: zmax = np.max(shadow)

	nn = len(phase)
	low_phase, high_phase = np.zeros(nn), np.zeros(nn)
	low_phase[:] = phase[sp] - exp_phase[sp]/2. - exp_phase[sp]/5.
	high_phase[:] = phase[sp] + exp_phase[sp]/2. + exp_phase[sp]/5.
	if not ax:
		fig = plt.figure()
		ax = fig.add_subplot(111)
	else:
		fig = ax.get_figure()
	mm = ax.pcolormesh(vel,phase*per*24,shadow,cmap=cmap,vmin=zmin,vmax=zmax)
	# for ii in range(nn):
	# 	xi = vel[ii] - np.append(np.diff(vel[ii])/2.,np.diff(vel[ii])[-1]/2.)
	# 	x_low, y_low = np.meshgrid(xi,low_phase)
	# 	x_high, y_high = np.meshgrid(xi,high_phase)
	# 	xx = np.array([x_low[ii],x_high[ii]])
	# 	yy = np.array([y_low[ii],y_high[ii]])
	# 	if diff_cmap and (ii in its):
	# 		ncmap = clr.LinearSegmentedColormap.from_list('custom blue', ['black',diff_cmap(ii),'white'], N=256)
	# 		mm = ax.pcolormesh(xx,yy*per*24,shadow[ii:ii+1],cmap=ncmap,vmin=zmin,vmax=zmax)
	# 	else:
	# 		mm = ax.pcolormesh(xx,yy*per*24,shadow[ii:ii+1],cmap=cmap,vmin=zmin,vmax=zmax)
	
	if contour:
		XX, YY = np.meshgrid(vel[0,:],phase*per*24)	
		ax.contour(XX,YY,shadow,ncont,colors='w')
	ax.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
	ax.set_ylabel(r'$\rm Hours \ from \ midtransit$',fontsize=font)
	if colorbar:
		if cbar_pos == 'right':
			cb = fig.colorbar(mm,ax=ax)
		else:
			## Now adding the colorbar
			cbaxes = fig.add_axes([0.128, 0.75, 0.43, 0.04]) 
			cb = fig.colorbar(mm,ax=ax, cax = cbaxes, orientation='horizontal') 
			cb.ax.xaxis.set_ticks_position('top')

		cb.ax.tick_params(labelsize=tickfontsize)

	if len(xlims) == 0:	
		xl, xh = ax.get_xlim()
		xlims = [xl,xh]
	ax.set_xlim(xlims[0],xlims[1])
	if vsini: 
		ax.axvline(vsini,linestyle='-',color='C3',**kwargs)
		ax.axvline(-vsini,linestyle='-',color='C3',**kwargs)
		if vsini_zero:
			ax.axvline(0.0,linestyle='--',color='C3',**kwargs)

	if savefig: plt.savefig(fname)


def plot_shadow(parameters,data,n_pars=0,#oots=None,
	cmap='gray',contact_color='C0',font = 12,savefig=True,path='',
	tickfontsize=10,scale2model=True,xlim=None,xticks=[],yticks=[],
	only_obs=False,diff_cmap=False,usetex=False,**kwargs):
	'''Shadow plot wrapper.


	Function which calls the "actual" shadow plot, i.e., from :py:func:`create_shadow`.
	Here the data is prepared and the model calculated.

	:param parameters: The parameters. See :py:class:`tracit.structure.par_struct`.
	:type parameters: dict

	:param data: The data. See :py:class:`tracit.structure.dat_struct`.
	:type data: dict


	'''
	

	plt.rc('text',usetex=usetex)

	#business.data_structure(data_fname)

	if n_pars == 0: n_pars = len(parameters['FPs'])
	
	pls = parameters['Planets']
	n_ls = data['LSs']
	# def time2phase(time,per,T0):
	# 	phase = ((time-T0)%per)/per
	# 	for ii in range(len(phase)):
	# 		if phase[ii] > 0.5: phase[ii] = phase[ii] - 1
	# 	return phase
	# if updated_pars is not None:

	# 	pars = parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	idx = 1
	# 	if (updated_pars.shape[0] > 3) & best_fit: idx = 4
	# 	for par in pars:
	# 		try:
	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass	

	vsini, zeta = parameters['vsini']['Value'], parameters['zeta']['Value'] 
	for pl in pls:
		P, T0 = parameters['P_{}'.format(pl)]['Value'], parameters['T0_{}'.format(pl)]['Value'] 


		ar, inc = parameters['a_Rs_{}'.format(pl)]['Value'], parameters['inc_{}'.format(pl)]['Value']*np.pi/180.
		rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
		ecc, ww = parameters['e_{}'.format(pl)]['Value'], parameters['w_{}'.format(pl)]['Value']*np.pi/180.
		b = ar*np.cos(inc)*(1 - ecc**2)/(1 + ecc*np.sin(ww))
		t14 = P/np.pi * np.arcsin( np.sqrt( ((1 + rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))
		t23 = P/np.pi * np.arcsin( np.sqrt( ((1 - rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))
		if np.isnan(t14): continue

		for nn in range(1,n_ls+1):
			shadow_data = data['LS_{}'.format(nn)]
			label = data['LS_label_{}'.format(nn)]
			jitter = 0.0
			chi2scale = data['Chi2 LS_{}'.format(nn)]
			times = []

			for key in shadow_data.keys():
				times.append(float(key))


			times = np.asarray(times)
			ss = np.argsort(times)
			times = times[ss]
			
			if any(np.array(abs(time2phase(times,P,T0)*P) < t14)):pass
			else:continue



			v0 = parameters['RVsys_{}'.format(nn)]['Value']
			rv_m = np.zeros(len(times))
			for pl in pls:
				p2, t02 = parameters['P_{}'.format(pl)]['Value'], parameters['T0_{}'.format(pl)]['Value'] 
				rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
				rv_m += rv_pl
			rv_m += v0


			#resol = data['Resolution_{}'.format(nn)]
			#thick = data['Thickness_{}'.format(nn)]
			#start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)
			
			resol = data['Resolution_{}'.format(nn)]
			thick = data['Thickness_{}'.format(nn)]
			#start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)

			start_grid = data['Start_grid_{}'.format(nn)]
			ring_grid = data['Ring_grid_{}'.format(nn)]
			vel_grid = data['Velocity_{}'.format(nn)]
			mu = data['mu_{}'.format(nn)]
			mu_grid = data['mu_grid_{}'.format(nn)]
			mu_mean	= data['mu_mean_{}'.format(nn)]

			no_bump = data['No_bump_{}'.format(nn)]
			span = data['Velocity_range_{}'.format(nn)]
			assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))

			vel_res = data['Velocity_resolution_{}'.format(nn)]
			vels = np.arange(-span,span,vel_res)
			avg_ccf = np.zeros(len(vels))

			use_gp = data['GP LS_{}'.format(nn)]
			if use_gp:
				vel_model, model_ccf_transit, model_ccf, darks, oot_lum, index_error = ls_model2(
					times,start_grid,ring_grid,
					vel_grid,mu,mu_grid,mu_mean,resol,vels,
					)
			else:
				#vel_model, shadow_model, model_ccf, darks, oot_lum, index_error = ls_model(
				vel_model, model_ccf_transit, model_ccf, darks, oot_lum, index_error = ls_model2(
					times,start_grid,ring_grid,
					vel_grid,mu,mu_grid,mu_mean,resol,vels
					)

			

			#keep = (vel_model > min(vels)) & (vel_model < max(vels))
			#vel_model = vel_model[keep]

			bright = np.sum(oot_lum)

			idxs = [ii for ii in range(len(times))]
			# if oots is None:
			# 	oots = data['idxs_{}'.format(nn)]
			oots = data['idxs_{}'.format(nn)]

			print('Number of spectra: {}'.format(len(idxs)))
			print('Using indices {} as out-of-transit spectra'.format(oots))
			its = [ii for ii in idxs if ii not in oots]



			obs_shadows = np.zeros(shape=(len(times),len(vels)))
			int_shadows = np.zeros(shape=(len(times),len(vel_model)))
			shadow_model = np.zeros(shape=(len(times),len(vel_model)))
			shadow2obs = np.zeros(shape=(len(times),len(vels)))


			if use_gp:

				sigma = parameters['LS_{}_GP_log_sigma'.format(nn)]['Value']
				rho = parameters['LS_{}_GP_log_rho'.format(nn)]['Value']
				diag = np.exp(parameters['LS_{}_GP_log_diag'.format(nn)]['Value'])
				gp = data['LS_{} GP'.format(nn)]
				gp.set_parameter_vector(np.array([sigma,rho]))
				
				# oot_sd = []
				# for ii, idx in enumerate(oots):
				# 	time = times[idx]
				# 	vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
				# 	# if not ii:
				# 	# 	## Interpolate to grid in stellar restframe
				# 	# 	# vel_min, vel_max = min(vel), max(vel)
				# 	# 	# span  = (vel_max - vel_min)
				# 	# 	# vels = np.arange(vel_min+span/10,vel_max-span/10,vel_res)
				# 	# 	vels = np.arange(-span,span,vel_res)
				# 	# 	avg_ccf = np.zeros(len(vels))
				# 	# 	oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

				# 	#vels[:,idx] = vel
				# 	no_peak = (vel > no_bump) | (vel < -no_bump)
					

				# 	ccf = shadow_data[time]['ccf'].copy()
				# 	poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				# 	ccf -= vel*poly_pars[0] + poly_pars[1]

				# 	area = np.trapz(ccf,vel)

				# 	ccf /= abs(area)

				# 	ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				# 	nccf = ccf_int(vels)

				# 	#oot_ccfs[:,ii] = nccf
				# 	avg_ccf += nccf
				
				oot_sd = []
				for ii, idx in enumerate(oots):
					time = times[idx]
					vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

					ccf = shadow_data[time]['ccf'].copy()

					no_peak = (vel > no_bump) | (vel < -no_bump)
					
					poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
					ccf -= (poly_pars[0]*vel + poly_pars[1])

					area = np.trapz(ccf,vel)
				
							
					ccf /= area	
					oot_sd.append(np.std(ccf[no_peak]))

					ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
					nccf = ccf_int(vels)
					avg_ccf += nccf

				avg_ccf /= len(oots)

				#avg_vel /= len(oots)

				model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
				newline = model_int(vels)
				sd = np.mean(oot_sd)
				unc = np.ones(len(vels))*sd
				
				# gp.compute(vels,unc)
				# gp_mean, var = gp.predict(avg_ccf - newline, vels, return_var=True)

				# figgp = plt.figure()
				# axgp = figgp.add_subplot(111)
				# axgp.plot(vels,gp_mean)
				# axgp.plot(vels,avg_ccf - newline)

				red_chi2_avg = []
				#oot_sd_b = []
				nps = []
				#jitter = 1e-2#0.
				for idx in range(len(times)):
					time = times[idx]
					vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

					ccf = shadow_data[time]['ccf'].copy()


					no_peak = (vel > no_bump) | (vel < -no_bump)

					poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
					ccf -= (poly_pars[0]*vel + poly_pars[1])

					area = np.trapz(ccf,vel)

					ccf /= area
					

					ccf *= darks[idx]/bright#blc[idx]		

					ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
					nccf = ccf_int(vels)
						
					shadow = avg_ccf - nccf
					obs_shadows[idx,:] = shadow# - (poly_pars[0]*vel + poly_pars[1])
									

					#int_to_model = interpolate.interp1d(vels,shadow,kind='cubic',fill_value='extrapolate')
					#ishadow = int_to_model(vel_model)
					
					#int_shadows[idx,:] = ishadow

					no_peak = (vels > no_bump) | (vels < -no_bump)
					sd = np.std(nccf[no_peak])
					unc = np.ones(len(vels))*np.sqrt(sd**2 + jitter**2)					

					shadow_model[idx,:] = model_ccf - model_ccf_transit[idx]

					int_to_obs = interpolate.interp1d(vel_model,shadow_model[idx],kind='cubic',fill_value='extrapolate')
					model_to_obs = int_to_obs(vels)

					mean = shadow - model_to_obs
					gp.compute(vels,diag)
					gp_mean, var = gp.predict(mean, vels, return_var=True)
					obs_shadows[idx,:] = shadow# - gp_mean
					shadow2obs[idx,:] = model_to_obs + gp_mean

					print(gp.log_likelihood(mean))

					#obs_shadows[idx,:] = shadow - gp_mean
				

				if 0:
					## Again shift CCFs to star rest frame
					## and detrend CCFs
					## Compare to shadow model
					jitter = 0
					for ii, idx in enumerate(its):
						#arr = data[time]
						time = times[idx]
						vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
						#vels[:,idx] = vel
						no_peak = (vel > no_bump) | (vel < -no_bump)
							
						ccf = shadow_data[time]['ccf'].copy()
						if False:#use_gp:
							ccf -= np.median(ccf[no_peak])
						else:
							poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
							ccf -= vel*poly_pars[0] + poly_pars[1]
						
						area = np.trapz(ccf,vel)
						ccf /= area
						
						

						ccf *= darks[idx]/bright#blc[ii]		

						ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
						nccf = ccf_int(vels)
						

						no_peak = (vels > no_bump) | (vels < -no_bump)
						sd = np.std(nccf[no_peak])
						unc = np.ones(len(vels))*np.sqrt(sd**2 + jitter**2)
						# if use_gp:			
						# 	unc = np.ones(len(vels))*np.sqrt(sd**2 + jitter**2)
						# 	nccf -= mean
						# else:
						# 	unc = np.ones(len(vels))*sd
						# 	unc *= chi2scale_shadow

						
						#shadow = nccf
						shadow = avg_ccf - nccf

						#ff = interpolate.interp1d(vel_model,shadow_model[idx],kind='cubic',fill_value='extrapolate')
						#ishadow = ff(vels)

						model_to_obs = interpolate.interp1d(vel_model,model_ccf_transit[idx],kind='cubic',fill_value='extrapolate')
						ishadow = newline - model_to_obs(vels)
						shadow2obs[idx,:] = ishadow


						#mean = shadow - ishadow
						#gp.compute(vels,unc)
						#gp_mean, var = gp.predict(mean, vels, return_var=True)
						obs_shadows[idx,:] = shadow #- gp_mean
						# vv,ss = get_binned(vel,shadow)

					# no_peak = (vv > 15) | (vv < -15)
					# sd = np.std(ss[no_peak])
					# poly_pars = np.polyfit(vv[no_peak],ss[no_peak],1)
					# nvv,nss = get_binned(vel,ishadow)

					# unc = np.ones(len(vv))*np.sqrt(sd**2 + jitter**2)

			# 		res_cff = avg_ccf - newline

			# 		lprob = gp.log_likelihood(res_cff)
			# 		log_prob += lprob#lnlike(flux_m,flux,sigma)
					#lprob = gp.log_likelihood(mean)




					#shadow = avg_ccf - nccf
					
					# shadow_model[idx,:] = model_ccf - model_ccf_transit[idx]

					# int_to_model = interpolate.interp1d(vels,shadow,kind='cubic',fill_value='extrapolate')
					# ishadow = int_to_model(vel_model)
					


					#chisq += chi2(shadow,ishadow,unc)
					#log_prob += lnlike(shadow,ishadow,unc)

					# log_prob += lprob#lnlike(flux_m,flux,sigma)

					# chisq += -2*lprob - np.sum(np.log(2*np.pi*unc**2))#chi2(flux_m,flux,sigma)
					
					# n_dps += len(shadow)

				# loga = parameters['LS_{}_GP_log_a'.format(nn)]['Value']
				# logc = parameters['LS_{}_GP_log_c'.format(nn)]['Value']
				# gp = data['LS_{} GP'.format(nn)]
				# gp.set_parameter_vector(np.array([loga,logc]))

				# jitter = parameters['LSsigma_{}'.format(nn)]['Value']
				# jitter = np.exp(jitter)

				# model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
				# newline = model_int(vels)
				
				# unc = np.zeros(len(vels))

				# oot_sd_b = []
				# for ii, idx in enumerate(oots):
				# 	time = times[idx]
				# 	vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
				# 	ccf = shadow_data[time]['ccf'].copy()
				# 	err = shadow_data[time]['err'].copy()


				# 	ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				# 	nccf = ccf_int(vels)
						

				# 	unc += np.sqrt(np.mean(err)**2 + jitter**2)
				# 	gp.compute(vels,unc)
				# 	unc -= np.sqrt(np.mean(err)**2 + jitter**2)

				# 	gp_mean, var = gp.predict(avg_ccf  - newline, vels, return_var=True)
		
				# 	area = np.trapz(nccf,vels)	
				# 	nccf /= area	

				# 	avg_ccf += nccf - gp_mean
				# avg_ccf /= len(oots)

				# red_chi2_avg = []
				# #oot_sd_b = []
				# nps = []

				# for idx in range(len(times)):
				# 	time = times[idx]
				# 	vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
				# 	ccf = shadow_data[time]['ccf'].copy()
				# 	err = shadow_data[time]['err'].copy()


				# 	ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				# 	nccf = ccf_int(vels)
						
				# 	unc += np.sqrt(np.mean(err)**2 + jitter**2)
				# 	gp.compute(vels,unc)
				# 	unc -= np.sqrt(np.mean(err)**2 + jitter**2)


				# 	model_to_obs = interpolate.interp1d(vel_model,model_ccf_transit[idx],kind='cubic',fill_value='extrapolate')
				# 	int_transit = model_to_obs(vels)

				# 	gp_mean, var = gp.predict(nccf  - int_transit, vels, return_var=True)
					
				# 	nccf -= gp_mean
				# 	area = np.trapz(nccf,vels)
				# 	nccf /= area
				# 	nccf *= darks[idx]/bright#blc[idx]		


				# 	shadow = avg_ccf - nccf
				# 	obs_shadows[idx,:] = shadow
					
				# 	shadow_model[idx,:] = model_ccf - model_ccf_transit[idx]

				# 	int_to_model = interpolate.interp1d(vels,shadow,kind='cubic',fill_value='extrapolate')
				# 	ishadow = int_to_model(vel_model)
					
				# 	int_shadows[idx,:] = ishadow



			else:
				oot_sd_b = []
				#cut = data['LS floor_{}'.format(nn)] 
				use_min = 0
				for ii, idx in enumerate(oots):
					time = times[idx]
					vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
					keep = (vel > -span) & (vel < span)
					vel = vel[keep]
					ccf = shadow_data[time]['ccf'].copy()
					ccf = ccf[keep]
					# if use_min:
					# 	ccf -= np.min(ccf)
					# elif cut:
					# 	right = np.argmin(vel-cut)
					# 	left = np.argmin(vel+cut)
					# 	off = np.mean([ccf[left],ccf[right]])
					# 	ccf -= off
					# else:
					no_peak = (vel > no_bump) | (vel < -no_bump)
				
					poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
					ccf -= (poly_pars[0]*vel + poly_pars[1])

					area = np.trapz(ccf,vel)
				
							
					ccf /= area	

					ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
					nccf = ccf_int(vels)
					avg_ccf += nccf
						
		

					#avg_ccf += ccf
				avg_ccf /= len(oots)

			
				red_chi2_avg = []
				#oot_sd_b = []
				nps = []

				for idx in range(len(times)):
					time = times[idx]
					vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
					keep = (vel > -span) & (vel < span)
					vel = vel[keep]

					ccf = shadow_data[time]['ccf'].copy()
					ccf = ccf[keep]
					# if use_min:
					# 	#print(np.min(ccf))
					# 	ccf -= np.min(ccf)
					# 	#print('Using min')
					# 	#print(np.min(ccf))
					# elif cut:
					# 	right = np.argmin(vel-cut)
					# 	left = np.argmin(vel+cut)
					# 	off = np.mean([ccf[left],ccf[right]])
					# 	ccf -= off
					# else:

					no_peak = (vel > no_bump) | (vel < -no_bump)

					poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
					ccf -= (poly_pars[0]*vel + poly_pars[1])

					area = np.trapz(ccf,vel)
					ccf /= area
					

					ccf *= darks[idx]/bright#blc[idx]		

					ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
					nccf = ccf_int(vels)
						
					shadow = avg_ccf - nccf
					obs_shadows[idx,:] = shadow# - (poly_pars[0]*vel + poly_pars[1])
									

					#int_to_model = interpolate.interp1d(vels,shadow,kind='cubic',fill_value='extrapolate')
					#ishadow = int_to_model(vel_model)
					
					#int_shadows[idx,:] = ishadow

					no_peak = (vels > no_bump) | (vels < -no_bump)
					

					shadow_model[idx,:] = model_ccf - model_ccf_transit[idx]

					int_to_obs = interpolate.interp1d(vel_model,shadow_model[idx],kind='cubic',fill_value='extrapolate')
					model_to_obs = int_to_obs(vels)
					shadow2obs[idx,:] = model_to_obs

					#vv,cc = get_binned(vels,shadow)
					#vn,ncc = get_binned(vels,model_to_obs)	
					#no_peak_b = (vv > no_bump) | (vv < -no_bump)
					#sd = np.std(cc[no_peak_b])
					#unc_b = np.ones(len(vv))*np.sqrt((sd**2 + jitter**2))*chi2scale
					#unc_b = np.ones(len(vv))*np.sqrt((sd**2 + jitter**2))
					#red_chi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-n_pars)
					
					#unc = np.ones(len(vel))*np.sqrt((np.std(shadow[no_peak])**2 + jitter**2))*chi2scale
					unc = np.ones(len(vels))*np.sqrt((np.std(shadow[no_peak])**2 + jitter**2))*chi2scale
					red_chi2 = np.sum((shadow-model_to_obs)**2/unc**2)/(len(shadow)/4 - n_pars)
					nps.append(len(shadow)/4)
					red_chi2_avg.append(red_chi2)
				n_points = np.mean(nps)



			print('## Spectroscopic system {}/{} ##:'.format(nn,label))
			print('\nReduced chi-squared for the shadow is:\n\t {:.03f}'.format(np.mean(red_chi2_avg)))
			#print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(np.mean(red_chi2_avg))))
			print('Number of data points: {}'.format(n_points))
			print('Number of fitting parameters: {}'.format(n_pars))
			print('#########################')

			phase = time2phase(times,P,T0) #phase of observing times
			exptime = np.mean(np.diff(times))*np.ones(len(times))*24.*3600.
			exptime_phase = exptime/(P*24.*3600.) #exptimes converted to phase-units for making shadow figure
			vel_m_arr = np.asarray([vels]*len(times))

			if not only_obs:
				if scale2model:
					#zmin = np.min(-1*shadow_model)
					zmin = np.min(-1*shadow2obs)
				else:
					#zmin = np.min(-1*int_shadows)
					zmin = np.min(-1*obs_shadows)

				zmax = abs(zmin)

				plt.rcParams['ytick.labelsize']	= tickfontsize
				plt.rcParams['xtick.labelsize']	= tickfontsize
				plt.figure(figsize=(16,6))
				gs = GridSpec(5, 7)
				ax1 = plt.subplot(gs[1:, 0:2])
				ax2 = plt.subplot(gs[1:, 2:4])
				ax3 = plt.subplot(gs[1:, 4:6])

				axes = [ax1,ax2,ax3]

				axres2 = plt.subplot(gs[1:, 6])
				axres1 = plt.subplot(gs[0, 4:6])




				#vel_m_arr = np.asarray([vel_model]*len(times))

				#create_shadow(phase, vel_m_arr, -1*int_shadows, exptime_phase,P,cmap=cmap,
				create_shadow(phase, vel_m_arr, -1*obs_shadows, exptime_phase,P,cmap=cmap,
										vsini=vsini,zmin=zmin,zmax=zmax,contour=False,ax=ax1,
										colorbar=False,font=font,usetex=usetex,**kwargs)

				#create_shadow(phase, vel_m_arr, -1*shadow_model, exptime_phase,P, vsini=vsini,cmap=cmap,font=font,
				create_shadow(phase, vel_m_arr, -1*shadow2obs, exptime_phase,P, vsini=vsini,cmap=cmap,font=font,
										zmin=zmin,zmax=zmax,contour=False,ax=ax2,cbar_pos='top',
										tickfontsize=tickfontsize,usetex=usetex,**kwargs)

				#diff = -1*(int_shadows - shadow_model)
				diff = -1*(obs_shadows - shadow2obs)
				create_shadow(phase, vel_m_arr, diff, exptime_phase,P, cmap=cmap,font=font,
										vsini=vsini,zmin=zmin,zmax=zmax,contour=False,ax=ax3,
										colorbar=False,usetex=usetex,**kwargs)

				
				if xlim:
					x1, x2 = -xlim, xlim
				else: 
					x1, x2 = min(vels), max(vels)


				for ax in axes:
					#x1, x2 = ax.get_xlim()
					y1, y2 = ax.get_ylim()
					ax.axhline(-1*t23*24/2,linestyle='--',color=contact_color,**kwargs)
					ax.axhline(1*t23*24/2,linestyle='--',color=contact_color,**kwargs)

					ax.axhline(1*t14*24/2,linestyle='-',color=contact_color,**kwargs)
					ax.axhline(-1*t14*24/2,linestyle='-',color=contact_color,**kwargs)
					#if xmax != None: x2 = xmax
					#if xmin != None: x1 = xmin
					ax.set_xlim(x1,x2)
					ax.set_ylim(y1,y2)

				ax1.tick_params(axis='both',labelsize=tickfontsize)
				ax2.tick_params(axis='both',labelsize=tickfontsize)
				ax3.tick_params(axis='both',labelsize=tickfontsize)
		
				ax2.set_ylabel('')
				ax3.set_ylabel('')
				plt.setp(ax2.get_yticklabels(),visible=False)
				plt.setp(ax3.get_yticklabels(),visible=False)


				low = np.min(diff)
				diff *= -1
				res2 = np.zeros(len(phase))
				for ii in range(len(phase)):
					res2[ii] = np.sum(abs(diff[ii,:]))
				res1 = np.zeros(diff.shape[1])
				for ii in range(len(res1)):
					res1[ii] = np.sum(abs(diff[:,ii]))
					
				axres2.plot(res2,phase,'k-')
				axres2.set_yticks([])
				axres2.set_xlabel(r'$\Sigma \rm |O-C|$',fontsize=font)# \abs{\delta}$')

				axres2.set_ylim(min(phase),max(phase))

				# if (xmin != None) & (xmax != None):
				# 	keep = (vel_m_arr[0,:] > xmin) & (vel_m_arr[0,:] < xmax)
				# 	vel_m = vel_m_arr[0,keep]
				# 	res1 = res1[keep]
				# elif xmax != None:
				# 	keep = vel_m_arr[0,:] < xmax
				# 	vel_m = vel_m_arr[0,keep]
				# 	res1 = res1[keep]
				# elif xmin != None:
				# 	keep = vel_m_arr[0,:] > xmin
				# 	vel_m = vel_m_arr[0,keep]
				# 	res1 = res1[keep]
				# else:
				# 	vel_m = vel_m_arr[0,:]

				keep = (vel_m_arr[0,:] > x1) & (vel_m_arr[0,:] < x2)
				vel_m = vel_m_arr[0,keep]
				res1 = res1[keep]

				axres1.plot(vel_m,res1,'k-')
				axres1.set_xticks([])
				axres1.set_ylabel(r'$\Sigma \rm |O-C|$',fontsize=font)# \abs{\delta}$')
				axres1.set_xlim(min(vel_m),max(vel_m))
				axres1.set_ylim(ymin=0.0)
				#axres1.set_xlim(x1,x2)
				axres2.set_xlim(xmin=0.0)
				axres1.yaxis.tick_right()
				axres1.yaxis.set_label_position("right")

				plt.subplots_adjust(wspace=0.0,hspace=0.0)
			else:
				fig = plt.figure()
				ax = fig.add_subplot(111)

				zmin = np.min(-1*obs_shadows)
				zmax = abs(zmin)
				if diff_cmap:
					ncmap = plt.get_cmap('Spectral',len(phase))
					create_shadow(phase, vel_m_arr, -1*obs_shadows, exptime_phase,P,cmap=cmap,
											vsini=vsini,zmin=zmin,zmax=zmax,contour=False,ax=ax,
											colorbar=False,font=font,usetex=usetex,
											diff_cmap=ncmap,its=its,**kwargs)
				else:
					create_shadow(phase, vel_m_arr, -1*obs_shadows, exptime_phase,P,cmap=cmap,
											vsini=False,zmin=zmin,zmax=zmax,contour=False,ax=ax,
											colorbar=True,font=font,usetex=usetex,**kwargs)
				ax.axhline(-1*t23*24/2,linestyle='--',color=contact_color,**kwargs)
				ax.axhline(1*t23*24/2,linestyle='--',color=contact_color,**kwargs)

				ax.axhline(1*t14*24/2,linestyle='-',color=contact_color,**kwargs)
				ax.axhline(-1*t14*24/2,linestyle='-',color=contact_color,**kwargs)


				if len(xticks) == 2:
					ax.xaxis.set_major_locator(MultipleLocator(xticks[0]))
					ax.xaxis.set_minor_locator(MultipleLocator(xticks[1]))
				if len(yticks) == 2:
					ax.yaxis.set_major_locator(MultipleLocator(yticks[0]))
					ax.yaxis.set_minor_locator(MultipleLocator(yticks[1]))
				if xlim:
					ax.set_xlim(-xlim,xlim)

			if savefig: plt.savefig(path+'shadow.png',dpi=500,bbox_inches='tight')
			#if savefig: plt.savefig(path+'shadow.pdf')

# =============================================================================
# Out-of-transit plot
# =============================================================================

def plot_oot_ccf_gp(parameters,data,updated_pars=None,n_pars=0,chi2_scale=1.0,#oots=None,
	font = 12,savefig=True,path='',best_fit=True,xmajor=None,xminor=None,
	ymajor1=None,yminor1=None,ymajor2=None,yminor2=None,plot_intransit=True,xmax=None,xmin=None,
	usetex=False,**kwargs):
	'''Plot out-of-transit CCFs.

	

	'''
	

	plt.rc('text',usetex=usetex)


	if n_pars == 0: n_pars = len(parameters['FPs'])

	n_ls = data['LSs']
	pls = parameters['Planets']
	# if updated_pars is not None:
	# 	pars = parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	for par in pars:
	# 		if best_fit: idx = 4
	# 		else: idx = 1
	# 		try:
	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass	
	
	for nn in range(1,n_ls+1):
		label = data['LS_label_{}'.format(nn)]

		shadow_data = data['LS_{}'.format(nn)]
		#chi2scale = data['Chi2 OOT_{}'.format(nn)]

		times = []
		for key in shadow_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]

		v0 = parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			#rv_pl = rv_model(parameters,time,n_planet=pl,n_rv=nn,RM=calc_RM)
			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
			rv_m += rv_pl
		rv_m += v0


		resol = data['Resolution_{}'.format(nn)]
		thick = data['Thickness_{}'.format(nn)]
		#start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)

		start_grid = data['Start_grid_{}'.format(nn)]
		ring_grid = data['Ring_grid_{}'.format(nn)]
		vel_grid = data['Velocity_{}'.format(nn)]
		mu = data['mu_{}'.format(nn)]
		mu_grid = data['mu_grid_{}'.format(nn)]
		mu_mean	= data['mu_mean_{}'.format(nn)]

		

	
		
		no_bump = data['No_bump_{}'.format(nn)]
		span = data['Velocity_range_{}'.format(nn)]
		assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))
		
		idxs = [ii for ii in range(len(times))]
		# if oots is None:
		# 	oots = data['idxs_{}'.format(nn)]
		oots = data['idxs_{}'.format(nn)]
		#nvel = len(shadow_data[times[0]]['vel'])
		vel_res = data['Velocity_resolution_{}'.format(nn)]
		vels = np.arange(-span,span,vel_res)
		avg_ccf = np.zeros(len(vels))
		oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

		vel_model, model_ccf, oot_lum = ls_model(
			times,start_grid,ring_grid,
			vel_grid,mu,mu_grid,mu_mean,resol,vels,
			n_planet='b',n_rv=nn,oot=True
			)

		bright = np.sum(oot_lum)



		print('Using indices {} as out-of-transit spectra'.format(oots))

		its = [ii for ii in idxs if ii not in oots]	
		## Create average out-of-transit CCF
		## Used to create shadow for in-transit CCFs
		## Shift CCFs to star rest frame
		## and detrend CCFs
		use_gp = data['GP LS_{}'.format(nn)]
		if use_gp:
			# loga = parameters['LS_{}_GP_log_a'.format(nn)]['Value']
			# logc = parameters['LS_{}_GP_log_c'.format(nn)]['Value']
			# gp = data['LS_{} GP'.format(nn)]#celerite.GP(kernel)
			# gp.set_parameter_vector(np.array([loga,logc]))

			# vels = np.arange(-span,span,vel_res)
			# avg_ccf = np.zeros(len(vels))
			# oot_ccfs = np.zeros(shape=(len(vels),len(oots)))
			# oot_sd = []
			# for ii, idx in enumerate(oots):
			# 	time = times[idx]
			# 	vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

			# 	no_peak = (vel > no_bump) | (vel < -no_bump)

			# 	ccf = shadow_data[time]['ccf'].copy()
				
			# 	ccf -= np.median(ccf[no_peak])


			# 	area = np.trapz(ccf,vel)
			# 	ccf /= abs(area)

			# 	ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
			# 	nccf = ccf_int(vels)
				
			# 	no_peak = (vels > no_bump) | (vels < -no_bump)
			# 	oot_sd.append(np.std(nccf[no_peak]))
					

			# 	oot_ccfs[:,ii] = nccf
			# 	avg_ccf += nccf


			# avg_ccf /= len(oots)
			# jitter = parameters['LSsigma_{}'.format(nn)]['Value']
			# jitter = np.exp(jitter)
			# unc = np.ones(len(vels))*np.sqrt((np.mean(oot_sd)**2 + jitter**2))
			# gp.compute(vels,unc)
			# model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
			# newline = model_int(vels)		
			# gp_mean, var = gp.predict(avg_ccf  - newline, vels, return_var=True)
			#avg_ccf -= gp_mean
			# std = np.sqrt(var)
			# fig = plt.figure()
			# ax = fig.add_subplot(211)
			# ax2 = fig.add_subplot(212)
			# #ax.errorbar(avg_vel,oot_ccfs[:,ii]-newline,yerr=unc)
			# #ax.plot(vels,oot_ccfs[:,ii])
			# ax.plot(vels,avg_ccf)		
			# ax.plot(vels,avg_ccf-mu)		
			# ax.plot(vels,newline)		
			# ax.fill_between(vels, newline+mu+std, newline+mu-std, color='C1', alpha=0.3, edgecolor="none")
			
			# #ax2.plot(vels,avg_ccf-newline)		
			# #ax2.errorbar(vels,avg_ccf-newline,yerr=unc,linestyle='none')
			# #ax2.errorbar(vels,avg_ccf-newline,yerr=np.mean(oot_sd),linestyle='none',color='k')
			# #ax2.fill_between(vels, mu+std, mu-std, color='C1', alpha=0.3, edgecolor="none")
			# ax2.errorbar(vels,avg_ccf-newline-mu,yerr=unc,linestyle='none')
			# ax2.errorbar(vels,avg_ccf-newline-mu,yerr=np.mean(oot_sd),linestyle='none',color='k')
			# #ax2.plot(vels,avg_ccf-newline-mu,color='k')

			gp_pars = []
			gp_type = data['GP type LS_{}'.format(nn)]
			if gp_type == 'Matern32':
				loga = parameters['LS_{}_GP_log_sigma'.format(nn)]['Value']
				logc = parameters['LS_{}_GP_log_rho'.format(nn)]['Value']
			elif gp_type == 'Real':
				loga = parameters['LS_{}_GP_log_a'.format(nn)]['Value']
				logc = parameters['LS_{}_GP_log_c'.format(nn)]['Value']
			
			gp_pars = [loga,logc]

			jitt = 1
			if jitt:
				jitter = parameters['LSsigma_{}'.format(nn)]['Value']
				jitter = np.exp(jitter)
				gp_pars.append(jitter)

			gp = data['LS_{} GP'.format(nn)]
			#print(gp_pars)
			gp.set_parameter_vector(np.array(gp_pars))


			# model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
			# newline = model_int(vels)
			
			# unc = np.zeros(len(vels))

			# oot_sd = []
			# for ii, idx in enumerate(oots):
			# 	time = times[idx]
			# 	vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
			# 	ccf = shadow_data[time]['ccf'].copy()
			# 	err = shadow_data[time]['err'].copy()


			# 	ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
			# 	nccf = ccf_int(vels)
					

			# 	unc += np.sqrt(np.mean(err)**2 + jitter**2)
			# 	gp.compute(vels,unc)
			# 	unc -= np.sqrt(np.mean(err)**2 + jitter**2)

			# 	oot_sd.append(err)
			# 	gp_mean, var = gp.predict(avg_ccf  - newline, vels, return_var=True)
	
			# 	area = np.trapz(nccf,vels)	
			# 	nccf /= area	

			# 	oot_ccfs[:,ii] = nccf - gp_mean
			# 	avg_ccf += nccf - gp_mean

			# avg_ccf /= len(oots)


			oot_sd = []
			for ii, idx in enumerate(oots):
				time = times[idx]
				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
				# if not ii:
				# 	## Interpolate to grid in stellar restframe
				# 	# vel_min, vel_max = min(vel), max(vel)
				# 	# span  = (vel_max - vel_min)
				# 	# vels = np.arange(vel_min+span/10,vel_max-span/10,vel_res)
				# 	vels = np.arange(-span,span,vel_res)
				# 	avg_ccf = np.zeros(len(vels))
				# 	oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

				#vels[:,idx] = vel
				no_peak = (vel > no_bump) | (vel < -no_bump)
				

				ccf = shadow_data[time]['ccf'].copy()
				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				# ccf -= vel*poly_pars[0] + poly_pars[1]

				# area = np.trapz(ccf,vel)

				# ccf /= abs(area)
				oot_sd.append(np.std(ccf[no_peak]))



				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)


				oot_ccfs[:,ii] = nccf
				avg_ccf += nccf

			avg_ccf /= len(oots)
			
			#avg_vel /= len(oots)

			model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
			newline = model_int(vels)
			sd = np.mean(oot_sd)
			unc = np.ones(len(vels))*sd
			gp.compute(vels)
			gp_mean, var = gp.predict(avg_ccf  - newline, vels, return_var=True)
			
			
			area = np.trapz(avg_ccf-gp_mean,vels)
			avg_ccf /= area


			lab = r'$\rm Obs.\ avg. \ CCF \ w/ \ GP$'

		else:
			oot_sd = []
			from scipy.special import voigt_profile
			from scipy.stats import cauchy
			from scipy.signal import convolve
			for ii, idx in enumerate(oots):
				time = times[idx]
				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

				#vels[:,idx] = vel
				no_peak = (vel > no_bump) | (vel < -no_bump)

				ccf = shadow_data[time]['ccf'].copy()

				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				ccf -= vel*poly_pars[0] + poly_pars[1]

				area = np.trapz(ccf,vel)
				ccf /= abs(area)

				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)
				
				no_peak = (vels > no_bump) | (vels < -no_bump)
				oot_sd.append(np.std(nccf[no_peak]))
					

				oot_ccfs[:,ii] = nccf
				avg_ccf += nccf

			avg_ccf /= len(oots)


			jitter = parameters['LSsigma_{}'.format(nn)]['Value']
			jitter = np.exp(jitter)

			model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
			newline = model_int(vels)

			unc = np.ones(len(vels))*np.sqrt((np.mean(oot_sd)**2 + jitter**2))
			chi2scale_oot = data['Chi2 OOT_{}'.format(nn)]
			unc *= chi2scale_oot
			gp_mean = np.zeros(len(vels))
			sigma, gamma = 1.5, 6.0
			#sigma, gamma = 0.0, 6.0
			def cauchy(x, gamma):
				return gamma/(np.pi * (np.square(x)+gamma**2))
			#gp_mean = voigt_profile(vels, sigma, gamma)
			#gp_mean = cauchy.pdf(vels, loc=0.0, scale=0.1)
			gp_mean = cauchy(vels,4.9)
			convolved = vel_res * convolve(newline, gp_mean, mode="same")
			convolved = np.append(convolved,convolved[0])
			convolved = convolved[1:]
			#convolved = convolve(gp_mean, newline, mode="same")

			lab = r'$\rm Obs.\ avg. \ CCF$'
			jitt = 0



		red_chi2 = np.sum((avg_ccf-newline)**2/unc**2)/(len(avg_ccf)-n_pars)
		print('## Spectroscopic system {}/{} ##:'.format(nn,label))
		print('\nReduced chi-squared for the oot CCF is:\n\t {:.03f}'.format(red_chi2))
		#print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
		print('Number of data points: {}'.format(len(avg_ccf)))
		print('Number of fitting parameters: {}'.format(n_pars))
		print('#########################')

		figccf = plt.figure()
		ax1_ccf = figccf.add_subplot(211)
		ax2_ccf = figccf.add_subplot(212)

		ax1_ccf.plot(vels,avg_ccf,'-',color='k',label=lab,lw=5.0,zorder=0)
		#ax1_ccf.plot(vels,avg_ccf - gp_mean,'-',color='k',label=lab,lw=5.0,zorder=0)
		ax1_ccf.plot(vels,gp_mean,'-',color='r',label=r'$\rm GP$',lw=2.0,zorder=5)
		xx = 0.5*(vels[1:] + vels[:-1])
		ax1_ccf.plot(xx,convolved[1:],'-',color='C6',label=r'$\rm *$',lw=2.0,zorder=5)
		ax1_ccf.plot(vels,convolved,'-',color='C5',label=r'$\rm *2$',lw=2.0,zorder=5)
		ax2_ccf.plot(vels,avg_ccf-convolved,'-',color='C5',lw=2.0,zorder=5)
		ax1_ccf.plot(vels,newline,'--',color='C7',label=r'$\rm Model \ CCF$',lw=2.0)
		#ax1_ccf.plot(vels,newline+gp_mean,'--',color='y',label=r'$\rm Model + GP$',lw=2.0)
		if jitt:
			jterm = gp.kernel.terms[1]
			#print(jterm.jitter)
			ax2_ccf.errorbar(vels,avg_ccf - newline - gp_mean,yerr=np.log(jterm.jitter)*np.ones_like(vels))
		ax2_ccf.plot(vels,avg_ccf - newline - gp_mean,color='k',linestyle='-',lw=5.0,zorder=0)#,mfc='C7')
		out = (vels < -no_bump) | (no_bump < vels)
		#print(gp_mean)
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]  - newline[out],yerr=unc[out],color='k',marker='.',mfc='k',linestyle='none',ecolor='k')
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]  - newline[out],yerr=np.ones(len(vels))[out]*np.mean(oot_sd),color='k',marker='.',mfc='C7',linestyle='none',ecolor='k')
		for ii, idx in enumerate(oots):
			#ax1_ccf.plot(vels,oot_ccfs[:,ii] - gp_mean,zorder=0,label=r'$\rm OOT\ idx.\ {}$'.format(idx),lw=1.0)
			#ax2_ccf.plot(vels,oot_ccfs[:,ii] - newline - gp_mean,zorder=0,lw=1.0)
			#area = np.trapz(oot_ccfs[:,ii] - gp_mean,vels)
			ax1_ccf.plot(vels,oot_ccfs[:,ii]/area,zorder=0,label=r'$\rm OOT\ idx.\ {}$'.format(idx),lw=1.0)
			ax2_ccf.plot(vels,oot_ccfs[:,ii]/area - newline - gp_mean,zorder=0,lw=1.0)


		#ax2_ccf.errorbar(vv[out],cc[out]-ncc[out],yerr=unc_b[out],color='k',marker='o',mfc='C3',ecolor='C3',linestyle='none')
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]-newline[out],yerr=unc[out],color='k',marker='o',mfc='k',ecolor='k',linestyle='none')
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]-newline[out],yerr=np.ones(len(vels))[out]*np.mean(oot_sd),color='k',marker='o',mfc='C7',ecolor='C7',linestyle='none')
		ax2_ccf.axhline(0.0,linestyle='--',color='C7',zorder=-4)

		ax2_ccf.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
		ax2_ccf.set_ylabel(r'$\rm Residuals$',fontsize=font)
		ax1_ccf.set_ylabel(r'$\rm CCF$',fontsize=font)
		ax1_ccf.legend(fancybox=True,shadow=True,fontsize=0.9*font,
			ncol=round(len(oots)/2+1),loc='upper center',bbox_to_anchor=(0.5, 1.55))
			#ncol=1,loc='right',bbox_to_anchor=(1.0, 0.5))

		if (xmajor != None) & (xminor != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax1_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
			ax2_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax2_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
		if (ymajor1 != None) & (yminor1 != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.yaxis.set_major_locator(MultipleLocator(ymajor1))
			ax1_ccf.yaxis.set_minor_locator(MultipleLocator(yminor1))
		if (ymajor2 != None) & (yminor2 != None):
			from matplotlib.ticker import MultipleLocator
			ax2_ccf.yaxis.set_major_locator(MultipleLocator(ymajor2))
			ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

		ax1_ccf.set_xlim(xmin,xmax)
		ax2_ccf.set_xlim(xmin,xmax)
		plt.setp(ax1_ccf.get_xticklabels(),visible=False)
		#figccf.subplots_adjust(hspace=0.05)
		figccf.tight_layout()
		if savefig: figccf.savefig('oot_ccf.pdf')

		## 1D shadow
		if plot_intransit:
			_, _, _, darks, oot_lum, _ = ls_model(
				times,start_grid,ring_grid,
				vel_grid,mu,mu_grid,mu_mean,resol,vels
				)


			bright = np.sum(oot_lum)

			fig_in = plt.figure()

			cmap = plt.get_cmap('Spectral',len(its))
			#cmap = plt.get_cmap('tab20b',len(its))
			sm = plt.cm.ScalarMappable(cmap=cmap)#, norm=plt.normalize(min=0, max=1))
			cbaxes = fig_in.add_axes([0.91, 0.11, 0.02, 0.78])
			cticks = [ii/len(its)+0.05 for ii in range(len(its))]
			#print(cticks)
			cbar = fig_in.colorbar(sm,cax=cbaxes,ticks=cticks)
			cbar.set_label(r'$\rm Exposure \ index \ (Time \Rightarrow)$')
			off = 0
			oots.sort()
			#oots = oots[np.argsort(oots)]
			for ot in oots:
				if not any(ot > np.asarray(its)):
					off += 1

			cticklabs = ['${}$'.format(ii+off) for ii in range(len(its))]
			cbar.ax.set_yticklabels(cticklabs)
			#ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

			ax1 = fig_in.add_subplot(211)
			ax2 = fig_in.add_subplot(212)


			ax1.axhline(0.0,color='C7',linestyle='--')
			ax1.plot(vels,avg_ccf,'k-',lw=4.0,label=r'$\rm Observed\ avg.$')
			ax2.axhline(0.0,color='k')

			for ii, idx in enumerate(its):
				time = times[idx]
				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
				

				ccf = shadow_data[time]['ccf'].copy()

				no_peak = (vel > no_bump) | (vel < -no_bump)
				if use_gp:
					ccf -= np.mean(ccf[no_peak])
					#gp.compute(vel, np.ones(len(vel))*np.mean(unc))
					#gp_mean, var = gp.predict(ccf, vel, return_var=True)
					#ccf -= 0.0#gp_mean
				else:
					poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
					ccf -= vel*poly_pars[0] + poly_pars[1]

				area = np.trapz(ccf,vel)

				#area = np.trapz(ccf,vel)
				ccf /= abs(area)
				ccf *= darks[idx]/bright

		
				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)	
				#nccf -= gp_mean
				

				ax1.plot(vels,nccf,'-',color=cmap(ii),lw=1.0)
				ax2.plot(vels,nccf - avg_ccf,'-',color=cmap(ii),lw=1.0)


			ax1.legend(fancybox=True,shadow=True,fontsize=0.9*font)
			plt.setp(ax1.get_xticklabels(),visible=False)
			fig_in.subplots_adjust(hspace=0.05)
			ax2.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
			ax2.set_ylabel(r'$\rm Exp.\ idx.-Avg.$',fontsize=font)
			ax1.set_ylabel(r'$\rm CCF$',fontsize=font)
			ax1.set_xlim(xmin,xmax)
			ax2.set_xlim(xmin,xmax)
			if savefig: fig_in.savefig('in_minus_out_ccf.pdf')

def plot_oot_ccf_2Gauss(parameters,data,updated_pars=None,oots=None,n_pars=0,chi2_scale=1.0,
	font = 12,savefig=True,path='',no_bump=15,best_fit=True,xmajor=None,xminor=None,
	ymajor1=None,yminor1=None,ymajor2=None,yminor2=None,plot_intransit=True,xmax=None,xmin=None,
	usetex=False,**kwargs):
	'''Plot out-of-transit CCFs.

	

	'''
	

	plt.rc('text',usetex=usetex)


	if n_pars == 0: n_pars = len(parameters['FPs'])

	n_ls = data['LSs']
	pls = parameters['Planets']
	# if updated_pars is not None:
	# 	pars = parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	for par in pars:
	# 		if best_fit: idx = 4
	# 		else: idx = 1
	# 		try:
	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass	
	
	for nn in range(1,n_ls+1):
		label = data['LS_label_{}'.format(nn)]

		shadow_data = data['LS_{}'.format(nn)]
		#chi2scale = data['Chi2 OOT_{}'.format(nn)]

		times = []
		for key in shadow_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]

		v0 = parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
			rv_m += rv_pl
		rv_m += v0



		idxs = [ii for ii in range(len(times))]
		if oots is None:
			oots = data['idxs_{}'.format(nn)]

		print('Number of spectra: {}'.format(len(idxs)))
		print('Using indices {} as out-of-transit spectra'.format(oots))

		its = [ii for ii in idxs if ii not in oots]	
		
		
		
		no_bump = data['No_bump_{}'.format(nn)]
		span = data['Velocity_range_{}'.format(nn)]
		assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))
		
		vel_res = data['Velocity_resolution_{}'.format(nn)]
		vels = np.arange(-span,span,vel_res)
		avg_ccf = np.zeros(len(vels))
		oot_ccfs = np.zeros(shape=(len(vels),len(oots)))
		
		## Create average out-of-transit CCF
		## Shift CCFs to star rest frame
		## and detrend CCFs
		oot_sd = []
		for ii, idx in enumerate(oots):
			time = times[idx]
			vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

			#vels[:,idx] = vel
			no_peak = (vel > no_bump) | (vel < -no_bump)

			ccf = shadow_data[time]['ccf'].copy()

			poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
			ccf -= vel*poly_pars[0] + poly_pars[1]
			zp_idx = np.argmin(ccf)
			zp_x = abs(vel[zp_idx])
			under_curve = (vel < zp_x) & (vel > -zp_x)

			vel_u, ccf_u = vel[under_curve], ccf[under_curve]
			pos = ccf_u > 0.0

			area = np.trapz(ccf_u[pos],vel_u[pos])

			ccf /= abs(area)

			ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
			nccf = ccf_int(vels)
			
			no_peak = (vels > no_bump) | (vels < -no_bump)
			oot_sd.append(np.std(nccf[no_peak]))
				

			oot_ccfs[:,ii] = nccf
			avg_ccf += nccf

		avg_ccf /= len(oots)
		jitter = parameters['LSsigma_{}'.format(nn)]['Value']
		jitter = np.exp(jitter)

		max_idx = np.argmax(avg_ccf)
		min_idx = np.argmin(avg_ccf)

		amp1 = avg_ccf[max_idx]*1.5
		amp2 = abs(avg_ccf[min_idx]*1.5)

		sig2 = abs(vels[min_idx])
		sig1 = sig2/2

		low = np.where(vels < 0.0)[0]
		sub_min = np.amin(avg_ccf[low])

		high = np.where(vels > 0.0)[0]
		sup_min = np.amin(avg_ccf[high])

		if sub_min < sup_min:
			mu2 = -vel_res
		else:
			mu2 = vel_res

		gau2_par, pcov = curve_fit(inv2Gauss,vels,avg_ccf,p0=[amp1,amp2,sig1,sig2,mu2])
		newline = inv2Gauss(vels,gau2_par[0],gau2_par[1],gau2_par[2],gau2_par[3],gau2_par[4])

		unc = np.ones(len(vels))*np.sqrt((np.mean(oot_sd)**2 + jitter**2))
		gp_mean = np.zeros(len(vels))
		lab = r'$\rm Obs.\ avg. \ CCF$'




		red_chi2 = np.sum((avg_ccf-newline)**2/unc**2)/(len(avg_ccf)-n_pars)
		print('## Spectroscopic system {}/{} ##:'.format(nn,label))
		print('\nReduced chi-squared for the oot CCF is:\n\t {:.03f}'.format(red_chi2))
		#print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
		print('Number of data points: {}'.format(len(avg_ccf)))
		print('Number of fitting parameters: {}'.format(n_pars))
		print('#########################')

		figccf = plt.figure()
		ax1_ccf = figccf.add_subplot(211)
		ax2_ccf = figccf.add_subplot(212)

		ax1_ccf.plot(vels,avg_ccf,'-',color='k',label=lab,lw=5.0,zorder=0)
		ax1_ccf.plot(vels,newline,'--',color='C7',label=r'$\rm Model \ CCF$',lw=2.0)
		ax2_ccf.plot(vels,avg_ccf - newline,color='k',linestyle='-',lw=5.0,zorder=0)#,mfc='C7')
		out = (vels < -no_bump) | (no_bump < vels)
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]  - newline[out],yerr=unc[out],color='k',marker='.',mfc='k',linestyle='none',ecolor='k')
		#ax2_ccf.errorbar(vels[out],avg_ccf[out]  - newline[out],yerr=np.ones(len(vels))[out]*np.mean(oot_sd),color='k',marker='.',mfc='C7',linestyle='none',ecolor='k')
		for ii, idx in enumerate(oots):
			ax1_ccf.plot(vels,oot_ccfs[:,ii],zorder=0,label=r'$\rm OOT\ idx.\ {}$'.format(idx),lw=1.0)
			ax2_ccf.plot(vels,oot_ccfs[:,ii] - newline,zorder=0,lw=1.0)


		#ax2_ccf.errorbar(vv[out],cc[out]-ncc[out],yerr=unc_b[out],color='k',marker='o',mfc='C3',ecolor='C3',linestyle='none')
		ax2_ccf.errorbar(vels[out],avg_ccf[out]-newline[out],yerr=unc[out],color='k',marker='o',mfc='k',ecolor='k',linestyle='none')
		ax2_ccf.errorbar(vels[out],avg_ccf[out]-newline[out],yerr=np.ones(len(vels))[out]*np.mean(oot_sd),color='k',marker='o',mfc='C7',ecolor='C7',linestyle='none')
		ax2_ccf.axhline(0.0,linestyle='--',color='C7',zorder=-4)

		ax2_ccf.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
		ax2_ccf.set_ylabel(r'$\rm Residuals$',fontsize=font)
		ax1_ccf.set_ylabel(r'$\rm CCF$',fontsize=font)
		ax1_ccf.legend(fancybox=True,shadow=True,fontsize=0.9*font,
			ncol=round(len(oots)/2+1),loc='upper center',bbox_to_anchor=(0.5, 1.55))
			#ncol=1,loc='right',bbox_to_anchor=(1.0, 0.5))

		if (xmajor != None) & (xminor != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax1_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
			ax2_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax2_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
		if (ymajor1 != None) & (yminor1 != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.yaxis.set_major_locator(MultipleLocator(ymajor1))
			ax1_ccf.yaxis.set_minor_locator(MultipleLocator(yminor1))
		if (ymajor2 != None) & (yminor2 != None):
			from matplotlib.ticker import MultipleLocator
			ax2_ccf.yaxis.set_major_locator(MultipleLocator(ymajor2))
			ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

		ax1_ccf.set_xlim(xmin,xmax)
		ax2_ccf.set_xlim(xmin,xmax)
		plt.setp(ax1_ccf.get_xticklabels(),visible=False)
		#figccf.subplots_adjust(hspace=0.05)
		figccf.tight_layout()
		if savefig: figccf.savefig('oot_ccf.pdf')


def plot_oot_ccf(parameters,data,updated_pars=None,oots=None,n_pars=0,chi2_scale=1.0,
	font = 12,savefig=True,path='',no_bump=15,best_fit=True,xmajor=None,xminor=None,
	ymajor1=None,yminor1=None,ymajor2=None,yminor2=None,plot_intransit=True,xmax=None,xmin=None,
	usetex=False,**kwargs):

	plt.rc('text',usetex=usetex)


	if n_pars == 0: n_pars = len(parameters['FPs'])

	n_ls = data['LSs']
	pls = parameters['Planets']
	if updated_pars is not None:
		pars = parameters['FPs']
		pars = updated_pars.keys()[1:-2]
		if n_pars == 0: n_pars = len(pars)
		for par in pars:
			if best_fit: idx = 4
			else: idx = 1
			try:
				parameters[par]['Value'] = float(updated_pars[par][idx])	
			except KeyError:
				pass	
	
	for nn in range(1,n_ls+1):
		label = data['LS_label_{}'.format(nn)]

		shadow_data = data['LS_{}'.format(nn)]
		chi2scale = data['Chi2 OOT_{}'.format(nn)]

		times = []
		for key in shadow_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]

		v0 = parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			#rv_pl = rv_model(parameters,time,n_planet=pl,n_rv=nn,RM=calc_RM)
			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
			rv_m += rv_pl
		rv_m += v0


		resol = data['Resolution_{}'.format(nn)]
		thick = data['Thickness_{}'.format(nn)]
		#start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)

		start_grid = data['Start_grid_{}'.format(nn)]
		ring_grid = data['Ring_grid_{}'.format(nn)]
		vel_grid = data['Velocity_{}'.format(nn)]
		mu = data['mu_{}'.format(nn)]
		mu_grid = data['mu_grid_{}'.format(nn)]
		mu_mean	= data['mu_mean_{}'.format(nn)]

		no_bump = data['No_bump_{}'.format(nn)]
		span = data['Velocity_range_{}'.format(nn)]
		assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))
		vel_res = data['Velocity_resolution_{}'.format(nn)]

		vels = np.arange(-span,span,vel_res)

		vel_model, model_ccf, oot_lum = ls_model(
			times,start_grid,ring_grid,
			vel_grid,mu,mu_grid,mu_mean,resol,vels,
			n_planet='b',n_rv=nn,oot=True
			)

		bright = np.sum(oot_lum)


		idxs = [ii for ii in range(len(times))]
		if oots is None:
			oots = data['idxs_{}'.format(nn)]

		print('Number of spectra: {}'.format(len(idxs)))
		print('Using indices {} as out-of-transit spectra'.format(oots))

		its = [ii for ii in idxs if ii not in oots]	
		
		nvel = len(shadow_data[times[0]]['vel'])
		
		
		avg_ccf = np.zeros(len(vels))
		oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

		## Create average out-of-transit CCF
		## Used to create shadow for in-transit CCFs
		## Shift CCFs to star rest frame
		## and detrend CCFs
		oot_sd_b = []
		for ii, idx in enumerate(oots):
			time = times[idx]
			vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
			keep = (vel > -span) & (vel < span)
			vel = vel[keep]

			#vels[:,idx] = vel
			no_peak = (vel > no_bump) | (vel < -no_bump)

			ccf = shadow_data[time]['ccf'].copy()
			ccf = ccf[keep]
			poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)

			ccf -= vel*poly_pars[0] + poly_pars[1]

			# zp_idx = np.argmin(ccf)
			# zp_x = abs(vel[zp_idx])
			
			# under_curve = (vel < zp_x) & (vel > -zp_x)

			# ccf_u = ccf[under_curve]
			# vel_u = vel[under_curve]
			# pos = ccf_u > 0.0
			# ccf_p = ccf_u[pos]
			# vel_p = vel_u[pos]
			# area = np.trapz(ccf_p,vel_p)

			area = np.trapz(ccf,vel)
			ccf /= abs(area)

			ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
			nccf = ccf_int(vels)

			vv,cc = get_binned(vels,nccf)
			no_peak_b = (vv > no_bump) | (vv < -no_bump)
			oot_sd_b.append(np.std(cc[no_peak_b]))
				

			oot_ccfs[:,ii] = nccf
			avg_ccf += nccf
			#avg_vel += vel

		avg_ccf /= len(oots)
		#avg_vel /= len(oots)





		## Here we simply fit our average out-of-transit CCF
		## to an out-of-transit model CCF
		## Hard-coded
		jitter = parameters['RVsigma_{}'.format(nn)]['Value']
		jitter = 0.0

		model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
		newline = model_int(vels)



		#unc = np.ones(len(vel))*np.mean(oot_sd_b)*jitter
		vv,cc = get_binned(vels,avg_ccf)
		vn,ncc = get_binned(vels,newline)
		unc_b = np.ones(len(vv))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
		unc = np.ones(len(vels))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
		unc_b *= chi2scale
		red_chi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-n_pars)
		print('## Spectroscopic system {}/{} ##:'.format(nn,label))
		print('\nReduced chi-squared for the oot CCF is:\n\t {:.03f}'.format(red_chi2))
		print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
		print('Number of data points: {}'.format(len(cc)))
		print('Number of fitting parameters: {}'.format(n_pars))
		print('#########################')


		figccf = plt.figure()
		ax1_ccf = figccf.add_subplot(211)
		ax2_ccf = figccf.add_subplot(212)

		ax1_ccf.plot(vels,avg_ccf,'-',color='k',label=r'$\rm Observed\ avg. \ CCF$',lw=5.0,zorder=0)
		ax1_ccf.plot(vels,newline,'--',color='C7',label=r'$\rm Model \ CCF$',lw=2.0)
		ax2_ccf.plot(vels,avg_ccf  - newline,color='k',linestyle='-',lw=5.0,zorder=0)#,mfc='C7')
		out = (vv < -no_bump) | (no_bump < vv)
		out2 = (vels < -no_bump) | (no_bump < vels)
		ax2_ccf.errorbar(vels[out2],avg_ccf[out2]  - newline[out2],yerr=unc[out2],color='k',marker='.',mfc='C7',linestyle='none')
		for ii, idx in enumerate(oots):
			ax1_ccf.plot(vels,oot_ccfs[:,ii],zorder=0,label=r'$\rm OOT\ idx.\ {}$'.format(idx),lw=1.0)
			ax2_ccf.plot(vels,oot_ccfs[:,ii] - newline,zorder=0,lw=1.0)


		ax2_ccf.errorbar(vv[out],cc[out]-ncc[out],yerr=unc_b[out],color='k',marker='o',mfc='C3',ecolor='C3',linestyle='none')
		ax2_ccf.axhline(0.0,linestyle='--',color='C7',zorder=-4)

		ax2_ccf.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
		ax2_ccf.set_ylabel(r'$\rm Residuals$',fontsize=font)
		ax1_ccf.set_ylabel(r'$\rm CCF$',fontsize=font)
		ax1_ccf.legend(fancybox=True,shadow=True,fontsize=0.9*font,
			ncol=round(len(oots)/2+1),loc='upper center',bbox_to_anchor=(0.5, 1.35))
			#ncol=1,loc='right',bbox_to_anchor=(1.0, 0.5))

		if (xmajor != None) & (xminor != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax1_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
			ax2_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
			ax2_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
		if (ymajor1 != None) & (yminor1 != None):
			from matplotlib.ticker import MultipleLocator

			ax1_ccf.yaxis.set_major_locator(MultipleLocator(ymajor1))
			ax1_ccf.yaxis.set_minor_locator(MultipleLocator(yminor1))
		if (ymajor2 != None) & (yminor2 != None):
			from matplotlib.ticker import MultipleLocator
			ax2_ccf.yaxis.set_major_locator(MultipleLocator(ymajor2))
			ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

		ax1_ccf.set_xlim(xmin,xmax)
		ax2_ccf.set_xlim(xmin,xmax)
		plt.setp(ax1_ccf.get_xticklabels(),visible=False)
		figccf.subplots_adjust(hspace=0.05)
		figccf.tight_layout()
		if savefig: figccf.savefig('oot_ccf.pdf')

		if plot_intransit:

			_, _, _, darks, oot_lum, _ = ls_model(
				times,start_grid,ring_grid,
				vel_grid,mu,mu_grid,mu_mean,resol,vels
				)


			bright = np.sum(oot_lum)

			fig_in = plt.figure()

			cmap = plt.get_cmap('Spectral',len(its))
			#cmap = plt.get_cmap('tab20b',len(its))
			sm = plt.cm.ScalarMappable(cmap=cmap)#, norm=plt.normalize(min=0, max=1))
			cbaxes = fig_in.add_axes([0.91, 0.11, 0.02, 0.78])
			cticks = [ii/len(its)+0.05 for ii in range(len(its))]
			#print(cticks)
			cbar = fig_in.colorbar(sm,cax=cbaxes,ticks=cticks)
			cbar.set_label(r'$\rm Exposure \ index \ (Time \Rightarrow)$')

			cticklabs = ['${}$'.format(ii) for ii in range(len(its))]
			cbar.ax.set_yticklabels(cticklabs)
			#ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

			ax1 = fig_in.add_subplot(211)
			ax2 = fig_in.add_subplot(212)


			ax1.axhline(0.0,color='C7',linestyle='--')
			ax1.plot(vels,avg_ccf,'k-',lw=4.0,label=r'$\rm Observed\ avg.$')
			ax2.axhline(0.0,color='k')

			for ii, idx in enumerate(its):
				time = times[idx]
				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3

				keep = (vel > -span) & (vel < span)
				vel = vel[keep]
				
				#vels[:,idx] = vel
				no_peak = (vel > no_bump) | (vel < -no_bump)

				ccf = shadow_data[time]['ccf'].copy()
				ccf = ccf[keep]

				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)

				ccf -= vel*poly_pars[0] + poly_pars[1]

				# zp_idx = np.argmin(ccf)
				# zp_x = abs(vel[zp_idx])

				# under_curve = (vel < zp_x) & (vel > -zp_x)

				# ccf_u = ccf[under_curve]
				# vel_u = vel[under_curve]
				# pos = ccf_u > 0.0
				# ccf_p = ccf_u[pos]
				# vel_p = vel_u[pos]
				# area = np.trapz(ccf_p,vel_p)
				
				area = np.trapz(ccf,vel)
				
				ccf /= abs(area)
				
				ccf *= darks[idx]/bright#blc[idx]

		
				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)	

				vv,cc = get_binned(vels,nccf)
				no_peak_b = (vv > no_bump) | (vv < -no_bump)
				oot_sd_b.append(np.std(cc[no_peak_b]))

				ax1.plot(vels,nccf,'-',color=cmap(ii),lw=1.0)
				ax2.plot(vels,nccf-avg_ccf,'-',color=cmap(ii),lw=1.0)


			ax1.legend(fancybox=True,shadow=True,fontsize=0.9*font)
			plt.setp(ax1.get_xticklabels(),visible=False)
			fig_in.subplots_adjust(hspace=0.05)
			ax2.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
			ax2.set_ylabel(r'$\rm Exp.\ idx.-Avg.$',fontsize=font)
			ax1.set_ylabel(r'$\rm CCF$',fontsize=font)
			ax1.set_xlim(xmin,xmax)
			ax2.set_xlim(xmin,xmax)
			if savefig: fig_in.savefig('in_minus_out_ccf.pdf')

def plot_distortion(param_fname,data_fname,updated_pars=None,observation=False,
	oots=None,n_pars=0,display=[],background='white',model=False,ax=None,stack = {},
	font = 14,savefig=True,path='',contact_color='C3',movie_time=False,return_slopes=False,
	no_bump=15,best_fit=True,get_vp=False,tickfontsize=10,usetex=False,**kwargs):

	#from matplotlib.gridspec import GridSpec

	plt.rc('text',usetex=usetex)

	if not get_vp:
		business.params_structure(param_fname)
		business.data_structure(data_fname)
	if updated_pars is not None:

		pars = business.parameters['FPs']
		pars = updated_pars.keys()[1:-2]
		if n_pars == 0: n_pars = len(pars)
		for par in pars:
			if best_fit: idx = 4
			else: idx = 1
			try:
				business.parameters[par]['Value'] = float(updated_pars[par][idx])	
			except KeyError:
				pass				
	pls = business.parameters['Planets']
	n_sl = business.data['SLs']

	from matplotlib.ticker import MultipleLocator, FormatStrFormatter,ScalarFormatter

	for nn in range(1,n_sl+1):
		slope_data = business.data['SL_{}'.format(nn)]
		label = business.data['RV_label_{}'.format(nn)]
		times = []
		for key in slope_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]
		v0 = business.parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			p2, t2 = business.parameters['P_{}'.format(pl)]['Value'],business.parameters['T0_{}'.format(pl)]['Value']
			rv_pl = business.rv_model(times,n_planet=pl,n_rv=nn,RM=False)
	
			rv_m += rv_pl
		rv_m += v0


		for pl in pls:
			try:
				t0n = business.parameters['Spec_{}:T0_{}'.format(nn,pl)]['Value']
				business.parameters['T0_{}'.format(pl)]['Value'] = t0n				
			except KeyError:
				pass




			per, T0 = business.parameters['P_{}'.format(pl)]['Value'], business.parameters['T0_{}'.format(pl)]['Value'] 
			ar, inc = business.parameters['a_Rs_{}'.format(pl)]['Value'], business.parameters['inc_{}'.format(pl)]['Value']*np.pi/180.
			rp = business.parameters['Rp_Rs_{}'.format(pl)]['Value']
			ecc, ww = business.parameters['e_{}'.format(pl)]['Value'], business.parameters['w_{}'.format(pl)]['Value']*np.pi/180.
			b = ar*np.cos(inc)*(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t14 = per/np.pi * np.arcsin( np.sqrt( ((1 + rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t23 = per/np.pi * np.arcsin( np.sqrt( ((1 - rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))
			if np.isnan(t14): continue


			model_slope = business.localRV_model(times,n_planet=pl)				

			### HARD-CODED
			darks = business.lc_model(times,n_planet=pl,n_phot=1)


			idxs = [ii for ii in range(len(times))]
			if oots is None:
				oots = business.data['idxs_{}'.format(nn)]

			if model:
				resol = business.data['Resolution_{}'.format(nn)]
				thick = business.data['Thickness_{}'.format(nn)]
				start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = business.ini_grid(resol,thick)

	

				vel_model, shadow_model, _, _, _, _ = business.ls_model(
					times,start_grid,ring_grid,
					vel_grid,mu,mu_grid,mu_mean,resol,
					oot=False,n_planet=pl,n_rv=nn
					)

				vel_m_arr = np.asarray([vel_model]*len(times))


			print('Number of spectra: {}'.format(len(idxs)))
			print('Using indices {} as out-of-transit spectra'.format(oots))

			its = [ii for ii in idxs if ii not in oots]	

			pp = dynamics.time2phase(times[its],per,T0)*24*per

			nvel = len(slope_data[times[0]]['vel'])
			vels = np.zeros(shape=(nvel,len(its)))
			ccfs = np.zeros(shape=(nvel,len(its)))
			avg_ccf = np.zeros(nvel)
			for ii, idx in enumerate(oots):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
				no_peak = (vel > no_bump) | (vel < -no_bump)
				

				ccf = slope_data[time]['ccf']
				area = np.trapz(ccf,vel)
				ccf /= area	

				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				ccf -= vel*poly_pars[0] + poly_pars[1]

				# oot_ccfs[:,ii] = ccf
				avg_ccf += ccf

			avg_ccf /= len(oots)

			lam = business.parameters['lam_{}'.format(pl)]['Value']*np.pi/180
			vsini = business.parameters['vsini']['Value'] 


			fnames = []
			xs = np.array([])
			ys = np.array([])
			cs = np.array([])
			mus = np.array([])
			for ii, idx in enumerate(its):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
				vels[:,ii] = vel
				no_peak = (vel > no_bump) | (vel < -no_bump)

				cos_f, sin_f = dynamics.true_anomaly(time, T0, ecc, per, ww)
				xx, yy = dynamics.xy_pos(cos_f,sin_f,ecc,ww,ar,inc,lam)
				# xs = np.append(xs,xx)
				# ys = np.append(ys,yy)
				rr = np.sqrt(xx**2 + yy**2)
				mm = np.sqrt(1 - (rr)**2)
				if rr > 1.0: mm = 0.0
				mus = np.append(mus,mm)
				#print(xx,yy)
				cs = np.append(cs,xx*vsini)
				
				ccf = slope_data[time]['ccf']
				area = np.trapz(ccf,vel)
				ccf /= area
				
				sd = np.std(ccf[no_peak])

				ccf *= darks[idx]#/bright#blc[ii]		
				shadow = avg_ccf - ccf
				poly_pars = np.polyfit(vel[no_peak],shadow[no_peak],1)
				
				shadow -=  vel*poly_pars[0] + poly_pars[1]
				ccfs[:,ii] = shadow


			cmap = plt.get_cmap('RdBu_r',len(cs))
			if ax == None:
				fig = plt.figure()
				ax = fig.add_subplot(111)
			ax.set_facecolor(background)
			ilikedis = False

			if ilikedis:
				for ii, idx in enumerate(its):
					vel = vels[:,ii]
					shadow = ccfs[:,ii]

					if len(display):
						if ii in display:
							if observation:
								ax.plot(vel,shadow,color='k',lw=2.0,zorder=8)
								ax.plot(vel,shadow,color=cmap(ii),lw=1.5,zorder=9,linestyle='--')
							if model:
								#print(shadow_model[idx])
								ax.plot(vel_model,shadow_model[idx],color='k',lw=2.,zorder=5,linestyle='-')
								ax.plot(vel_model,shadow_model[idx],color=cmap(ii),lw=1.5,zorder=6,linestyle='-')


					else:
						ax.plot(vel,shadow,color=cmap(ii))
				ax.set_xlim(-16,16)
				ax.yaxis.set_major_locator(MultipleLocator(0.0004))
				ax.yaxis.set_minor_locator(MultipleLocator(0.0002))
			else:
				from matplotlib.legend_handler import HandlerBase

				class AnyObjectHandler(HandlerBase):
					def create_artists(self, legend, orig_handle,
									x0, y0, width, height, fontsize, trans):
						l1 = plt.Line2D([x0,y0+15.0], [0.4*height,0.4*height],linestyle='-', color='k',lw=2.5,zorder=-1)	        
						l2 = plt.Line2D([x0,y0+15.0], [0.4*height,0.4*height],linestyle='-', color=orig_handle[1],lw=1.5)

						return [l1, l2]

				labs, hands = [], []
				labs2 = []
				off = 0
				disp = -0.0007
				for key in stack.keys():
					idxs = stack[key]
					avg_shadow = np.zeros(len(ccfs[:,0]))
					if model:
						avg_vel_model = np.zeros(len(shadow_model[0,:]))
						avg_model = np.zeros(len(shadow_model[0,:]))
					
					avg_vel = np.zeros(len(ccfs[:,0]))
					avg_mu = 0
					for idx in idxs:
						vel = vels[:,idx]
						shadow = ccfs[:,idx]
						avg_vel += vel - cs[idx]
						if model:
							avg_vel_model += vel_model - cs[idx]
							avg_model += shadow_model[idx]
						avg_shadow += shadow
						avg_mu += mus[idx]

						#print(mus[idx])
					avg_vel /= len(idxs)
					avg_shadow /= len(idxs)
					if model:
						avg_model /= len(idxs)
						avg_vel_model /= len(idxs)
					
					avg_color = int(np.mean(idxs))
					avg_mu /= len(idxs)
					#print(avg_mu)
					label = r'$\rm Index \ ' + str(idxs)[1:-1] + ':\ \langle \mu \\rangle={:.2f}'.format(avg_mu) + '$'
					#label = r'$\rm Index \ ' + str(idxs)[1:-1] + '$'
					labs.append(label)
					label2 = r'$\rm  \mu={:.1f}'.format(avg_mu) + '$'
					labs2.append(label2)
					hands.append((0.2,cmap(avg_color)))

					ax.plot(avg_vel,avg_shadow+off,color='k',lw=2.5,zorder=5,linestyle='-')
					ax.plot(avg_vel,avg_shadow+off,color=cmap(avg_color),lw=1.5,zorder=6,linestyle='-')
					if model:
						ax.plot(avg_vel_model,avg_model+off,color='k',lw=2.5,zorder=5,linestyle='-')
						ax.plot(avg_vel_model,avg_model+off,color=cmap(avg_color),lw=1.5,zorder=6,linestyle='-')

					ax.axhline(off,color='C7',zorder=0,linestyle='--')
					off += disp

				ax.legend(hands, labs,ncol=1,#bbox_to_anchor=(0.7,1.0),
							handler_map={tuple: AnyObjectHandler()},
							fancybox=True,shadow=True,fontsize=0.7*font)#,


				ax.set_xlim(-14,14)
				
				ax.yaxis.set_major_locator(MultipleLocator(0.0005))
				ax.yaxis.set_minor_locator(MultipleLocator(0.00025))

			ax.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
			ax.set_ylabel(r'$\rm Distortion$',fontsize=font)
			
			ax.xaxis.set_major_locator(MultipleLocator(5))
			ax.xaxis.set_minor_locator(MultipleLocator(2.5))
			ax.tick_params(axis='both',labelsize=tickfontsize)

			plt.tight_layout()

			if savefig: plt.savefig(path+'distortion2.pdf')


# =============================================================================
# Slope of planet across disk
# =============================================================================

def plot_slope(parameters,data,
	#updated_pars=None,
	oots=None,n_pars=0,
	font = 12,savefig=True,path='',
	contact_color='C3',movie_time=False,return_slopes=False,
	no_bump=15,best_fit=True,get_vp=False,
	usetex=False,**kwargs):
	'''Plot the subplanetary velocities.

	Function to plot the subplanetary velocities/the slope across the stellar disk.

	'''

	plt.rc('text',usetex=usetex)

	# if not get_vp:
	# 	business.params_structure(param_fname)
	# 	business.data_structure(data_fname)
	# if updated_pars is not None:

	# 	pars = business.parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	for par in pars:
	# 		if best_fit: idx = 4
	# 		else: idx = 1
	# 		try:
	# 			business.parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass				
	# pls = business.parameters['Planets']
	# n_sl = business.data['SLs']


	if n_pars == 0: n_pars = len(parameters['FPs'])
	
	pls = parameters['Planets']
	n_sl = data['SLs']
	# def time2phase(time,per,T0):
	# 	phase = ((time-T0)%per)/per
	# 	for ii in range(len(phase)):
	# 		if phase[ii] > 0.5: phase[ii] = phase[ii] - 1
	# 	return phase
	# if updated_pars is not None:

	# 	pars = parameters['FPs']
	# 	pars = updated_pars.keys()[1:-2]
	# 	if n_pars == 0: n_pars = len(pars)
	# 	idx = 1
	# 	if (updated_pars.shape[0] > 3) & best_fit: idx = 4
	# 	for par in pars:
	# 		try:
	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
	# 		except KeyError:
	# 			pass	

	slopes = {}

	for nn in range(1,n_sl+1):
		slope_data = data['SL_{}'.format(nn)]
		label = data['SL_label_{}'.format(nn)]
		slopes['RV_'+str(nn)] = {}
		times = []
		for key in slope_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]
		v0 = parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			p2, t2 = parameters['P_{}'.format(pl)]['Value'],parameters['T0_{}'.format(pl)]['Value']
			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
	
			rv_m += rv_pl
		rv_m += v0



		for pl in pls:
			try:
				t0n = parameters['Spec_{}:T0_{}'.format(nn,pl)]['Value']
				parameters['T0_{}'.format(pl)]['Value'] = t0n				
			except KeyError:
				pass

			per, T0 = parameters['P_{}'.format(pl)]['Value'], parameters['T0_{}'.format(pl)]['Value'] 
			ar, inc = parameters['a_Rs_{}'.format(pl)]['Value'], parameters['inc_{}'.format(pl)]['Value']*np.pi/180.
			rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
			omega = parameters['w_{}'.format(pl)]['Value']
			ecc, ww = parameters['e_{}'.format(pl)]['Value'], parameters['w_{}'.format(pl)]['Value']*np.pi/180.
			b = ar*np.cos(inc)*(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t14 = per/np.pi * np.arcsin( np.sqrt( ((1 + rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t23 = per/np.pi * np.arcsin( np.sqrt( ((1 - rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))
			if np.isnan(t14): continue

			model_slope = localRV_model(times,n_planet=pl)
		

			### HARD-CODED
			darks = lc_model(times,n_planet=pl,n_phot=1)


			idxs = [ii for ii in range(len(times))]
			if oots is None:
				oots = data['idxs_{}'.format(nn)]

			print('Number of spectra: {}'.format(len(idxs)))
			print('Using indices {} as out-of-transit spectra'.format(oots))

			its = [ii for ii in idxs if ii not in oots]	

			its = [ii for ii in idxs if ii not in oots]	
			pp = time2phase(times[its],per,T0)*24*per
			
			its = []
			for idx, p in enumerate(pp):
				if (p < t14*24/2) & (p > -t14*24/2):
					its.append(idx)
			pp = pp[its]

			#nvel = len(slope_data[times[0]]['vel'])
			#vels = np.zeros(shape=(nvel,len(times)))
			#oot_ccfs = np.zeros(shape=(nvel,len(oots)))
			#avg_ccf = np.zeros(nvel)
			vel_res = data['Velocity_resolution_{}'.format(nn)]
			vels = np.array([])

			
			no_bump = data['No_bump_{}'.format(nn)]
			span = data['Velocity_range_{}'.format(nn)]
			assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))

			# for ii, idx in enumerate(oots):
			# 	time = times[idx]
			# 	vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
			# 	vels[:,idx] = vel
			# 	no_peak = (vel > no_bump) | (vel < -no_bump)
				

			# 	ccf = slope_data[time]['ccf']
			# 	area = np.trapz(ccf,vel)
			# 	ccf /= area	

			# 	poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
			# 	ccf -= vel*poly_pars[0] + poly_pars[1]

			# 	oot_ccfs[:,ii] = ccf
			# 	avg_ccf += ccf
			for ii, idx in enumerate(oots):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
				if not ii:
					# vel_min, vel_max = min(vel), max(vel)
					# span  = (vel_max - vel_min)
					# vels = np.arange(vel_min+span/10,vel_max-span/10,vel_res)
					vels = np.arange(-span,span,vel_res)
					avg_ccf = np.zeros(len(vels))
					oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

				no_peak = (vel > no_bump) | (vel < -no_bump)
				
				ccf = slope_data[time]['ccf']
				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				ccf -= vel*poly_pars[0] + poly_pars[1]

				area = np.trapz(ccf,vel)
				ccf /= area	

				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)	

				oot_ccfs[:,ii] = nccf
				avg_ccf += nccf

			avg_ccf /= len(oots)
			rvs = np.array([])
			errs = np.array([])

			lam = parameters['lam_{}'.format(pl)]['Value']*np.pi/180
			vsini = parameters['vsini']['Value'] 


			## With this you supply the mid-transit time 
			## and then the time of periastron is calculated
			## from S. R. Kane et al. (2009), PASP, 121, 886. DOI: 10.1086/648564
			if (ecc > 1e-5) & (omega != 90.):
				f = np.pi/2 - ww
				ew = 2*np.arctan(np.tan(f/2)*np.sqrt((1 - ecc)/(1 + ecc)))
				Tw = T0 - per/(2*np.pi)*(ew - ecc*np.sin(ew))
			else:
				Tw = T0

			fit_params = lmfit.Parameters()
			fnames = []
			xs = np.array([])
			ys = np.array([])
			for ii, idx in enumerate(its):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
				no_peak = (vel > no_bump) | (vel < -no_bump)

				cos_f, sin_f = true_anomaly(time, Tw, ecc, per)
				xx, yy = xy_pos(cos_f,sin_f,ecc,ww,ar,inc,lam)

				xs = np.append(xs,xx)
				ys = np.append(ys,yy)

				ccf = slope_data[time]['ccf']
				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)				
				ccf -=  vel*poly_pars[0] + poly_pars[1]

				area = np.trapz(ccf,vel)
				ccf /= area
				
				sd = np.std(ccf[no_peak])

				ccf *= darks[idx]#/bright#blc[ii]
				
				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)

				shadow = avg_ccf - nccf

				peak = np.where((vels > -no_bump) & (vels < no_bump))
				#peak = np.where((vels > (xx*vsini - vsini/2)) & (vels < (xx*vsini + vsini/2)))
				midx = np.argmax(shadow[peak])
				amp, mu1 = shadow[peak][midx], vels[peak][midx]# get max value of CCF and location

				gau_par, pcov = curve_fit(Gauss,vels,shadow,p0=[amp,xx*vsini,0.2])
				perr = np.sqrt(np.diag(pcov))
				rv = gau_par[1]
				std = perr[1]

				# loc = xx*vsini
				# midx = np.argmin(np.abs(vels - loc))
				# pars = np.polyfit(vels[midx-3:midx+4],shadow[midx-3:midx+4],2)

				# ## The maximum of the parabola
				# rv = -pars[1]/(2*pars[0])
				# ## The curvature is taking as the error.
				# std = np.sqrt(2/pars[0])

				rvs = np.append(rvs,rv)
				errs = np.append(errs,std)
				if movie_time:
					print('Making movie shadow.mp4 - this may take a while')
					movie_fig = plt.figure()
					movie_ax = movie_fig.add_subplot(111)
					movie_ax.axhline(0.0,color='C7',linestyle='--')
					movie_ax.plot(vels,shadow,'k',lw=2.0)
					movie_ax.plot(vels,shadow,'C0',lw=1.5)
					movie_ax.axvline(xx*vsini,color='C1',linestyle='-')
					#movie_ax.plot(vels,Gauss(vels,gau_par[0],gau_par[1],gau_par[2]),'k',lw=2.0)
					#movie_ax.plot(vel,Gauss(vel,gau_par[0],gau_par[1],gau_par[2]),'C7',lw=1.5)

					movie_ax.set_xlabel(r'$\rm Velocity \ (kms/s)$',fontsize=font)
					movie_ax.set_ylabel(r'$\rm Shadow$',fontsize=font)
					#movie_ax.text(min(vel)+1,0.95,r'$\rm Hours \ From \ Midtransit \ {:.3f}$'.format(pp[ii]),fontsize=font)
					fname = 'shadow_no_{:03d}.png'.format(ii)
					fnames.append(fname)
					movie_ax.set_ylim(-0.0004,0.001)
					movie_fig.savefig(fname)
					plt.close()

			if movie_time:
				import subprocess
				import os
				subprocess.call("ffmpeg -framerate 4 -i ./shadow_no_%3d.png -c:v libx264 -r 30 -pix_fmt yuv420p ./shadow.mp4", shell=True)
				for fname in fnames: os.remove(fname)

			slope = localRV_model(times[its])
			#print(xs)
			vsini = parameters['vsini']['Value']
			rv_scale = rvs/vsini
			erv_scale = errs/vsini
			chi2scale = data['Chi2 SL_{}'.format(nn)]
			#chi2scale = 1.0#business.data['Chi2 SL_{}'.format(nn)]
			#erv_scale *= chi2scale
			full = (pp > -1*t23*24/2) & (pp < 1*t23*24/2)
			part = (pp < -1*t23*24/2) | (pp > 1*t23*24/2)
			erv_scale[full] *= chi2scale
			erv_scale[part] *= chi2scale*1.5

			
			print('## Spectroscopic system {}/{} ##:'.format(nn,label))
			red_chi2 = np.sum((rv_scale - slope)**2/erv_scale**2)/(len(rv_scale)-n_pars)
			print('\nReduced chi-squared for the slope is:\n\t {:.03f}'.format(red_chi2))
			print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
			print('Number of data points: {}'.format(len(rv_scale)))
			print('Number of fitting parameters: {}'.format(n_pars))
			print('#########################'.format(nn))


			if get_vp:
				arr = np.zeros(shape=(len(rv_scale),4))
				ss = np.argsort(pp)
				arr[:,0] = times[its][ss]
				arr[:,1] = rv_scale[ss]*vsini
				arr[:,2] = erv_scale[ss]
				arr[:,3] = slope[ss]
				return arr

			fig = plt.figure()
			ax = fig.add_subplot(211)
			ax2 = fig.add_subplot(212)
			ax.errorbar(pp,rv_scale,yerr=erv_scale,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
			ax.errorbar(pp,rv_scale,yerr=erv_scale,marker='o',markersize=4.0,color='C{}'.format(nn-1),linestyle='none',zorder=5)
		
			ax.axhline(0.0,color='C7',zorder=-1,linestyle='--')
			ax.axhline(1.0,color='C0',zorder=-1,linestyle='--')
			ax.axhline(-1.0,color='C0',zorder=-1,linestyle='--')
			ax.axvline(-1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)
			ax.axvline(1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)

			ax.axvline(1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)
			ax.axvline(-1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)

			ax2.axvline(-1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)
			ax2.axvline(1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)

			ax2.axvline(1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)
			ax2.axvline(-1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)

			slope = localRV_model(times[its],n_planet=pl)
			ax.plot(pp,slope,'-',color='k',lw=2.0)
			ax.plot(pp,slope,'-',color='C7',lw=1.0)
			ax.set_ylabel(r'$\mathrm{Local} \ \mathrm{RV} \ (v\sin i)$',fontsize=font)
			ax2.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)
			ax2.set_ylabel(r'$\rm Residuals$',fontsize=font)

			ax2.errorbar(pp,rv_scale-slope,yerr=erv_scale,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
			ax2.errorbar(pp,rv_scale-slope,yerr=erv_scale,marker='o',markersize=4.0,color='C{}'.format(nn-1),linestyle='none',zorder=5)
			ax2.axhline(0.0,color='C7',zorder=-1,linestyle='--')
			slopes['RV_'+str(nn)]['pl_'+pl] = [pp,rv_scale,erv_scale,slope,xs,ys]

			plt.subplots_adjust(wspace=0.0,hspace=0.0)

			if savefig: plt.savefig(path+'slope.png')
	if return_slopes:
		return slopes

def plot_slope_2Gauss(parameters,data,
	oots=None,n_pars=0,
	font = 12,savefig=True,path='',
	contact_color='C3',movie_time=False,return_slopes=False,
	no_bump=15,best_fit=True,get_vp=False,usetex=False,**kwargs):
	'''Plot the subplanetary velocities.

	Function to plot the subplanetary velocities/the slope across the stellar disk.

	'''

	plt.rc('text',usetex=usetex)


	if n_pars == 0: n_pars = len(parameters['FPs'])
	
	pls = parameters['Planets']
	n_sl = data['SLs']

	slopes = {}

	for nn in range(1,n_sl+1):
		slope_data = data['SL_{}'.format(nn)]
		label = data['SL_label_{}'.format(nn)]
		slopes['RV_'+str(nn)] = {}
		times = []
		for key in slope_data.keys():
			try:
				times.append(float(key))
			except ValueError:
				pass
		times = np.asarray(times)
		ss = np.argsort(times)
		times = times[ss]
		v0 = parameters['RVsys_{}'.format(nn)]['Value']
		rv_m = np.zeros(len(times))
		for pl in pls:
			p2, t2 = parameters['P_{}'.format(pl)]['Value'],parameters['T0_{}'.format(pl)]['Value']
			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
	
			rv_m += rv_pl
		rv_m += v0



		for pl in pls:
			try:
				t0n = parameters['Spec_{}:T0_{}'.format(nn,pl)]['Value']
				parameters['T0_{}'.format(pl)]['Value'] = t0n				
			except KeyError:
				pass

			per, T0 = parameters['P_{}'.format(pl)]['Value'], parameters['T0_{}'.format(pl)]['Value'] 
			ar, inc = parameters['a_Rs_{}'.format(pl)]['Value'], parameters['inc_{}'.format(pl)]['Value']*np.pi/180.
			rp = parameters['Rp_Rs_{}'.format(pl)]['Value']
			omega = parameters['w_{}'.format(pl)]['Value']
			ecc, ww = parameters['e_{}'.format(pl)]['Value'], parameters['w_{}'.format(pl)]['Value']*np.pi/180.
			b = ar*np.cos(inc)*(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t14 = per/np.pi * np.arcsin( np.sqrt( ((1 + rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))

			t23 = per/np.pi * np.arcsin( np.sqrt( ((1 - rp)**2 - b**2))/(np.sin(inc)*ar)  )*np.sqrt(1 - ecc**2)/(1 + ecc*np.sin(ww))
			if np.isnan(t14): continue

			model_slope = localRV_model(times,n_planet=pl)
		

			### HARD-CODED
			darks = lc_model(times,n_planet=pl,n_phot=1)


			idxs = [ii for ii in range(len(times))]
			if oots is None:
				oots = data['idxs_{}'.format(nn)]

				print('Number of spectra: {}'.format(len(idxs)))
			print('Number of spectra: {}'.format(len(idxs)))
			print('Using indices {} as out-of-transit spectra'.format(oots))


			its = [ii for ii in idxs if ii not in oots]	
			pp = time2phase(times[its],per,T0)*24*per
			
			its = []
			for idx, p in enumerate(pp):
				if (p < t14*24/2) & (p > -t14*24/2):
					its.append(idx)
			pp = pp[its]
			#its = [ii for ii in idxs if ii not in oots]	

			nvel = len(slope_data[times[0]]['vel'])
			#vels = np.zeros(shape=(nvel,len(times)))
			#oot_ccfs = np.zeros(shape=(nvel,len(oots)))
			#avg_ccf = np.zeros(nvel)
			vel_res = data['Velocity_resolution_{}'.format(nn)]
			vels = np.array([])

			
			no_bump = data['No_bump_{}'.format(nn)]
			span = data['Velocity_range_{}'.format(nn)]
			assert span > no_bump, print('\n ### \n The range of the velocity grid must be larger than the specified range with no bump in the CCF.\n Range of velocity grid is from +/-{} km/s, and the no bump region isin the interval m +/-{} km/s \n ### \n '.format(span,no_bump))

			vels = np.arange(-span,span,vel_res)
			avg_ccf = np.zeros(len(vels))
			oot_ccfs = np.zeros(shape=(len(vels),len(oots)))

			for ii, idx in enumerate(oots):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3

				no_peak = (vel > no_bump) | (vel < -no_bump)
				
				ccf = slope_data[time]['ccf']
				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				ccf -= vel*poly_pars[0] + poly_pars[1]

				area = np.trapz(ccf,vel)
				ccf /= area	

				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)	

				oot_ccfs[:,ii] = nccf
				avg_ccf += nccf

			avg_ccf /= len(oots)
			rvs = np.array([])
			errs = np.array([])

			lam = parameters['lam_{}'.format(pl)]['Value']*np.pi/180
			vsini = parameters['vsini']['Value'] 


			ccf_fig = plt.figure()
			ccf_ax = ccf_fig.add_subplot(211)
			ccf_res = ccf_fig.add_subplot(212)

			## With this you supply the mid-transit time 
			## and then the time of periastron is calculated
			## from S. R. Kane et al. (2009), PASP, 121, 886. DOI: 10.1086/648564
			if (ecc > 1e-5) & (omega != 90.):
				f = np.pi/2 - ww
				ew = 2*np.arctan(np.tan(f/2)*np.sqrt((1 - ecc)/(1 + ecc)))
				Tw = T0 - per/(2*np.pi)*(ew - ecc*np.sin(ew))
			else:
				Tw = T0

			fit_params = lmfit.Parameters()
			fnames = []
			xs = np.array([])
			ys = np.array([])
			for ii, idx in enumerate(its):
				time = times[idx]
				vel = slope_data[time]['vel'] - rv_m[idx]*1e-3
				no_peak = (vel > no_bump) | (vel < -no_bump)

				cos_f, sin_f = true_anomaly(time, Tw, ecc, per, ww)
				xx, yy = xy_pos(cos_f,sin_f,ecc,ww,ar,inc,lam)

				xs = np.append(xs,xx)
				ys = np.append(ys,yy)

				ccf = slope_data[time]['ccf']

				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
				ccf -= vel*poly_pars[0] + poly_pars[1]
				zp_idx = np.argmin(ccf)
				zp_x = abs(vel[zp_idx])
				under_curve = (vel < zp_x) & (vel > -zp_x)

				vel_u, ccf_u = vel[under_curve], ccf[under_curve]
				pos = ccf_u > 0.0

				area = np.trapz(ccf_u[pos],vel_u[pos])
				
				ccf /= area
				
				sd = np.std(ccf[no_peak])

				ccf *= darks[idx]#/bright#blc[ii]
				
				ccf_int = interpolate.interp1d(vel,ccf,kind='cubic',fill_value='extrapolate')
				nccf = ccf_int(vels)
				ccf_ax.plot(vels,nccf)

				max_idx = np.argmax(nccf)
				min_idx = np.argmin(nccf)
				amp1 = nccf[max_idx]*1.5
				amp2 = abs(nccf[min_idx]*1.5)
				#amp, mu1 = shadow[peak][midx], vels[peak][midx]# get max value of CCF and location
				#amp1, amp2, sig1, sig2 = 1.0, 1.0, 1.0, 5.0
				#sig1, sig2 = 1.0, 5.0
				sig2 = abs(vels[min_idx])
				sig1 = sig2/2
				#print(amp1,amp2,sig1,sig2)
				low = np.where(vels < 0.0)[0]
				#sub_idx = np.argmin(avg_ccf[low])
				sub_min = np.amin(avg_ccf[low])
				high = np.where(vels > 0.0)[0]
				#sup_idx = np.argmin(avg_ccf[high])
				sup_min = np.amin(avg_ccf[high])
				if sub_min < sup_min:
					mu2 = -vel_res
				else:
					mu2 = vel_res
				gau2_par, pcov = curve_fit(inv2Gauss,vels,nccf,p0=[amp1,amp2,sig1,sig2,mu2])

				newline = inv2Gauss(vels,gau2_par[0],gau2_par[1],gau2_par[2],gau2_par[3],gau2_par[4])
				ccf_ax.plot(vels,newline,linestyle='--')
				#print(gau2_par[0],gau2_par[1],gau2_par[2],gau2_par[3])
				#		perr = np.sqrt(np.diag(pcov))
				#		rv = gau_par[1]
				#		std = perr[1]

		
				shadow = newline - nccf
				ccf_res.plot(vels,shadow)

				peak = np.where((vels > -no_bump) & (vels < no_bump))
				#peak = np.where((vels > (xx*vsini - vsini/2)) & (vels < (xx*vsini + vsini/2)))
				midx = np.argmax(shadow[peak])
				amp, mu1 = shadow[peak][midx], vels[peak][midx]# get max value of CCF and location

				gau_par, pcov = curve_fit(Gauss,vels,shadow,p0=[amp,xx*vsini,0.2])
				bump = Gauss(vels,gau_par[0],gau_par[1],gau_par[2])
				perr = np.sqrt(np.diag(pcov))
				rv = gau_par[1]
				std = perr[1]

				ccf_res.plot(vels,bump,'--')

				rvs = np.append(rvs,rv)
				errs = np.append(errs,std)

			slope = localRV_model(times[its])
			vsini = parameters['vsini']['Value']
			rv_scale = rvs/vsini
			erv_scale = errs/vsini
			chi2scale = data['Chi2 SL_{}'.format(nn)]
			#full = (pp > -1*t23*24/2) & (pp < 1*t23*24/2)
			#part = (pp < -1*t23*24/2) | (pp > 1*t23*24/2)
			#erv_scale[full] *= chi2scale
			#erv_scale[part] *= chi2scale*1.5

			
			print('## Spectroscopic system {}/{} ##:'.format(nn,label))
			red_chi2 = np.sum((rv_scale - slope)**2/erv_scale**2)/(len(rv_scale)-n_pars)
			print('\nReduced chi-squared for the slope is:\n\t {:.03f}'.format(red_chi2))
			print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
			print('Number of data points: {}'.format(len(rv_scale)))
			print('Number of fitting parameters: {}'.format(n_pars))
			print('#########################'.format(nn))


			if get_vp:
				arr = np.zeros(shape=(len(rv_scale),3))
				ss = np.argsort(pp)
				arr[:,0] = times[its][ss]
				arr[:,1] = rv_scale[ss]
				arr[:,2] = erv_scale[ss]
				return arr

			fig = plt.figure()
			ax = fig.add_subplot(211)
			ax2 = fig.add_subplot(212)
			ax.errorbar(pp,rv_scale,yerr=erv_scale,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
			ax.errorbar(pp,rv_scale,yerr=erv_scale,marker='o',markersize=4.0,color='C{}'.format(nn-1),linestyle='none',zorder=5)
		
			ax.axhline(0.0,color='C7',zorder=-1,linestyle='--')
			ax.axhline(1.0,color='C0',zorder=-1,linestyle='--')
			ax.axhline(-1.0,color='C0',zorder=-1,linestyle='--')
			ax.axvline(-1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)
			ax.axvline(1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)

			ax.axvline(1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)
			ax.axvline(-1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)

			ax2.axvline(-1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)
			ax2.axvline(1*t23*24/2,linestyle='--',color=contact_color,lw=2.0)

			ax2.axvline(1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)
			ax2.axvline(-1*t14*24/2,linestyle='-',color=contact_color,lw=2.0)

			slope = localRV_model(times[its],n_planet=pl)
			ax.plot(pp,slope,'-',color='k',lw=2.0)
			ax.plot(pp,slope,'-',color='C7',lw=1.0)
			ax.set_ylabel(r'$\mathrm{Local} \ \mathrm{RV} \ (v\sin i)$',fontsize=font)
			ax2.set_xlabel(r'$\rm Hours \ From \ Midtransit$',fontsize=font)
			ax2.set_ylabel(r'$\rm Residuals$',fontsize=font)

			ax2.errorbar(pp,rv_scale-slope,yerr=erv_scale,marker='o',markersize=6.0,color='k',linestyle='none',zorder=4)
			ax2.errorbar(pp,rv_scale-slope,yerr=erv_scale,marker='o',markersize=4.0,color='C{}'.format(nn-1),linestyle='none',zorder=5)
			ax2.axhline(0.0,color='C7',zorder=-1,linestyle='--')

			slopes['RV_'+str(nn)]['pl_'+pl] = [pp,rv_scale,erv_scale,slope,xs,ys]

			plt.subplots_adjust(wspace=0.0,hspace=0.0)

			if savefig: plt.savefig(path+'slope.png')
	if return_slopes:
		return slopes


# =============================================================================
# Radial velocity periodogram
# =============================================================================


def plot_rv_pgram(param_fname,data_fname,updated_pars=None,savefig=False,path='',pls=None,
	freq_grid=None,samples_per_peak=5,savefile=False,best_fit=True,usetex=False,**kwargs):#,
#	xminLS=0.0,xmaxLS=None):

	colors = {
		'b' : 'C3',
		'c' : 'C4',
		'd' : 'C5',
		'e' : 'C0',
		'f' : 'C1',
		'g' : 'C2',
		'h' : 'C6',
		'i' : 'C8'
	}


	plt.rc('text',usetex=usetex)

	font = 15
	plt.rc('xtick',labelsize=3*font/4)
	plt.rc('ytick',labelsize=3*font/4)


	bms = 6.0 # background markersize
	fms = 4.0 # foreground markersize
	tms = 40.0 # triangle markersize
	flw = 1.3 # freq linewidth

	business.data_structure(data_fname)
	business.params_structure(param_fname)

	if updated_pars is not None:
		pars = business.parameters['FPs']
		pars = updated_pars.keys()[1:-2]
		if n_pars == 0: n_pars = len(pars)
		idx = 1
		if (updated_pars.shape[0] > 3) & best_fit: idx = 4
		for par in pars:
			try:
				business.parameters[par]['Value'] = float(updated_pars[par][idx])	
			except KeyError:
				pass

	n_rv = business.data['RVs']
	if not pls:
		pls = business.parameters['Planets']

	if n_rv >= 1:
		aa = [business.parameters['a{}'.format(ii)]['Value'] for ii in range(1,3)]
		fig = plt.figure(figsize=(8,8))
		figls = plt.figure(figsize=(8,8))
		#figls_phase = plt.figure(figsize=(8,8))
		n_subs = len(pls) + 1
		if any(np.asarray(aa) != 0): n_subs += 1
		axes_rvs = []
		axes_ls = []
		#axes_phase = []
		for ii in range(1,n_subs+1):
			axes_rvs.append(fig.add_subplot(n_subs,1,ii))
			axes_ls.append(figls.add_subplot(n_subs,1,ii))


		times, rvs, rv_errs = np.array([]), np.array([]), np.array([])
		for nn in range(1,n_rv+1):
			arr = business.data['RV_{}'.format(nn)]
			time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
			times, rvs, rv_errs = np.append(times,time), np.append(rvs,rv), np.append(rv_errs,rv_err)

		zp = np.amin(times)

		RMs = []
		all_times, all_rvs, all_errs = np.array([]), np.array([]), np.array([])
		idxs = np.array([],dtype=int)
		all_rvs_signal_removed = np.array([])
		ins_idxs = np.array([])


		for nn in range(1,n_rv+1):
			#label = business.data['RV_label_{}'.format(nn)]
			arr = business.data['RV_{}'.format(nn)]
			time, rv, rv_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()
			v0 = business.parameters['RVsys_{}'.format(nn)]['Value']
			jitter = business.parameters['RVsigma_{}'.format(nn)]['Value']
			#jitter = np.exp(log_jitter)
			#jitter = log_jitter
			jitter_err = np.sqrt(rv_err**2 + jitter**2)

			drift = aa[1]*(time-zp)**2 + aa[0]*(time-zp)
			#RM = business.data['RM RV_{}'.format(nn)]


			all_times = np.append(all_times,time)
			idxs = np.append(idxs,np.ones(len(time))*nn)
			all_rvs = np.append(all_rvs,rv-v0)
			all_errs = np.append(all_errs,jitter_err)
			all_rvs_signal_removed = np.append(all_rvs_signal_removed,rv-v0-drift)


		#### REMEMBER TO INSTALL CHECK FOR RM FOR NON-TRANSITING PLANETS ####
		#### FOR NOW RM SIGNAL IS NOT INCLUDED IN THE PLOTTED MODEL ###
		#### IT IS HOWEVER PROPERLY REMOVED FROM THE RVS ###


		npoints = 50000
		unp_m = np.linspace(min(all_times)-10.,max(all_times)+10.,npoints)
		model_rvs = np.zeros(npoints)
		temp_rvs = aa[1]*(unp_m-zp)**2 + aa[0]*(unp_m-zp)
		if any(temp_rvs != 0.0):
			ax = axes_rvs[0]
			ax.plot(unp_m,temp_rvs,'-',color='k',lw=1.0,zorder=-1)
		model_rvs += temp_rvs


		ax0 = axes_rvs[0]
		ax0.errorbar(all_times,all_rvs,yerr=all_errs,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
		for nn in range(1,n_rv+1):
			RM = business.data['RM RV_{}'.format(nn)]
			label = business.data['RV_label_{}'.format(nn)]
			idx = nn == idxs
			ax0.errorbar(all_times[idx],all_rvs[idx],yerr=all_errs[idx],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5,label=r'$\rm {}$'.format(label))
		ax0.legend(bbox_to_anchor=(0, 1.05, 1, 0),ncol=n_rv)
		freqs = []
		for ii, pl in enumerate(pls): 
			per = business.parameters['P_{}'.format(pl)]['Value']
			freqs.append(1/per)
			temp_rvs = business.rv_model(unp_m,n_planet=pl,n_rv=1,RM=False)
			ax0.plot(unp_m,temp_rvs,'-',color=colors[pl],lw=1.0,zorder=-1)
			model_rvs += temp_rvs

		ax0.plot(unp_m,model_rvs,'-',color='k',lw=2.0,zorder=-1)
		ax0.plot(unp_m,model_rvs,'-',color='C7',lw=1.0,zorder=0)		

		max_freq = max(freqs)#*2.0
		ax0ls = axes_ls[0]
		LS = LombScargle(all_times, all_rvs, dy=all_errs)
		if freq_grid is None:
			frequency, power = LS.autopower(maximum_frequency=max_freq*1.5,samples_per_peak=samples_per_peak)
		else:			
			power = LS.power(freq_grid)
			frequency = freq_grid
		FAP = LS.false_alarm_probability(power.max())


		midx = np.argmax(power)
		mper = frequency[midx]
		ax0ls.plot(frequency,power,'-',color='k',lw=flw)
		ax0.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
		y1,y2 = ax0ls.get_ylim()
		x1,x2 = ax0ls.get_xlim()
		ax0ls.set_ylabel(r'$\rm LS \ power$',fontsize=font)
		ax0ls.text(0.7*x2,0.8*y2,r'$P_{} = {:0.1f} \ \rm d$'.format('\mathrm{max}',1/mper),color='k',bbox=dict(edgecolor='k',facecolor='w'))
		ax0ls.scatter(mper,y2,marker='v',facecolor='C7',edgecolor='k',s=tms,zorder=5)

		ii = 1
		if any(np.asarray(aa) != 0):
			ax = axes_rvs[ii]
			axls = axes_ls[ii]
			ii += 1
			ax.errorbar(all_times,all_rvs_signal_removed,yerr=all_errs,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
			for nn in range(1,n_rv+1):
				idx = nn == idxs
				ax.errorbar(all_times[idx],all_rvs_signal_removed[idx],yerr=all_errs[idx],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
			LS2 = LombScargle(all_times, all_rvs_signal_removed, dy=all_errs)
			if freq_grid is None:
				frequency, power = LS2.autopower(maximum_frequency=max_freq*1.5,samples_per_peak=samples_per_peak)
			else:			
				power = LS.power(freq_grid)
				frequency = freq_grid

			axls.plot(frequency,power,'-',color='k',lw=flw)
			ax.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
			axls.set_ylabel(r'$\rm LS \ power$',fontsize=font)
			model_rvs -= aa[1]*(unp_m-zp)**2 + aa[0]*(unp_m-zp)
			ax.plot(unp_m,model_rvs,'-',color='k',lw=2.0,zorder=-1)
			ax.plot(unp_m,model_rvs,'-',color='C7',lw=1.0,zorder=0)
			


			for kk, pl in enumerate(pls): 
				temp_rvs = business.rv_model(unp_m,n_planet=pl,n_rv=1,RM=False)
				ax.plot(unp_m,temp_rvs,'-',color=colors[pl],lw=1.0,zorder=-1)

		pers = []
		removed_pls = []
		for jj, pl in enumerate(pls):
			ax = axes_rvs[ii]
			axls = axes_ls[ii]
			axls_vert = axes_ls[ii-1]
			ii += 1
			per = business.parameters['P_{}'.format(pl)]['Value']
			pers.append(per)

			
			for nn in range(1,n_rv+1):
				label = business.data['RV_label_{}'.format(nn)]
				arr = business.data['RV_{}'.format(nn)]
				time = arr[:,0].copy()
				RM = business.data['RM RV_{}'.format(nn)]
				idx = nn == idxs
				all_rvs_signal_removed[idx] -= business.rv_model(all_times[idx],n_planet=pl,n_rv=nn,RM=RM)
				ax.errorbar(all_times[idx],all_rvs_signal_removed[idx],yerr=all_errs[idx],marker='o',markersize=fms,color='C{}'.format(nn-1),linestyle='none',zorder=5)
			ax.errorbar(all_times,all_rvs_signal_removed,yerr=all_errs,marker='o',markersize=bms,color='k',linestyle='none',zorder=4)
			LS3 = LombScargle(all_times, all_rvs_signal_removed, dy=all_errs)
			if freq_grid is None:
				frequency, power = LS3.autopower(maximum_frequency=max_freq*1.5,samples_per_peak=samples_per_peak)
			else:			
				power = LS.power(freq_grid)
				frequency = freq_grid

			axls.plot(frequency,power,'-',color='k',lw=flw)
			midx = np.argmax(power)
			mper = frequency[midx]
			y1,y2 = axls.get_ylim()
			x1,x2 = axls.get_xlim()
			axls.text(0.7*x2,0.8*y2,r'$P_{} = {:0.1f} \ \rm d \ removed$'.format(pl,per),color=colors[pl],bbox=dict(edgecolor='k',facecolor='w'))
			axls.text(0.7*x2,0.4*y2,r'$P_{} = {:0.1f} \ \rm d$'.format('\mathrm{max}',1/mper),color='C7',bbox=dict(edgecolor='k',facecolor='w'))
			#axls.axvline(mper,color='C7',zorder=-1)
			#axls_vert.axvline(1/per,color='C{}'.format(jj),zorder=-1)
			y1_vert,y2_vert = axls_vert.get_ylim()
			axls.scatter(mper,y2,marker='v',facecolor='C7',edgecolor='k',s=tms,zorder=5)
			axls_vert.scatter(1/per,y2_vert,marker='v',facecolor=colors[pl],edgecolor='k',s=tms,zorder=6)

			#ax0ls.axvline(1/per,color='C{}'.format(jj))
			ax.set_ylabel(r'$\rm RV \ (m/s)$',fontsize=font)
			axls.set_ylabel(r'$\rm LS \ power$',fontsize=font)
			removed_pls.append(pl)
			model_rvs = np.zeros(npoints)
			for kk, pl2 in enumerate(pls):
				if pl2 not in removed_pls:
					temp_rvs = business.rv_model(unp_m,n_planet=pl2)
					model_rvs += temp_rvs
					ax.plot(unp_m,temp_rvs,'-',color=colors[pl2],lw=1.0,zorder=-1)
				else:
					per = business.parameters['P_{}'.format(pl2)]['Value']
					axls.scatter(1/per,0.0,marker='^',facecolor=colors[pl2],edgecolor='k',s=tms,zorder=5)


			ax.plot(unp_m,model_rvs,'-',color='k',lw=2.0,zorder=-1)
			ax.plot(unp_m,model_rvs,'-',color='C7',lw=1.0,zorder=0)

		if savefile:
			labels = []
			ii = 1
			for nn in range(1,n_rv+1):
				idx = nn == idxs
				label = business.data['RV_label_{}'.format(nn)]
				if label in labels: 
					label += str(ii)
					ii += 1
				labels.append(label)
				tt, rr, ee = all_times[idx], all_rvs_signal_removed[idx], all_errs[idx]
				arr = np.zeros(shape=(len(tt),3))
				arr[:,0] = tt
				arr[:,1] = rr
				arr[:,2] = ee
				ll = label.replace(' ','')
				np.savetxt(ll+'_rvs_signal_removed.txt',arr)

		for jj, pl in enumerate(pls):
			per = business.parameters['P_{}'.format(pl)]['Value']
			axls.scatter(1/per,0.0,marker='^',facecolor=colors[pl],edgecolor='k',s=tms,zorder=5)
		# 	#axls.axvline(1/per,linestyle='--',color='C{}'.format(kk),zorder=-1)
	
		ax.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)
		axls.set_xlabel(r'$\rm Frequency \ (c/d)$',fontsize=font)
		fig.tight_layout()
		fig.subplots_adjust(hspace=0.0)
		figls.tight_layout()
		figls.subplots_adjust(hspace=0.0)
		if savefig: fig.savefig(path+'rvs_subtracted.pdf')
		if savefig: figls.savefig(path+'rv_periodogram.pdf')

# =============================================================================
# Light curve periodogram
# =============================================================================

def plot_lc_pgram(param_fname,data_fname,updated_pars=None,savefig=False,
	path='',pls=None,tls = False,best_fit=True,usetex=False,**kwargs):#,
#	xminLS=0.0,xmaxLS=None):
	'''Periodogram from light curves.

	'''

	colors = {
		'b' : 'C3',
		'c' : 'C4',
		'd' : 'C5',
		'e' : 'C0',
		'f' : 'C1',
		'g' : 'C2',
		'h' : 'C6',
		'i' : 'C8'
	}


	plt.rc('text',usetex=usetex)

	font = 15
	plt.rc('xtick',labelsize=3*font/4)
	plt.rc('ytick',labelsize=3*font/4)


	bms = 6.0 # background markersize
	fms = 4.0 # foreground markersize
	tms = 40.0 # triangle markersize
	flw = 1.3 # freq linewidth
	blw = 1.5 # back linewidth
	plw = 1.0 # planet linewidth

	business.data_structure(data_fname)
	business.params_structure(param_fname)

	if updated_pars is not None:
		#pars = updated_pars.keys()[1:]
		pars = business.parameters['FPs']
		for par in pars:
			if best_fit:
				business.parameters[par]['Value'] = float(updated_pars[par][4])
			else:
				business.parameters[par]['Value'] = float(updated_pars[par][1])		
	n_phot = business.data['LCs']
	if not pls:
		pls = business.parameters['Planets']

	
	if tls: from transitleastsquares import transitleastsquares as transitls

	if n_phot >= 1:

		npoints = 10000
		fig = plt.figure(figsize=(8,8))
		figls = plt.figure(figsize=(8,8))
		figp = plt.figure()

		n_pls = len(pls) + 1
		axes = []
		axesls = []
		axesp = []
		for ii in range(2): axesp.append(figp.add_subplot(2,1,ii+1))
		if tls:
			figtls = plt.figure()
			axestls = figtls.add_subplot(111)
		for nn in range(n_pls):
			axesls.append(figls.add_subplot(n_pls,1,nn+1))
			axes.append(fig.add_subplot(n_pls,1,nn+1))

		times, fluxs, flux_errs = np.array([]), np.array([]), np.array([])
		idxs = np.array([])
		#ii = 0
		ax = axes[0]
		for nn in range(1,n_phot+1):
			arr = business.data['LC_{}'.format(nn)]
			time, flux, flux_err = arr[:,0].copy(), arr[:,1].copy(), arr[:,2].copy()

			ax.plot(time,flux,'.',color='k',markersize=bms)
			ax.plot(time,flux,'.',color='C{}'.format(nn-1),markersize=fms)
			times, fluxs, flux_errs = np.append(times,time), np.append(fluxs,flux), np.append(flux_errs,flux_err)
			idxs = np.append(idxs,np.ones(len(time))*nn)		
			#ii += 1

		LS = LombScargle(times, fluxs, dy=flux_errs)
		frequency, power = LS.autopower()
		FAP = LS.false_alarm_probability(power.max())
		mper = 1/frequency[np.argmax(power)]

		#axls.text(0.7*max(frequency),0.8*max(power),r'$P_{} = {:0.1f} \ \rm d \ removed$'.format(pl,per),color=colors[pl],bbox=dict(edgecolor='k',facecolor='w'))
		axesls[0].axvline(mper,lw=flw,color='C7')
		axesls[0].semilogx(1/frequency,power,'-',lw=flw,color='k')
		axesp[0].loglog(frequency,power,'-',lw=flw,color='k')
		axesp[0].set_ylabel(r'$\rm LS \ Power$',fontsize=font)
		axesp[1].set_ylabel(r'$\rm LS \ Power$',fontsize=font)
		axesls[0].set_ylabel(r'$\rm LS \ Power$',fontsize=font)
		axes[0].set_ylabel(r'$\rm Rel. \ Int.$',fontsize=font)


		mts = np.linspace(min(times)-1.0,max(times)+1.0,npoints)
		lcs = np.ones(npoints)
		pers = []
		for kk,pl in enumerate(pls):
			#for nn in range(1,n_phot+1):
			lc_pl = business.lc_model(mts,n_planet=pl,n_phot=1)
			#lcs += 1.0 - lc_pl
			ax.plot(mts,lc_pl,'-',color='k',lw=blw)
			ax.plot(mts,lc_pl,'-',color=colors[pl],lw=plw)
			per = business.parameters['P_{}'.format(pl)]['Value']
			axesls[0].axvline(per,color=colors[pl])
			pers.append(per)

		#axesls[0].set_xlim(0.0,max(pers)+1.05*max(pers))
		axesls[0].text(0.7*(max(pers)+max(pers)),0.8*max(power),r'$P_{} = {:0.1f} \ \rm d $'.format('\mathrm{max}',mper),color='C7',bbox=dict(edgecolor='k',facecolor='w'))



		removed_pls = []
		ii = 1
		for pl in pls:
			ax = axes[ii]
			tt_sub, fl_sub, er_sub = np.array([]), np.array([]), np.array([])
			for nn in range(1,n_phot+1):
				
				idx = nn == idxs
				lc_pl = business.lc_model(times[idx],n_planet=pl,n_phot=nn)
				fluxs[idx] = fluxs[idx] - lc_pl + 1.0	

				ax.plot(times[idx],fluxs[idx],'.',color='k',markersize=bms)
				ax.plot(times[idx],fluxs[idx],'.',color='C{}'.format(nn-1),markersize=fms)
			removed_pls.append(pl)
			#for aa, pl2 in enumerate(removed_pls):


			for aa, pl2 in enumerate(pls):
				axesls[ii].axvline(business.parameters['P_{}'.format(pl2)]['Value'],linestyle='--',color=colors[pl2])
				if pl2 not in removed_pls:
					lc_pl = business.lc_model(mts,n_planet=pl2,n_phot=1)
					axesls[ii].axvline(business.parameters['P_{}'.format(pl2)]['Value'],linestyle='-',color=colors[pl2])
					ax.plot(mts,lc_pl,'-',color='k',lw=blw)
					ax.plot(mts,lc_pl,'-',color=colors[pl2],lw=plw)#8-len(removed_pls)))

			LS = LombScargle(times, fluxs, dy=flux_errs)
			frequency, power = LS.autopower()
			FAP = LS.false_alarm_probability(power.max())
			axesls[ii].semilogx(1/frequency,power,'-',lw=flw,color='k')			
			#axesls[ii].set_xlim(0.0,max(pers)+1.05*max(pers))
			axesls[ii].set_ylabel(r'$\rm LS \ Power$',fontsize=font)
			ax.set_ylabel(r'$\rm Rel. \ Int.$',fontsize=font)

			mper = 1/frequency[np.argmax(power)]
			axesls[ii].axvline(mper,lw=flw,color='C7')
			axesls[ii].text(0.7*(max(pers)+max(pers)),0.8*max(power),r'$P_{} = {:0.1f} \ \rm d$'.format('\mathrm{max}',mper),color='C7',bbox=dict(edgecolor='k',facecolor='w'))
			axesls[ii].text(0.7*(max(pers)+max(pers)),0.4*max(power),r'$P_{} = {:0.1f} \ \rm d \ removed$'.format(pl,per),color=colors[pl],bbox=dict(edgecolor='k',facecolor='w'))

			ii += 1

			# 	#os = np.argsort(tt)
		for pl in pls:
			per = business.parameters['P_{}'.format(pl)]['Value']
			axesp[0].axvline(1/per,linestyle='-',lw=flw,color=colors[pl])
			axesp[1].axvline(1/per,linestyle='--',lw=flw,color=colors[pl])
		axesp[1].loglog(frequency,power,'-',lw=flw,color='k')
		axesp[1].set_xlim(min(frequency),max(frequency))
		axesp[0].set_xlim(min(frequency),max(frequency))

		axesls[-1].set_xlabel(r'$\rm Period \ (d)$',fontsize=font)
		axesp[-1].set_xlabel(r'$\rm Frequency \ (c/d)$',fontsize=font)
		for ii in range(len(axesls)-1):
			axesls[ii].set_xticks([])


		ax.set_xlabel(r'$\rm Time \ (BJD)$',fontsize=font)
		fig.tight_layout()
		fig.subplots_adjust(hspace=0.0)
		figls.tight_layout()
		figls.subplots_adjust(hspace=0.0)
		figp.subplots_adjust(hspace=0.0)
		if savefig:
			fig.savefig('full_lc.pdf')
			figls.savefig('LS_period.pdf')
			figp.savefig('LS_freq.pdf')

		if tls:
			import seaborn as sns
			blues = sns.color_palette("Blues")

			c1 = business.parameters['LC1_q1']['Value']
			c2 = business.parameters['LC1_q2']['Value']

			model = transitls(times,fluxs,flux_errs)
			results = model.power(oversampling_factor=2,
					limb_dark='quadratic', u=[c1,c2])
			per = results.period
			axestls.plot(results.periods,results.power,'k',lw=flw)
			axestls.set_xlabel(r'$\rm Period \ (days)$')
			axestls.set_ylabel(r'$\rm SDE$')
			axestls.set_xlim(np.amin(results.periods),np.amax(results.periods))
			axestls.axvline(per,color=blues[2],lw=3,zorder=-1)
			for nn in range(2,30):
				axestls.axvline(nn*per,color=blues[0],ls='--',zorder=-2)
				axestls.axvline(per/nn,color=blues[0],ls='--',zorder=-2)
			if savefig: figtls.savefig('TLS_result.pdf')


# def plot_oot_ccf(parameters,data,updated_pars=None,oots=None,n_pars=0,chi2_scale=1.0,
# 	font = 12,savefig=True,path='',no_bump=15,best_fit=True,xmajor=None,xminor=None,
# 	ymajor1=None,yminor1=None,ymajor2=None,yminor2=None,plot_intransit=True,xmax=None,xmin=None):

# 	plt.rc('text',usetex=usetex)
	
# 	import celerite

# 	#business.data_structure(data_fname)
# 	#business.params_structure(param_fname)
# 	#data_structure(data_fname)
# 	#params_structure(param_fname)

# 	# if updated_pars is not None:
# 	# 	pars = parameters['FPs']
# 	# 	pars = updated_pars.keys()[1:-2]
# 	# 	if n_pars == 0: n_pars = len(pars)
# 	# 	idx = 1
# 	# 	if (updated_pars.shape[0] > 3) & best_fit: idx = 4
# 	# 	for par in pars:
# 	# 		print(parameters[par]['Value'])
# 	# 		try:
# 	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
# 	# 		except KeyError:
# 	# 			pass
# 	if n_pars == 0: n_pars = len(parameters['FPs'])

# 	n_ls = data['LSs']
# 	pls = parameters['Planets']

# 	for nn in range(1,n_ls+1):
# 		label = data['RV_label_{}'.format(nn)]

# 		shadow_data = data['LS_{}'.format(nn)]
# 		chi2scale = data['Chi2 OOT_{}'.format(nn)]

# 		times = []
# 		for key in shadow_data.keys():
# 			try:
# 				times.append(float(key))
# 			except ValueError:
# 				pass
# 		times = np.asarray(times)
# 		ss = np.argsort(times)
# 		times = times[ss]

# 		v0 = parameters['RVsys_{}'.format(nn)]['Value']
# 		rv_m = np.zeros(len(times))
# 		for pl in pls:
# 			#rv_pl = rv_model(parameters,time,n_planet=pl,n_rv=nn,RM=calc_RM)
# 			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
# 			rv_m += rv_pl
# 		rv_m += v0
# 		#print(parameters['xi']['Value'])
# 		# resol = data['Resolution_{}'.format(nn)]
# 		# start_grid = data['Start_grid_{}'.format(nn)]
# 		# ring_grid = data['Ring_grid_{}'.format(nn)]
# 		# vel_grid = data['Velocity_{}'.format(nn)]
# 		# mu = data['mu_{}'.format(nn)]
# 		# mu_grid = data['mu_grid_{}'.format(nn)]
# 		# mu_mean = data['mu_mean_{}'.format(nn)]			
# 		#only_oot = data['Only_OOT_{}'.format(nn)]			
# 		#fit_oot = data['OOT_{}'.format(nn)]	

# 		resol = data['Resolution_{}'.format(nn)]
# 		thick = data['Thickness_{}'.format(nn)]
# 		start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)

# 		#for pl in pls:
# 		# vel_1d, line_oot_norm, lum = ls_model(
# 		# 	#parameters,time,start_grid,ring_grid,
# 		# 	times[-3:],start_grid,ring_grid,
# 		# 	vel_grid,mu,mu_grid,mu_mean,resol,
# 		# 	n_planet=pl,n_rv=nn,oot=True
# 		# 	)

# 		#vel_model, shadow_model, model_ccf, darks, oot_lum, index_error = ls_model(
# 		vel_model, model_ccf, oot_lum = ls_model(
# 			#parameters,time,start_grid,ring_grid,
# 			times,start_grid,ring_grid,
# 			vel_grid,mu,mu_grid,mu_mean,resol,
# 			n_planet='b',n_rv=nn,oot=True
# 			)

# 		bright = np.sum(oot_lum)


# 		## Select out-of/in-transit CCFs
# 		## Hard coded -- modify
# 		#oots = [ii for ii in range(len(times)-3,len(times))]
# 		#its = [ii for ii in range(len(times)-3)]
# 		idxs = [ii for ii in range(len(times))]
# 		#oots = [-3,-2,-1]
# 		if oots is None:
# 			#oots = [ii for ii in range(len(times)-3,len(times))]
# 			oots = data['idxs_{}'.format(nn)]

	print('Number of spectra: {}'.format(len(idxs)))
# 		print('Using indices {} as out-of-transit spectra'.format(oots))

# 		its = [ii for ii in idxs if ii not in oots]	
		
# 		nvel = len(shadow_data[times[0]]['vel'])
# 		vels = np.zeros(shape=(nvel,len(times)))
# 		oot_ccfs = np.zeros(shape=(nvel,len(oots)))
# 		#in_ccfs = np.zeros(shape=(nvel,len(its)))
# 		avg_ccf = np.zeros(nvel)
# 		avg_vel = np.zeros(nvel)

# 		## Create average out-of-transit CCF
# 		## Used to create shadow for in-transit CCFs
# 		## Shift CCFs to star rest frame
# 		## and detrend CCFs
# 		oot_sd = []
# 		for ii, idx in enumerate(oots):
# 			time = times[idx]
# 			vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
# 			vels[:,idx] = vel
# 			no_peak = (vel > no_bump) | (vel < -no_bump)
			


# 			#ccf = np.zeros(len(vel))
# 			#shadow_arr = shadow_data[time]['ccf'].copy()
# 			#ccf = 1 - shadow_arr/np.median(shadow_arr[no_peak])

# 			ccf = shadow_data[time]['ccf'].copy()
# 			#area = np.trapz(ccf,vel)

# 			zp_idx = np.argmin(ccf)
# 			zp_x = abs(vel[zp_idx])
			
# 			under_curve = (vel < zp_x) & (vel > -zp_x)
# 			#area = np.trapz(ccf[under_curve],vel[under_curve])

# 			ccf_u = ccf[under_curve]
# 			vel_u = vel[under_curve]
# 			pos = ccf_u > 0.0
# 			ccf_p = ccf_u[pos]
# 			vel_p = vel_u[pos]
# 			area = np.trapz(ccf_p,vel_p)

# 			ccf /= abs(area)
# 			oot_sd.append(np.std(ccf[no_peak]))

# 			#vv,cc = get_binned(vels[:,idx],ccf)
# 			#no_peak_b = (vv > no_bump) | (vv < -no_bump)
# 			#oot_sd_b.append(np.std(cc[no_peak_b]))
				
# 			#poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)

# 			#cc += vv*poly_pars[0] + poly_pars[1]
# 			#ccf -= vel*poly_pars[0] + poly_pars[1]

# 			oot_ccfs[:,ii] = ccf
# 			avg_ccf += ccf
# 			avg_vel += vel

# 		avg_ccf /= len(oots)
# 		avg_vel /= len(oots)







# 			#avg_ccf += ccf
# 			#avg_vel += vel

# 		## Here we simply fit our average out-of-transit CCF
# 		## to an out-of-transit model CCF
# 		## Hard-coded
# 		log_jitter = parameters['RVsigma_{}'.format(nn)]['Value']
# 		#jitter = np.exp(log_jitter)
# 		jitter = log_jitter
# 		jitter = 0.0

# 		model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
# 		newline = model_int(vels[:,idx])

# 		loga = np.log(np.var(oot_ccfs[:,ii]  - newline))
# 		logc = -np.log(10)
# 		print(loga,logc)
# 		logc = -4.3
# 		loga = -12
# 		kernel = celerite.terms.RealTerm(log_a=loga, log_c=logc)
# 		#kernel = celerite.terms.Matern32Term(log_sigma=loga, log_rho=logc)
# 		unc = np.ones(len(vel))*np.sqrt((np.mean(oot_sd)**2 + jitter**2))
# 		unc *= chi2scale#*2
# 		print(np.mean(unc))
# 		gp = celerite.GP(kernel)
# 		gp.compute(avg_vel,unc)

# 		mu, var = gp.predict(oot_ccfs[:,ii]  - newline, avg_vel, return_var=True)
# 		std = np.sqrt(var)
# 		fig = plt.figure()
# 		ax = fig.add_subplot(211)
# 		ax2 = fig.add_subplot(212)
# 		#ax.errorbar(avg_vel,oot_ccfs[:,ii]-newline,yerr=unc)
# 		ax.errorbar(avg_vel,oot_ccfs[:,ii],yerr=unc)
# 		ax.errorbar(avg_vel,newline+mu)
# 		ax.fill_between(avg_vel, newline+mu+std, newline+mu-std, color='C1', alpha=0.3, edgecolor="none")
# 		#ax.plot(avg_vel, mu, color='C1')
# 		#ax.fill_between(avg_vel, mu+std, mu-std, color='C1', alpha=0.3, edgecolor="none")
# 		ax2.errorbar(avg_vel,oot_ccfs[:,ii]-newline,yerr=unc,linestyle='none')
# 		ax2.fill_between(avg_vel, mu+std, mu-std, color='C1', alpha=0.3, edgecolor="none")

# 		import sys
# 		sys.exit()
# 		#unc = np.ones(len(vel))*np.mean(oot_sd_b)*jitter
# 		vv,cc = get_binned(vels[:,idx],avg_ccf)
# 		vn,ncc = get_binned(vels[:,idx],newline)
# 		unc_b = np.ones(len(vv))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
# 		unc = np.ones(len(vel))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
# 		unc_b *= chi2scale
# 		red_chi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-n_pars)
# 		print('## Spectroscopic system {}/{} ##:'.format(nn,label))
# 		print('\nReduced chi-squared for the oot CCF is:\n\t {:.03f}'.format(red_chi2))
# 		print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
# 		print('Number of data points: {}'.format(len(cc)))
# 		print('Number of fitting parameters: {}'.format(n_pars))
# 		print('#########################')


# 		figccf = plt.figure()
# 		ax1_ccf = figccf.add_subplot(211)
# 		ax2_ccf = figccf.add_subplot(212)

# 		ax1_ccf.plot(vels[:,idx],avg_ccf,'-',color='k',label=r'$\rm Observed\ avg. \ CCF$',lw=5.0,zorder=0)
# 		ax1_ccf.plot(vels[:,idx],newline,'--',color='C7',label=r'$\rm Model \ CCF$',lw=2.0)
# 		ax2_ccf.plot(vels[:,idx],avg_ccf  - newline,color='k',linestyle='-',lw=5.0,zorder=0)#,mfc='C7')
# 		out = (vv < -no_bump) | (no_bump < vv)
# 		out2 = (vels[:,idx] < -no_bump) | (no_bump < vels[:,idx])
# 		ax2_ccf.errorbar(vels[:,idx][out2],avg_ccf[out2]  - newline[out2],yerr=unc[out2],color='k',marker='.',mfc='C7',linestyle='none')
# 		for ii, idx in enumerate(oots):
# 			ax1_ccf.plot(vels[:,idx],oot_ccfs[:,ii],zorder=0,label=r'$\rm OOT\ idx.\ {}$'.format(idx),lw=1.0)
# 			ax2_ccf.plot(vels[:,idx],oot_ccfs[:,ii] - newline,zorder=0,lw=1.0)


# 		ax2_ccf.errorbar(vv[out],cc[out]-ncc[out],yerr=unc_b[out],color='k',marker='o',mfc='C3',ecolor='C3',linestyle='none')
# 		ax2_ccf.axhline(0.0,linestyle='--',color='C7',zorder=-4)

# 		ax2_ccf.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
# 		ax2_ccf.set_ylabel(r'$\rm Residuals$',fontsize=font)
# 		ax1_ccf.set_ylabel(r'$\rm CCF$',fontsize=font)
# 		ax1_ccf.legend(fancybox=True,shadow=True,fontsize=0.9*font,
# 			ncol=round(len(oots)/2+1),loc='upper center',bbox_to_anchor=(0.5, 1.35))
# 			#ncol=1,loc='right',bbox_to_anchor=(1.0, 0.5))

# 		if (xmajor != None) & (xminor != None):
# 			from matplotlib.ticker import MultipleLocator

# 			ax1_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
# 			ax1_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
# 			ax2_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
# 			ax2_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
# 		if (ymajor1 != None) & (yminor1 != None):
# 			from matplotlib.ticker import MultipleLocator

# 			ax1_ccf.yaxis.set_major_locator(MultipleLocator(ymajor1))
# 			ax1_ccf.yaxis.set_minor_locator(MultipleLocator(yminor1))
# 		if (ymajor2 != None) & (yminor2 != None):
# 			from matplotlib.ticker import MultipleLocator
# 			ax2_ccf.yaxis.set_major_locator(MultipleLocator(ymajor2))
# 			ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

# 		ax1_ccf.set_xlim(xmin,xmax)
# 		ax2_ccf.set_xlim(xmin,xmax)
# 		plt.setp(ax1_ccf.get_xticklabels(),visible=False)
# 		figccf.subplots_adjust(hspace=0.05)
# 		figccf.tight_layout()
# 		if savefig: figccf.savefig('oot_ccf.pdf')

# 		if plot_intransit:

# 			_, _, _, darks, oot_lum, _ = ls_model(
# 				#parameters,time,start_grid,ring_grid,
# 				times,start_grid,ring_grid,
# 				vel_grid,mu,mu_grid,mu_mean,resol
# 				)

# 			#vel_m_arr = np.asarray([vel_model]*len(times))

# 			bright = np.sum(oot_lum)

# 			fig_in = plt.figure()

# 			cmap = plt.get_cmap('Spectral',len(its))
# 			#cmap = plt.get_cmap('tab20b',len(its))
# 			sm = plt.cm.ScalarMappable(cmap=cmap)#, norm=plt.normalize(min=0, max=1))
# 			cbaxes = fig_in.add_axes([0.91, 0.11, 0.02, 0.78])
# 			cticks = [ii/len(its)+0.05 for ii in range(len(its))]
# 			#print(cticks)
# 			cbar = fig_in.colorbar(sm,cax=cbaxes,ticks=cticks)
# 			cbar.set_label(r'$\rm Exposure \ index \ (Time \Rightarrow)$')
# 			cticklabs = ['${}$'.format(ii) for ii in range(len(its))]
# 			cbar.ax.set_yticklabels(cticklabs)
# 			#ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))

# 			ax1 = fig_in.add_subplot(211)
# 			ax2 = fig_in.add_subplot(212)


# 			ax1.axhline(0.0,color='C7',linestyle='--')
# 			ax1.plot(vel,avg_ccf,'k-',lw=4.0,label=r'$\rm Observed\ avg.$')
# 			ax2.axhline(0.0,color='k')

# 			for ii, idx in enumerate(its):
# 				time = times[idx]
# 				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
# 				vels[:,idx] = vel
# 				no_peak = (vel > no_bump) | (vel < -no_bump)
				


# 				#ccf = np.zeros(len(vel))
# 				#shadow_arr = shadow_data[time]['ccf'].copy()
# 				#ccf = 1 - shadow_arr/np.median(shadow_arr[no_peak])

# 				ccf = shadow_data[time]['ccf'].copy()

# 				zp_idx = np.argmin(ccf)
# 				zp_x = abs(vel[zp_idx])

# 				under_curve = (vel < zp_x) & (vel > -zp_x)
# 				#area = np.trapz(ccf[under_curve],vel[under_curve])

# 				ccf_u = ccf[under_curve]
# 				vel_u = vel[under_curve]
# 				pos = ccf_u > 0.0
# 				ccf_p = ccf_u[pos]
# 				vel_p = vel_u[pos]
# 				area = np.trapz(ccf_p,vel_p)
				
# 				#area = np.trapz(ccf,vel)
# 				ccf /= abs(area)
				
# 				ccf *= darks[idx]/bright#blc[idx]
# 				#oot_sd.append(np.std(ccf[no_peak]))

# 				vv,cc = get_binned(vels[:,idx],ccf)
# 				no_peak_b = (vv > no_bump) | (vv < -no_bump)
# 				oot_sd_b.append(np.std(cc[no_peak_b]))
					
# 				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)

# 				#cc += vv*poly_pars[0] + poly_pars[1]
# 				ccf -= vel*poly_pars[0] + poly_pars[1]

# 				ax1.plot(vel,ccf,'-',color=cmap(ii),lw=1.0)
# 				ax2.plot(vel,ccf-avg_ccf,'-',color=cmap(ii),lw=1.0)

# 				#in_ccfs[:,ii] = ccf - avg_ccf

# 			ax1.legend(fancybox=True,shadow=True,fontsize=0.9*font)
# 			plt.setp(ax1.get_xticklabels(),visible=False)
# 			fig_in.subplots_adjust(hspace=0.05)
# 			ax2.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
# 			ax2.set_ylabel(r'$\rm Exp.\ idx.-Avg.$',fontsize=font)
# 			ax1.set_ylabel(r'$\rm CCF$',fontsize=font)
# 			ax1.set_xlim(xmin,xmax)
# 			ax2.set_xlim(xmin,xmax)
# 			if savefig: fig_in.savefig('in_minus_out_ccf.pdf')


# def plot_oot_ccf_old(parameters,data,updated_pars=None,oots=None,n_pars=0,chi2_scale=1.0,
# 	font = 12,savefig=True,path='',no_bump=15,best_fit=True,xmajor=None,xminor=None,
# 	ymajor1=None,yminor1=None,ymajor2=None,yminor2=None,plot_intransit=True,xmax=None,xmin=None):

# 	plt.rc('text',usetex=usetex)

# 	#business.data_structure(data_fname)
# 	#business.params_structure(param_fname)
# 	#data_structure(data_fname)
# 	#params_structure(param_fname)

# 	# if updated_pars is not None:
# 	# 	pars = parameters['FPs']
# 	# 	pars = updated_pars.keys()[1:-2]
# 	# 	if n_pars == 0: n_pars = len(pars)
# 	# 	idx = 1
# 	# 	if (updated_pars.shape[0] > 3) & best_fit: idx = 4
# 	# 	for par in pars:
# 	# 		print(parameters[par]['Value'])
# 	# 		try:
# 	# 			parameters[par]['Value'] = float(updated_pars[par][idx])	
# 	# 		except KeyError:
# 	# 			pass
# 	if n_pars == 0: n_pars = len(parameters['FPs'])

# 	n_ls = data['LSs']
# 	pls = parameters['Planets']
# 	for nn in range(1,n_ls+1):
# 		label = data['RV_label_{}'.format(nn)]

# 		shadow_data = data['LS_{}'.format(nn)]
# 		chi2scale = data['Chi2 OOT_{}'.format(nn)]

# 		times = []
# 		for key in shadow_data.keys():
# 			try:
# 				times.append(float(key))
# 			except ValueError:
# 				pass
# 		times = np.asarray(times)
# 		ss = np.argsort(times)
# 		times = times[ss]

# 		v0 = parameters['RVsys_{}'.format(nn)]['Value']
# 		rv_m = np.zeros(len(times))
# 		for pl in pls:
# 			#rv_pl = rv_model(parameters,time,n_planet=pl,n_rv=nn,RM=calc_RM)
# 			rv_pl = rv_model(times,n_planet=pl,n_rv=nn,RM=False)
# 			rv_m += rv_pl
# 		rv_m += v0
# 		#print(parameters['xi']['Value'])
# 		# resol = data['Resolution_{}'.format(nn)]
# 		# start_grid = data['Start_grid_{}'.format(nn)]
# 		# ring_grid = data['Ring_grid_{}'.format(nn)]
# 		# vel_grid = data['Velocity_{}'.format(nn)]
# 		# mu = data['mu_{}'.format(nn)]
# 		# mu_grid = data['mu_grid_{}'.format(nn)]
# 		# mu_mean = data['mu_mean_{}'.format(nn)]			
# 		#only_oot = data['Only_OOT_{}'.format(nn)]			
# 		#fit_oot = data['OOT_{}'.format(nn)]	

# 		resol = data['Resolution_{}'.format(nn)]
# 		thick = data['Thickness_{}'.format(nn)]
# 		start_grid, ring_grid, vel_grid, mu, mu_grid, mu_mean = ini_grid(resol,thick)

# 		for pl in pls:
# 			# vel_1d, line_oot_norm, lum = ls_model(
# 			# 	#parameters,time,start_grid,ring_grid,
# 			# 	times[-3:],start_grid,ring_grid,
# 			# 	vel_grid,mu,mu_grid,mu_mean,resol,
# 			# 	n_planet=pl,n_rv=nn,oot=True
# 			# 	)

# 			#vel_model, shadow_model, model_ccf, darks, oot_lum, index_error = ls_model(
# 			vel_model, model_ccf, oot_lum = ls_model(
# 				#parameters,time,start_grid,ring_grid,
# 				times,start_grid,ring_grid,
# 				vel_grid,mu,mu_grid,mu_mean,resol,
# 				n_planet=pl,n_rv=nn,oot=True
# 				)

# 			bright = np.sum(oot_lum)


# 			## Select out-of/in-transit CCFs
# 			## Hard coded -- modify
# 			#oots = [ii for ii in range(len(times)-3,len(times))]
# 			#its = [ii for ii in range(len(times)-3)]
# 			idxs = [ii for ii in range(len(times))]
# 			#oots = [-3,-2,-1]
# 			if oots is None:
# 				#oots = [ii for ii in range(len(times)-3,len(times))]
# 				oots = data['idxs_{}'.format(nn)]

#	print('Number of spectra: {}'.format(len(idxs)))
# 			print('Using indices {} as out-of-transit spectra'.format(oots))

# 			its = [ii for ii in idxs if ii not in oots]	
			
# 			nvel = len(shadow_data[times[0]]['vel'])
# 			vels = np.zeros(shape=(nvel,len(times)))
# 			oot_ccfs = np.zeros(shape=(nvel,len(oots)))
# 			avg_ccf = np.zeros(nvel)
# 			avg_vel = np.zeros(nvel)

# 			## Create average out-of-transit CCF
# 			## Used to create shadow for in-transit CCFs
# 			## Shift CCFs to star rest frame
# 			## and detrend CCFs
# 			oot_sd_b = []
# 			for ii, idx in enumerate(oots):
# 				time = times[idx]
# 				vel = shadow_data[time]['vel'].copy() - rv_m[idx]*1e-3
# 				vels[:,idx] = vel
# 				no_peak = (vel > no_bump) | (vel < -no_bump)
				


# 				#ccf = np.zeros(len(vel))
# 				#shadow_arr = shadow_data[time]['ccf'].copy()
# 				#ccf = 1 - shadow_arr/np.median(shadow_arr[no_peak])

# 				ccf = shadow_data[time]['ccf'].copy()
# 				poly_pars = np.polyfit(vel[no_peak],ccf[no_peak],1)
# 				ccf -= vel*poly_pars[0] + poly_pars[1]
# 				area = np.trapz(ccf,vel)
# 				ccf /= area	
# 				#oot_sd.append(np.std(ccf[no_peak]))

# 				vv,cc = get_binned(vels[:,idx],ccf)
# 				no_peak_b = (vv > no_bump) | (vv < -no_bump)
# 				oot_sd_b.append(np.std(cc[no_peak_b]))
					
	
# 				#cc += vv*poly_pars[0] + poly_pars[1]

# 				oot_ccfs[:,ii] = ccf
# 				avg_ccf += ccf
# 				avg_vel += vel
# 			avg_ccf /= len(oots)
# 			avg_vel /= len(oots)

# 			## Here we simply fit our average out-of-transit CCF
# 			## to an out-of-transit model CCF
# 			## Hard-coded
# 			log_jitter = parameters['RVsigma_{}'.format(nn)]['Value']
# 			#jitter = np.exp(log_jitter)
# 			jitter = log_jitter
# 			jitter = 0.0

# 			model_int = interpolate.interp1d(vel_model,model_ccf,kind='cubic',fill_value='extrapolate')
# 			newline = model_int(vels[:,idx])



# 			#unc = np.ones(len(vel))*np.mean(oot_sd_b)*jitter
# 			vv,cc = get_binned(vels[:,idx],avg_ccf)
# 			vn,ncc = get_binned(vels[:,idx],newline)
# 			unc_b = np.ones(len(vv))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
# 			unc = np.ones(len(vel))*np.sqrt((np.mean(oot_sd_b)**2 + jitter**2))
# 			#unc = np.ones(len(vel))*(np.mean(oot_sd_b)**2 + jitter**2)
# 			#print(jitter)
# 			#chi2scale = True
# 			#redchi2 = np.sum((avg_ccf-newline)**2/unc**2)/(len(vels[:,idx])/4-3)
# 			unc_b *= chi2scale
# 			red_chi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-n_pars)
# 			print('## Spectroscopic system {}/{} ##:'.format(nn,label))
# 			print('\nReduced chi-squared for the oot CCF is:\n\t {:.03f}'.format(red_chi2))
# 			print('Factor to apply to get a reduced chi-squared around 1.0 is:\n\t {:.03f}\n'.format(np.sqrt(red_chi2)))
# 			print('Number of data points: {}'.format(len(cc)))
# 			print('Number of fitting parameters: {}'.format(n_pars))
# 			print('#########################')


# 			#if chi2scale:
# 				#redchi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-3)
# 				#print(oot_sd_b)
# 				#print(unc_b)
# 				#unc_b *= 1
# 				#unc_b *= np.sqrt(redchi2)
# 				#print(unc_b)
# 				#print(np.sqrt(redchi2))
# 				#redchi2 = np.sum((cc-ncc)**2/unc_b**2)/(len(cc)-4)
# 				#print(redchi2)

# 			figccf = plt.figure()
# 			ax1_ccf = figccf.add_subplot(211)
# 			ax2_ccf = figccf.add_subplot(212)

# 			ax1_ccf.plot(vels[:,idx],avg_ccf,'-',color='k',label=r'$\rm Observed\ avg.\ CCF$',lw=2.0)
# 			ax1_ccf.plot(vels[:,idx],newline,'--',color='C7',label=r'$\rm Model\ CCF$',lw=2.0)
# 			ax2_ccf.plot(vels[:,idx],avg_ccf  - newline,color='k',linestyle='-',lw=2.0)#,mfc='C7')
# 			out = (vv < -no_bump) | (no_bump < vv)
# 			out2 = (vels[:,idx] < -no_bump) | (no_bump < vels[:,idx])
# 			ax2_ccf.errorbar(vels[:,idx][out2],avg_ccf[out2]  - newline[out2],yerr=unc[out2],color='k',marker='.',mfc='C7',linestyle='none')
# 			for ii, idx in enumerate(oots):
# 				ax1_ccf.plot(vels[:,idx],oot_ccfs[:,ii],zorder=-1,label=r'$\rm OOT\ CCF\ index\ {}$'.format(idx))
# 				ax2_ccf.plot(vels[:,idx],oot_ccfs[:,ii] - newline,zorder=-1)


# 			ax2_ccf.errorbar(vv[out],cc[out]-ncc[out],yerr=unc_b[out],color='k',marker='o',mfc='C3',ecolor='C3',linestyle='none')
# 			ax2_ccf.axhline(0.0,linestyle='--',color='C7',zorder=-1)

# 			ax2_ccf.set_xlabel(r'$\rm Velocity \ (km/s)$',fontsize=font)
# 			ax2_ccf.set_ylabel(r'$\rm Residuals$',fontsize=font)
# 			ax1_ccf.set_ylabel(r'$\rm CCF$',fontsize=font)
# 			ax1_ccf.legend(fancybox=True,shadow=True,fontsize=0.9*font)

# 			if (xmajor != None) & (xminor != None):
# 				from matplotlib.ticker import MultipleLocator

# 				ax1_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
# 				ax1_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
# 				ax2_ccf.xaxis.set_major_locator(MultipleLocator(xmajor))
# 				ax2_ccf.xaxis.set_minor_locator(MultipleLocator(xminor))
# 			if (ymajor1 != None) & (yminor1 != None):
# 				from matplotlib.ticker import MultipleLocator

# 				ax1_ccf.yaxis.set_major_locator(MultipleLocator(ymajor1))
# 				ax1_ccf.yaxis.set_minor_locator(MultipleLocator(yminor1))
# 			if (ymajor2 != None) & (yminor2 != None):
# 				from matplotlib.ticker import MultipleLocator
# 				ax2_ccf.yaxis.set_major_locator(MultipleLocator(ymajor2))
# 				ax2_ccf.yaxis.set_minor_locator(MultipleLocator(yminor2))


# 			plt.setp(ax1_ccf.get_xticklabels(),visible=False)
# 			figccf.subplots_adjust(hspace=0.05)
# 			figccf.tight_layout()
# 			figccf.savefig('oot_ccf.pdf')
