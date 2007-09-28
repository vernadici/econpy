'''Various least squares routines.
Some are lightweight, in the sense that they do not depend on an array package.

:needs: Python 2.5.1+
:see: `pytrix.py <http://www.american.edu/econ/pytrix/pytrix.py>`
:see: `pyGAUSS.py <http://www.american.edu/econ/pytrix/pyGAUSS.py>`
:see: tseries.py
:see: unitroot.py
:see: pytrix.py
:see: io.py
:note: Please include proper attribution should this code be used in a research project or in other code.
:see: The code below by William Park and more can be found in his `Simple Recipes in Python`_
:copyright: 2007 Alan G. Isaac, except where another author is specified.
:license: `MIT license`_ except where otherwise specified.
:since: 2004-08-04

.. _`Simple Recipes in Python`: http://www.phys.uu.nl/~haque/computing/WPark_recipes_in_python.html
.. _`MIT license`: http://www.opensource.org/licenses/mit-license.php
'''
from __future__ import division, absolute_import
__docformat__ = "restructuredtext en"
__author__ = 'Alan G. Isaac (and others as specified)'
__lastmodified__ = '2007-09-10'

import random, math, operator
import types
import sys,os
import logging
logging.basicConfig(level=logging.WARN)
import time

have_numpy = False
try:
	import numpy as N
	from numpy import linalg
	have_numpy = True
	logging.info("have_numpy is True")
except ImportError:
	logging.info("NumPy not available.")

have_scipy = False
if have_numpy:
	try:
		from numpy.distutils import cpuinfo
	except ImportError:
		logging.warn("numpy.distutils unavailable, cannot test for SSE2 -> SciPy disabled.")
		pass                  #safest to leave have_scipy = False
	else:
		#unfortunately some of scipy.stats expects sse2 and will segfault if absent!!
		cpu = cpuinfo.cpuinfo()
		if cpu._has_sse2():
			logging.info("SSE2 detected")
			try:
				from scipy import stats
				logging.info("successful import of scipy.stats as stats")
			except ImportError:
				logging.info("SciPy cannot be imported -> no probabilities computed.")
			else:
				have_scipy = True
				logging.info("have_scipy is True")
		else:
			logging.warn("Cannot detect SSE2; disabling SciPy")



