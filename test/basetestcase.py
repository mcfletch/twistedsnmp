from twisted.internet import reactor
from twisted.internet import error as twisted_error
import unittest
from twistedsnmp import agent, agentprotocol, bisectoidstore
from twistedsnmp import snmpprotocol, agentproxy
from pysnmp.proto import v2c, v1, error
try:
	from twistedsnmp import bsdoidstore
except ImportError:
	import warnings
	warnings.warn( """No BSDDB OID Storage available for testing""" )
	bsdoidstore = None

class BaseTestCase( unittest.TestCase ):
	version = 'v1'
	oidsForTesting = [
	]
	def setUp( self ):
		"""Set up the agent to query as self.agent"""
		ports = [161]+range(20000,25000)
		self.response = None
		self.success = None
		for port in ports:
			try:
				self.agent = reactor.listenUDP(
					port, agentprotocol.AgentProtocol(
						snmpVersion = self.version,
						agent = agent.Agent(
							dataStore = self.createStorage(),
						),
					),
				)
			except twisted_error.CannotListenError:
				pass
			else:
				self.clientPort = self.createClientPort()
				self.client = agentproxy.AgentProxy(
					"127.0.0.1", port,
					community = "public",
					snmpVersion = self.version,
					protocol = self.clientPort.protocol,
				)
				return
		raise twisted_error.CannotListenError(
			"""Could not listen on *any* port in our (large) range of potential ports for agent!""",
		)
	def createClientPort( self ):
		for port in range(25000,30000):
			try:
				return reactor.listenUDP(
					port, snmpprotocol.SNMPProtocol(),
				)
			except twisted_error.CannotListenError:
				pass
		raise twisted_error.CannotListenError(
			"""Could not listen on *any* port in our (large) range of potential ports for client!""",
		)
	def doUntilFinish( self, d ):
		"""Given a defered, add our callbacks and iterated until completed"""
		self.response = None
		self.success = None
		d.addCallbacks( self.onSuccess, self.onFailure )
		while self.response is None:
			reactor.iterate()
	def createStorage( self ):
		return bisectoidstore.BisectOIDStore(
			OIDs = self.oidsForTesting,
		)
	def onSuccess( self, value ):
		self.response = value
		self.success = 1
	def onFailure( self, reason ):
		self.response = reason
		self.success = 0

	def tearDown( self ):
		"""Tear down our testing framework"""
		self.agent.stopListening()
		self.clientPort.stopListening()
		reactor.iterate()

if bsdoidstore:
	class BSDBase:
		def createStorage( self ):
			return bsdoidstore.BSDOIDStore(
				bsdoidstore.BSDOIDStore.open( 'temp.bsd', 'n'),
				OIDs = self.oidsForTesting,
			)
