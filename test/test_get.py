from __future__ import nested_scopes
from twisted.internet import reactor
import unittest
from twistedsnmp import agent, agentprotocol
from twistedsnmp import snmpprotocol, massretriever
from twistedsnmp.test import basetestcase
from pysnmp.proto import v2c, v1, error

class GetRetrieverV1( basetestcase.BaseTestCase ):
	version = 'v1'
	oidsForTesting = [
		('.1.3.6.1.2.1.1.1.0', 'Hello world!'),
		('.1.3.6.1.2.1.1.2.0', 32),
		('.1.3.6.1.2.1.1.3.0', v1.IpAddress('127.0.0.1')),
		('.1.3.6.1.2.1.1.4.0', v1.OctetString('From Octet String')),
		('.1.3.6.1.2.1.2.1.0', 'Hello world!'),
		('.1.3.6.1.2.1.2.2.0', 32),
		('.1.3.6.1.2.1.2.3.0', v1.IpAddress('127.0.0.1')),
		('.1.3.6.1.2.1.2.4.0', v1.OctetString('From Octet String')),
		('.1.3.6.2.1.0', 'Hello world!'),
		('.1.3.6.2.2.0', 32),
		('.1.3.6.2.3.0', v1.IpAddress('127.0.0.1')),
		('.1.3.6.2.4.0', v1.OctetString('From Octet String')),
	]
	def test_simpleGet( self ):
		"""Can retrieve a single simple value?"""
		d = self.client.get( [
			'.1.3.6.1.2.1.1.1.0',
		] )
		self.doUntilFinish( d )

		assert self.success, self.response
		assert isinstance( self.response, dict ), self.response
		assert self.response.has_key( '.1.3.6.1.2.1.1.1.0' ), self.response
		assert self.response['.1.3.6.1.2.1.1.1.0' ] == 'Hello world!', self.response

	def test_tableGet( self ):
		"""Can retrieve a tabular value?"""
		d = self.client.getTable( [
			'.1.3.6.1.2.1.1'
		] )
		self.doUntilFinish( d )

		assert self.success, self.response
		assert isinstance( self.response, dict ), self.response
		assert self.response.has_key( '.1.3.6.1.2.1.1' ), (self.response,self)
		tableData = self.response['.1.3.6.1.2.1.1' ]
		assert isinstance(tableData, dict)
		assert tableData.has_key('.1.3.6.1.2.1.1.1.0'), tableData

	def test_tableGetMissing( self ):
		"""Does tabular retrieval ignore non-existent oid-sets?"""
		d = self.client.getTable( [
			'.1.3.6.1.2.1.5'
		] )
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == {}, self.response

	def test_tableGetAll( self ):
		"""Does tabular retrieval work specifying a distant parent (e.g. .1.3.6)?"""
		d = self.client.getTable( [
			'.1.3.6'
		] )
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == {'.1.3.6':dict( self.oidsForTesting )}, self.response
	def test_multiTableGet( self ):
		oids = [
			'.1.3.6.1.2.1.1',
			'.1.3.6.1.2.1.2',
			'.1.3.6.2',
		]
		d = self.client.getTable( oids )
		self.doUntilFinish( d )
		for oid in oids:
			assert self.response.has_key( oid )
	def test_multiTableGetBad( self ):
		oids = [
			'.1.3.6.1.2.1.1',
			'.1.3.6.1.2.1.2',
			'.1.3.6.2',
			'.1.3.6.3',
		]
		d = self.client.getTable( oids )
		self.doUntilFinish( d )
		for oid in oids[:-1]:
			assert self.response.has_key( oid )
		assert not self.response.has_key( oids[-1] ), self.response
		
		

class GetRetrieverV2C( GetRetrieverV1 ):
	version = 'v2c'
	def test_tableGetAllBulk( self ):
		"""Does tabular retrieval do only a single query?"""
		def send(request, client= self.client):
			"""Send a request (string) to the network"""
			client.messageCount += 1
			client.protocol.send(request, (client.ip,client.port))
		self.client.messageCount = 0
		self.client.send = send
		d = self.client.getTable( [
			'.1.3.6'
		] )
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.client.messageCount == 1, """Took %s messages to retrieve with bulk table, should only take 1"""%( self.client.messageCount ,)

if basetestcase.bsdoidstore:
	class GetRetrieverV1BSD( basetestcase.BSDBase, GetRetrieverV1 ):
		pass
	class GetRetrieverV2CBSD( basetestcase.BSDBase, GetRetrieverV2C ):
		pass

class MassRetrieverTest( basetestcase.BaseTestCase ):
	"""Test for mass retrieval of values"""
	version = 'v2'
	oidsForTesting = [
		('.1.3.6.1.1.3',       'Blah!'),
		('.1.3.6.1.2.1.1.1.0', 'Hello world!'),
		('.1.3.6.1.2.1.1.2.0', 32),
		('.1.3.6.1.2.1.1.3.0', v1.IpAddress('127.0.0.1')),
		('.1.3.6.1.2.1.1.4.0', v1.OctetString('From Octet String')),
	]
	def testMassRetriever( self ):
		"""Can we retrieve mass value single-oid values?"""
		proxies = massretriever.proxies(
			self.client.protocol,
			[('127.0.0.1',self.agent.port, 'public',self.version)]*250
		)
		retriever = massretriever.MassRetriever(
			proxies
		)
		retriever.verbose = 1
		d = retriever( oids = ['.1.3.6.1.1.3',] )
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == {('127.0.0.1',self.agent.port): {'.1.3.6.1.1.3':'Blah!'}}, self.response
		retriever.printStats()
	def testMassRetrieverTables( self ):
		"""Can we retrieve mass value tabular sets?"""
		import random
		GOOD_COUNT = 500
		BAD_COUNT = 500
		proxies = massretriever.proxies(
			self.client.protocol,
			[
				('127.0.0.1',self.agent.port, 'public',self.version)
			]* GOOD_COUNT + [
				('127.0.0.1',self.agent.port+10000, 'public',self.version)
			] * BAD_COUNT
		)
		random.shuffle( proxies )
		random.shuffle( proxies )
		random.shuffle( proxies )
		retriever = massretriever.MassRetriever(
			proxies
		)
		retriever.verbose = 1
		d = retriever(
			tables = ['.1.3.6.1.2.1',]
		)
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == {
			('127.0.0.1', self.agent.port): {
				'.1.3.6.1.2.1':{
					'.1.3.6.1.2.1.1.1.0': 'Hello world!',
					'.1.3.6.1.2.1.1.2.0': 32,
					'.1.3.6.1.2.1.1.3.0': '127.0.0.1',
					'.1.3.6.1.2.1.1.4.0': 'From Octet String',
				}
			},
			('127.0.0.1', self.agent.port+10000): {
				'.1.3.6.1.2.1':None,
			},
		}, self.response
		retriever.printStats()
		assert retriever.successCount == GOOD_COUNT, """Expected %s valid responses, got %s"""%(GOOD_COUNT, retriever.successCount )
		assert retriever.errorCount == BAD_COUNT, """Expected %s valid responses, got %s"""%(GOOD_COUNT, retriever.successCount )
		

if __name__ == "__main__":
	unittest.main()