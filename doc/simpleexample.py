from twistedsnmp import agentproxy, snmpprotocol
from twisted.internet import reactor

port = 20000
agentAddress = "localhost"
agentPort = 161
agentCommunity = "public"
snmpVersion = 'v1'
oids = ('.1.3.6.1.2.1.2.2.1.3',)

protocol = snmpprotocol.SNMPProtocol()
port = reactor.listenUDP( port, protocol )

client = agentproxy.AgentProxy(
	agentAddress, agentPort,
	community = agentCommunity,
	snmpVersion = snmpVersion,
	protocol = protocol,
)

if __name__ == "__main__":
	class Runner:
		"""Simple class to allow for running Twisted reactor serially"""
		def doUntilFinished( self, d ):
			self.response = None
			self.success = None
			d.addCallbacks( self.onSuccess, self.onFailure )
			while self.response is None:
				reactor.iterate()
		def onSuccess( self, value ):
			self.response = value
			self.success = 1
		def onFailure( self, reason ):
			self.response = reason
			self.success = 0
	df = client.getTable( oids )
	r = Runner()
	r.doUntilFinished( df )
	print r.response
	