class OLS(object):
	'''Least squares estimates for a **single** equation.

	Example use::

		result = OLS(y, x)
		print result
		print result.resids
	
	:Ivariables:
		`nobs` : int
			rows(dep), the number of observations
		`coefs` : float array
			the least squares solution
		`cov` : array
			2d covariance array for coefficient estimates
		`resids` : array
			Tx1 array (dep - indep * coefs)
		`sigma2` : float
			(resids' * resids)/(T-K)
		`se` : array
			coefficient standard errors
		`tvals` : array
			t-ratios for the coefficient estimates
		`pvals` : array
			p-values for the coefficient estimates
		`pvalF` : scalar
			p-value for regression F statistic, based on F distribution
		`xTx` : array
			KxK array (roughly, indep' * indep)
		`xTy` : array
			Kx1 array (indep' * dep)
	:warning: adds intercept
	:requires: NumPy
	:requires: time (standard library)
	:see: Russell Davidson and James G. MacKinnon,
          _Estimation and Inference in Econometrics_
          (New York: Oxford, 1993)
	:see: http://www.scipy.org/Cookbook/OLS different approach but shared goals
	:todo: accept recarrays
	:date: 2006-12-08
	:since: 2004-08-11
	:author: Alan G. Isaac
	'''
	def __init__(self,dep,indep, dep_name='', indep_names='', constant=1, trend=None):
		'''
		:Parameters:
			`dep` : array
				(T x 1) array, the LHS variable
			`indep` : array
				(T x K) array, the RHS variables, in columns
		'''
		#make X sets self.nvars, self.nobs, self.indep_names
		self.indep_names = indep_names
		X = self.makeX(indep=indep, constant=constant, trend=trend)
		self.X = X  #used for end_points ... need for anything else?
		Y = N.mat(dep).reshape(-1,1)  #TODO single equation only
		try:
			results = linalg.lstsq(X,Y)[:2]  #OLS estimates
			coefs = results[0]    #matrix arguments -> matrix
			self.ess = results[1][0]  #sum of squared residuals
		except ImportError:
			raise NotImplementedError("OLS requires NumPy")
		assert (len(dep) == len(indep)), "Number of observations do not agree."
		self.yvar = Y.var()
		self.dep_name = dep_name or 'y'
		#data based attributes
		self.xTx = X.T * X
		self.xTy = X.T * Y
		self.fitted = X*coefs
		resids = N.ravel(Y - self.fitted)
		assert abs(self.ess - N.dot(resids,resids))<0.001 #check error sum of squares TODO: delete
		self._resids = resids                          #resids is a property
		#end of matrix algebra
		self.coefs = N.ravel(coefs)                     #self.coefs is a 1d array
		self.df_e = self.nobs - self.ncoefs				# degrees of freedom, error 
		self.sigma2 = self.ess / self.df_e              # sigma^2 = e'e/(T-K)
		self.llf, self.aic, self.bic = self.llf()
		# convenience declarations: attributes to be computed as needed
		self._cov = None                                #the parameter covariance matrix
		self._standard_errors = None                    #the parameter standard errors
		self._tvals = None
		self._pvals = None
		# other attributes
		t = time.localtime()
		self.date = time.strftime("%a, %d %b %Y",t)
		self.time = time.strftime("%H:%M:%S",t)
		################
		#stuff from Vince
		################ 
		self.R2 = 1 - self.resids.var()/self.yvar			# model R-squared
		self.R2adj = 1-(1-self.R2)*((self.nobs-1)/(self.nobs-self.ncoefs))	# adjusted R-square 
		self.df_r = self.ncoefs - 1						# degrees of freedom, regression 
		self.F = (self.R2/self.df_r) / ((1-self.R2)/self.df_e)	# model F-statistic
		self._pvalF = None
	def get_cov(self):
		'''get covariance matrix for solution; compute if nec'''
		if self._cov is None:
			self._cov = self.sigma2*self.xTx.I.A     #covariance matrix, as array
		#TODO var-cov(b),shd use invpd when availabe
		return self._cov
	cov = property(get_cov, None, None, "parameter covariance matrix")
	def get_standard_errors(self):	# coef. standard errors
		'''compute standard errors for solution'''
		if self._standard_errors is None:
			self._standard_errors = N.sqrt(self.cov.diagonal())
		return self._standard_errors
	se = property(get_standard_errors, None, None, "coefficient standard errors")
	def get_tvals(self):
		if self._tvals is None:
			self._tvals = self.coefs / self.se						# coef. t-statistics
		return self._tvals
	tvals = property(get_tvals, None, None, "t-ratios for parameters")
	def get_pvals(self):
		if self._pvals is None:
			if have_scipy:
				self._pvals = (1-stats.t.cdf(N.abs(self.tvals), self.df_e)) * 2	# coef. p-values
			else:
				logging.warn("SciPy unavailable. (Needed to compute p-values.)")
				self._pvals = [N.inf for _ in range(self.ncoefs)]
		return self._pvals
	pvals = property(get_pvals, None, None, "p-values for coef t-ratios, based on Student-t distribution")
	def get_pvalF(self):
		if self._pvalF is None:
			if have_scipy:
				self.pvalF = 1-stats.f.cdf(self.F, self.df_r, self.df_e)	# F-statistic p-value
			else:
				logging.warn("SciPy unavailable. (Needed to compute p-values.)")
				self._pvalF = N.inf
				print self._pvalF
		return self._pvalF
	pvalF = property(get_pvalF, None, None, "p-values for F statistic, based on F distribution")
	def get_resids(self):
		return self._resids
	resids = property(get_resids, None, None, "regression residuals")
	def slope_intercept(self, xcol=0):
		X = self.X.A         #as array
		x = X[:,xcol]
		means = X.mean(axis=0)
		means[xcol] = 0
		intercept = N.dot(self.coefs, means)
		slope = self.coefs[xcol]
		return slope, intercept
	def llf(self):
		"""Return model log-likelihood and two information criteria.

		:author: Vincent Nijs & Alan Isaac
		"""
		# Model log-likelihood, AIC, and BIC criterion values 
		nobs, ncoefs, ess = self.nobs, self.ncoefs, self.ess
		llf = -(nobs*1/2)*(1+math.log(2*math.pi)) - (nobs/2)*math.log(ess/nobs)
		aic = -2*llf/nobs + (2*ncoefs/nobs)
		bic = -2*llf/nobs + (ncoefs*math.log(nobs))/nobs
		return llf, aic, bic
	def makeX(self, indep, constant, trend):
		X = N.asmatrix(indep)
		if len(X)==1:  #must have been a one dimensional indep
			X = X.T
		nobs = len(X)
		self.nobs = nobs
		self.nvars = X.shape[1]  #variables shd NOT include constant
		self.indep_names = self.indep_names or tuple("x%02i"%(i+1) for i in range(self.nvars))
		if constant and trend is not None:
			#add constant term and trend
			constant = constant*N.ones( (nobs, 1) )
			trend = (N.arange(nobs)-N.mat([trend])).T
			X = N.hstack( [X, constant, trend] )
			self.indep_names += ('Constant', 'Trend')
			self.ncoefs = self.nvars + 2
		elif constant:
			#add constant term
			constant = constant*N.ones( (nobs, 1) )
			X = N.hstack( [X, constant] )
			self.indep_names += ('Constant',)
			self.ncoefs = self.nvars + 1
		elif trend is not None:
			#add linear trend
			trend = (N.arange(nobs)-N.mat([trend])).T
			X = N.hstack( [X, trend] )
			self.indep_names += ('Trend',)
			self.ncoefs = self.nvars + 1
		else:
			self.ncoefs = self.nvars
		assert (self.nobs, self.ncoefs) == X.shape
		return X
	def print_results(self):
		'''Return None.  Print results.
		'''
		print self
	def __str__(self):
		# use to print output
		header_template = '''
==============================================================================
==============================================================================
Dependent Variable: %(dep_name)s
Method: Least Squares
Date: %(date)s
Time: %(time)s
# obs:              %(nobs)5d
# RHS variables:    %(ncoefs)5d
==============================================================================
''' + 5*"%-15s"%('variable','coefficient','std. Error','t-statistic','pval.') + "\n"
		header_dict = dict(dep_name=self.dep_name, indep_names=self.indep_names,
		date=self.date, time=self.time, nobs=self.nobs, ncoefs=len(self.coefs))
		result_template = "%-15s" + 4*"% -15.5f"
		result = []
		for i in range(len(self.coefs)):
			result.append(result_template % tuple([self.indep_names[i],self.coefs[i],self.se[i],self.tvals[i],self.pvals[i]]) )
		modelstat_template = '''
==============================================================================
Model stats
------------------------------------------------------------------------------
Log likelihood       %(llf)10.3f        
R-squared            %(rsq)10.3f             Adjusted R-squared    %(R2adj)10.3f            
F-statistic          %(F)10.3f             Prob (F-statistic)    %(pvalF)10.3f            
AIC criterion        %(aic)10.3f             BIC criterion         %(bic)10.3f
==============================================================================
'''
		modelstat_dict = dict(llf=self.llf, rsq=self.R2, R2adj=self.R2adj, F=self.F,pvalF=self.pvalF,aic=self.aic,bic=self.bic)
		resid_stats_template = '''
==============================================================================
Residual stats
==============================================================================
Durbin-Watson stat    % -5.6f' % tuple([self.R2, self.dw()])
Omnibus stat        % -5.6f' % tuple([self.R2adj, omni])    Prob(Omnibus stat)    % -5.6f' % tuple([self.F, omnipv])
JB stat                % -5.6f' % tuple([self.Fpv, JB]) Prob(JB)            % -5.6f' % tuple([ll, JBpv])
Skew     Kurtosis            % -5.6f' % tuple([skew, kurtosis])
==============================================================================
'''
		return (header_template%header_dict)+'\n'.join(result).replace('1.#INF','.') + (modelstat_template%modelstat_dict)





