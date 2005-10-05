"""Simple example of an Agent for testing"""
import time
from twisted.internet import reactor
from twisted.internet import error as twisted_error
from twistedsnmp import agent, agentprotocol, bisectoidstore
try:
	from twistedsnmp import bsdoidstore
except ImportError:
	import warnings
	warnings.warn( """No BSDDB OID Storage available for testing""" )
	bsdoidstore = None

def createAgent( oids ):
	ports = [161]+range(20000,25000)
	for port in ports:
		try:
			agentObject = reactor.listenUDP(
				port, agentprotocol.AgentProtocol(
					snmpVersion = 'v2c',
					agent = agent.Agent(
						dataStore = bisectoidstore.BisectOIDStore(
							OIDs = oids,
						),
					),
				),
			)
		except twisted_error.CannotListenError:
			pass
		else:
			return agentObject, port

startTime = time.time()
def sysUpTime( oid, storage ):
	"""Determine uptime for our service in time-ticks"""
	seconds = time.time()-startTime
	return int(round(seconds * 100,0))

testingOIDs = {
	'.1.3.6.1.2.1.1.1.0': 'Some tool out in the field',
	'.1.3.6.1.2.1.1.2.0': '.1.3.6.1.4.1.88.3.1',
	'.1.3.6.1.2.1.1.3.0':  sysUpTime,
	'.1.3.6.1.2.1.1.4.0': "support@somewhere.ca",
	'.1.3.6.1.2.1.1.5.0': "NameOfSystem",
	'.1.3.6.1.2.1.1.6.0': "SomeHeadEnd, West Hinterlands, Canada",
}

def main(oids=testingOIDs):
	agent, port = createAgent( oids )
	print 'Listening on port', port

if __name__ == "__main__":
	reactor.callWhenRunning( main )
	reactor.run()

