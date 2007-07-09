'''
Unit tests for Pestieau replication.

:see: http://docs.python.org/lib/minimal-example.html for an intro to unittest
:see: http://agiletesting.blogspot.com/2005/01/python-unit-testing-part-1-unittest.html
:see: http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/305292
'''
from __future__ import absolute_import
import unittest
import random

from tests_config import econpy  #tests_config.py modifies sys.path to find econpy
from econpy.abs.pestieau1984oep import agents
from econpy.pytrix import utilities, iterate, fmath



class testPestieau(unittest.TestCase):
	def setUp(self):
		self.N = 5
		self.wealths = [random.random() for _ in range(2*self.N)]
		self.indivs = [agents.Indiv(sex=x) for x in "MF"*self.N]
	'''
	def test_match_exclude(self):
		males = self.indivs[:2]
		females = self.indivs[-2:]
		for i in range(2):
			males[i].siblings.add(females[i])
			females[i].siblings.add(males[i])
		mf = blindermodel.match_exclude(males,females, lambda x,y: x in y.siblings)
		self.assertEqual(mf , [(males[0],females[1]),(males[1],females[0])] )
	def test_match_exclude2(self):
		g1 = range(5)
		g2 = range(5)
		random.shuffle(g2)
		mf = blindermodel.match_exclude(g1,g2, lambda x,y: x != y)
		self.assertEqual(mf , [(0,0),(1,1),(2,2),(3,3),(4,4)] )
	def test_random2sexer(self):
		s = blindermodel.random2sexer(10)
		for si in s:
			self.assert_(si in ['MM','MF','FM','FF'])
	'''
	def test_ability(self):
		indiv = self.indivs[0]
		ability = agents.compute_ability(indiv, 0.5, 2)
		print ability
	def test_PestieauCohort(self):
		indivs = self.indivs
		cohort = agents.PestieauCohort(indivs)
		self.assertEqual(len(cohort),len(indivs))
		for i in indivs:
			self.assert_(i.sex in "MF")
	def test_permutations(self):
		x = utilities.permutations([1,2])
		y = utilities.permutations(range(3))
		z = list( utilities.permutationsg(range(3)) )
		self.assertEqual(x,[[1,2],[2,1]])
		self.assertEqual(y,z)
	def test_calc_gini(self):
		#test that two Gini formulae give same rsult
		gini1 = utilities.calc_gini(self.wealths)
		gini2 = utilities.calc_gini2(self.wealths)
		#print "gini1:%f, gini2:%f"%(gini1, gini2)
		self.assert_(fmath.feq(gini1,gini2))
	def test_Fund(self):
		fund = agents.Fund(None)  #usu want association w economy
		fund._accounts = [agents.FundAcct(fund, self.indivs[i], self.wealths[i]) for i in range(self.N)]
		for i in range(self.N):
			self.assertEqual(fund._accounts[i]._value, self.wealths[i])
	def test_math(self):
		print
		print fmath.get_float_radix()
		print fmath.get_machine_precision()
		print fmath.get_default_numerical_precision()
		print fmath.feq(1,2), fmath.feq(1e-9, 1e-10), fmath.feq(1e-16, 1e-17)

if __name__=="__main__":
	unittest.main()