def linreg(X, Y):
	"""Linear regression of y = ax + b. ::

		real, real = linreg(list, list)

	Returns coefficients to the regression line "y=ax+b" from x[] and
	y[].  Basically, it solves ::
	
		 Sxx a + Sx b = Sxy
		  Sx a +  N b = Sy

	where ::

		Sxy = \sum_i x_i y_i
		Sx = \sum_i x_i
		Sy = \sum_i y_i.

	The solution is ::
	
		 a = (Sxy N - Sy Sx)/det
		 b = (Sxx Sy - Sx Sxy)/det

	where ``det = Sxx N - Sx^2``.  In addition, ::
	
		 Var|a| = s^2 |Sxx Sx|^-1 = s^2 | N  -Sx| / det
			|b|       |Sx  N |          |-Sx Sxx|
		 s^2 = {\sum_i (y_i - \hat{y_i})^2 \over N-2}
			 = {\sum_i (y_i - ax_i - b)^2 \over N-2}
			 = residual / (N-2)
		 R^2 = 1 - {\sum_i (y_i - \hat{y_i})^2 \over \sum_i (y_i - \mean{y})^2}
			 = 1 - residual/meanerror

	It also prints a few other data, ::
	
		 N, a, b, R^2, s^2,

	which are useful in assessing the confidence of estimation.

	Only the coefficients of regression line are returned,
	since they are usually what I want.
	Other informations is sent to stdout to be read later.  

	:author: William Park
	"""
	from math import sqrt
	if len(X) != len(Y):  raise ValueError, 'unequal length'

	N = len(X)
	Sx = Sy = Sxx = Syy = Sxy = 0.0
	for x, y in map(None, X, Y):
		Sx = Sx + x
		Sy = Sy + y
		Sxx = Sxx + x*x
		Syy = Syy + y*y
		Sxy = Sxy + x*y
	det = Sxx * N - Sx * Sx
	a, b = (Sxy * N - Sy * Sx)/det, (Sxx * Sy - Sx * Sxy)/det

	meanerror = residual = 0.0
	for x, y in map(None, X, Y):
		meanerror = meanerror + (y - Sy/N)**2
		residual = residual + (y - a * x - b)**2
	RR = 1 - residual/meanerror
	ss = residual / (N-2)
	Var_a, Var_b = ss * N / det, ss * Sxx / det
	 
	print "y=ax+b"
	print "N= %d" % N
	print "a= %g \\pm t_{%d;\\alpha/2} %g" % (a, N-2, sqrt(Var_a))
	print "b= %g \\pm t_{%d;\\alpha/2} %g" % (b, N-2, sqrt(Var_b))
	print "R^2= %g" % RR
	print "s^2= %g" % ss
	 
	return a, b














