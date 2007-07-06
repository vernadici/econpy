'''Some iterative process related classes.

:date: 2007-07-04
:since: 2007-06-25
:copyright: Alan G. Isaac, except where another author is specified.
:license: `MIT license`_

.. _`MIT license`: http://www.opensource.org/licenses/mit-license.php
'''
from __future__ import absolute_import
from __future__ import division

__docformat__ = "restructuredtext en"
__author__ = 'Alan G. Isaac (and others as specified)'
__lastmodified__ = '2007-07-04'



class IterativeProcess(object):
	'''General description of iterative process.

	Requires a criterion.
	The stop criterion must be a function or callable class;
	Criterion may have `state` attribute; if so, `state` is recorded.
	'''
	def __init__(self, criterion): #TODO
		'''Return: None.
		Usually overrriden by user.
		Initialize the iterator.
		Must set a criterion.
		'''
		self.value = None
		self.iterations = 0
		self.history = []
		self.set_criterion(criterion)
	def set_criterion(self, criterion):
		if criterion is None:
			self.criterion = self.default_criterion
		else:
			self.criterion = criterion
	def run(self):
		iterations = 0
		#record initial state
		self.record_history()
		#iterate until criterion satisfied
		testvals = self.testval_generator()
		for testval in testvals:
			iterations += 1
			self.record_history()
			if self.criterion(testval, iterations):
				break
		self.iterations = iterations
		self.finalize()
	def report(self):
		'''Return: string.'''
		final_value = getattr(self, 'value',None)
		optimized = getattr(self.criterion, 'optimized', "Undefined")
		iterations = self.iterations
		report = '''
		Final value:          %s
		Optimized:            %s
		Number of iterations: %d
		'''%(final_value, optimized, iterations)
		return report
	def testval_generator(self):
		while True:
			self.iterate()
			yield self.get_testval()
	#users usually override the following methods
	def default_criterion(self, val, iter):
		return iter >= 100
	def record_history(self):
		'''Should return: None.'''
		pass
	def finalize(self):
		'''Should return: None.
		Should set self.value.
		'''
		pass
	#users must implement the following methods
	def iterate(self):
		'''Should return: None.
		Do one iteration.
		Used by `testval_generator`.
		'''
		return NotImplemented
	def get_testval(self):
		'''Should return: testval.
		The testval must be usable by the criterion.
		Used by `testval_generator`.
		'''
		return NotImplemented


class Bisect(IterativeProcess):
	def __init__(self, func, x1, x2, criterion=None):
		'''Return: None.
		Initialize the bisection iterative process.

		:Parameters:
			f : function (or callable object)
			  real-valued function of a real variable
			x1 : float
			  one side of a sign changing interval
			x2 : float
			  one side of a sign changing interval
			criterion : StopIter
			  convergence criterion
		'''
		IterativeProcess.__init__(self, criterion)  #TODO
		self.func = func
		f1, f2 = func(x1), func(x2)
		if f1 < 0 < f2:
			self.x_neg, self.x_pos = x1, x2
		elif f2 < 0 < f1:
			self.x_neg, self.x_pos = x2, x1
		else:
			raise ValueError("[%f,%f] is not a sign changing interval."%(x1,x2))
	#users usually override the following methods
	def default_criterion(self):
		return (lambda x,y: abs(x[1] - x[0]) < 1e-9) #TODO
	def record_history(self):
		self.history.append(self.get_testval())
	def finalize(self):
		self.value = (self.x_neg + self.x_pos)/2.0
	#users must implement the following methods
	def iterate(self):
		midpt = (self.x_neg + self.x_pos)/2.0
		if self.func(midpt) > 0:
			self.x_pos = midpt
		else:
			self.x_neg = midpt
	def get_testval(self):
		return (self.x_neg , self.x_pos)






#BEGIN cx:optimize.bisect
def bisect(f, x1, x2, eps=1e-8):
	'''Return: a zero of `f`.
	(Simple implementation of bisection algorithm.)

	:parameters:
		f : real-valued function
		x1, x2 : sign changing interval
		eps : convergence criterion
	'''
	#require: sign change over initial interval
	f1, f2 = f(x1), f(x2)
	if f1*f2 > 0:
		raise ValueError
	#initialize xneg, xpos
	xneg, xpos = (x1,x2) if(f2>0) else (x2,x1)
	while xpos-xneg > eps:
		xmid = (xneg+xpos)/2
		if f(xmid) > 0:
			xpos = xmid
		else:
			xneg = xmid
	return (xneg+xpos)/2
#END cx:optimize.bisect



#BEGIN: stop criteria #########################################################
class StopIter(object):
	def __init__(self, precision, maxit = 100):
		if (maxit<1 or not precision>0):
			raise ValueError
		self.precision = precision
		self.maxit = maxit
		self.optimized = False
	def __call__(self, testval, iterations):
		if iterations >= self.maxit:
			stop = True
		elif self.test(testval):
			stop = True
			self.optimized = True
		else:
			stop = False
		return stop
	def test(self, testval):
		'''User must override this method.'''
		return NotImplemented

class AbsDiff(StopIter):
	"""
	True when the *absolute difference* of the test values is below a certain level
	"""
	def test(self, testval):
		val1, val2 = testval
		return abs(val1 - val2) < self.precision


class RelDiff(StopIter):
	"""
	True when the *relative difference* of the test values is below a certain level
	"""
	def test(self, testval):
		val1, val2 = testval
		return abs(val1 - val2) < self.precision * max(abs(val1), abs(val2))

#END: stop criteria #####################################################################
