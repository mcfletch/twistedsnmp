from __future__ import nested_scopes
from twisted.internet import reactor
import unittest
from twistedsnmp.test import basetestcase
from twistedsnmp import tableretriever, agentproxy
from twistedsnmp.pysnmpproto import v2c,v1, error

class BasicProxyTests( basetestcase.BaseTestCase ):
	version = 'v2c'
	def testBulkRequestCreate( self ):
		"""Test that we can create bulk requests"""
		request = self.client.encode(
			[
				'.1.3.6'
			],
			self.client.community,
			next= True,
			bulk = True,
			maxRepetitions = 256,
		)
class TableRetrieverTests( basetestcase.BaseTestCase ):
	version = 'v2c'
	def testCreation( self ):
		self.installMessageCounter()
		tr = tableretriever.TableRetriever(
			self.client,
			['.1.3.6'],
		)
	



if __name__ == "__main__":
	unittest.main()
	