class ols:
	"""
	Author: Vincent Nijs (+ ?)

	Email: v-nijs at kellogg.northwestern.edu

	Last Modified: Mon Jan 15 17:56:17 CST 2007
	
	Dependencies: See import statement at the top of this file

	Doc: Class for multi-variate regression using OLS

	For usage examples of other class methods see the class tests at the bottom of this file. To see the class in action
	simply run this file using 'python ols.py'. This will generate some simulated data and run various analyses. If you have rpy installed
	the same model will also be estimated by R for confirmation.

	Input:
		y = dependent variable
		y_varnm = string with the variable label for y
		x = independent variables, note that a constant is added by default
		x_varnm = string or list of variable labels for the independent variables
	
	Output:
		There are no values returned by the class. Summary provides printed output.
		All other measures can be accessed as follows:

		Step 1: Create an OLS instance by passing data to the class

			m = ols(y,x,y_varnm = 'y',x_varnm = ['x1','x2','x3','x4'])

		Step 2: Get specific metrics

			To print the coefficients: 
				>>> print m.b
			To print the coefficients p-values: 
				>>> print m.p
	
	"""

	def __init__(self,y,x,y_varnm = 'y',x_varnm = ''):
		"""
		Initializing the ols class. 
		"""
		self.y = y
		self.x = c_[ones(x.shape[0]),x]
		self.y_varnm = y_varnm
		if not isinstance(x_varnm,list): 
			self.x_varnm = ['const'] + list(x_varnm)
		else:
			self.x_varnm = ['const'] + x_varnm

		# Estimate model using OLS
		self.estimate()

	def estimate(self):

		# estimating coefficients, and basic stats
		self.inv_xx = inv(dot(self.x.T,self.x))
		xy = dot(self.x.T,self.y)
		self.b = dot(self.inv_xx,xy)					# estimate coefficients

		self.nobs = self.y.shape[0]						# number of observations
		self.ncoef = self.x.shape[1]					# number of coef.
		self.df_e = self.nobs - self.ncoef				# degrees of freedom, error 
		#TODO: fix!
		self.df_r = self.ncoef - 1						# degrees of freedom, regression 

		self.e = self.y - dot(self.x,self.b)			# residuals
		self.sse = dot(self.e,self.e)/self.df_e			# SSE
		self.se = sqrt(diagonal(self.sse*self.inv_xx))	# coef. standard errors
		self.t = self.b / self.se						# coef. t-statistics
		self.p = (1-stats.t.cdf(abs(self.t), self.df_e)) * 2	# coef. p-values

		self.R2 = 1 - self.e.var()/self.y.var()			# model R-squared
		self.R2adj = 1-(1-self.R2)*((self.nobs-1)/(self.nobs-self.ncoef))	# adjusted R-square

		self.F = (self.R2/self.df_r) / ((1-self.R2)/self.df_e)	# model F-statistic
		self.Fpv = 1-stats.f.cdf(self.F, self.df_r, self.df_e)	# F-statistic p-value

	def dw(self):
		"""
		Calculates the Durbin-Waston statistic
		"""
		de = diff(self.e,1)
		dw = dot(de,de) / dot(self.e,self.e);

		return dw

	def omni(self):
		"""
		Omnibus test for normality
		"""
		return stats.normaltest(self.e) 
	
	def JB(self):
		"""
		Calculate residual skewness, kurtosis, and do the JB test for normality
		"""

		# Calculate residual skewness and kurtosis
		skew = stats.skew(self.e) 
		kurtosis = 3 + stats.kurtosis(self.e) 
		
		# Calculate the Jarque-Bera test for normality
		JB = (self.nobs/6) * (square(skew) + (1/4)*square(kurtosis-3))
		JBpv = 1-stats.chi2.cdf(JB,2);

		return JB, JBpv, kurtosis, skew

	def ll(self):
		"""
		Calculate model log-likelihood and two information criteria
		"""
		
		# Model log-likelihood, AIC, and BIC criterion values 
		ll = -(self.nobs*1/2)*(1+N.log(2*math.pi)) - (self.nobs/2)*N.log(N.dot(self.e,self.e)/self.nobs)
		aic = -2*ll/self.nobs + (2*self.ncoef/self.nobs)
		bic = -2*ll/self.nobs + (self.ncoef*N.log(self.nobs))/self.nobs

		return ll, aic, bic
	
	def summary(self):
		"""
		Printing model output to screen
		"""

		# local time & date
		t = time.localtime()

		# extra stats
		ll, aic, bic = self.ll()
		JB, JBpv, skew, kurtosis = self.JB()
		omni, omnipv = self.omni()

		# printing output to screen
		print '\n=============================================================================='
		print "Dependent Variable: " + self.y_varnm
		print "Method: Least Squares"
		print "Date: ", time.strftime("%a, %d %b %Y",t)
		print "Time: ", time.strftime("%H:%M:%S",t)
		print '# obs:				%5.0f' % self.nobs
		print '# variables:		%5.0f' % self.ncoef 
		print '=============================================================================='
		print 'variable		coefficient		std. Error		t-statistic		prob.'
		print '=============================================================================='
		for i in range(len(self.x_varnm)):
			print '''% -5s			% -5.6f		% -5.6f		% -5.6f		% -5.6f''' % tuple([self.x_varnm[i],self.b[i],self.se[i],self.t[i],self.p[i]]) 
		print '=============================================================================='
		print 'Models stats							Residual stats'
		print '=============================================================================='
		print 'R-squared			% -5.6f			Durbin-Watson stat	% -5.6f' % tuple([self.R2, self.dw()])
		print 'Adjusted R-squared	% -5.6f			Omnibus stat		% -5.6f' % tuple([self.R2adj, omni])
		print 'F-statistic			% -5.6f			Prob(Omnibus stat)	% -5.6f' % tuple([self.F, omnipv])
		print 'Prob (F-statistic)	% -5.6f			JB stat				% -5.6f' % tuple([self.Fpv, JB])
		print 'Log likelihood		% -5.6f			Prob(JB)			% -5.6f' % tuple([ll, JBpv])
		print 'AIC criterion		% -5.6f			Skew				% -5.6f' % tuple([aic, skew])
		print 'BIC criterion		% -5.6f			Kurtosis			% -5.6f' % tuple([bic, kurtosis])
		print '=============================================================================='
