"""Trivial example to retrieve an OID from a remote Agent"""
from twisted.internet import reactor
from twistedsnmp import snmpprotocol, agentproxy
import pprint

def main( proxy, oids ):
	"""Do a getTable on proxy for OIDs and store in oidStore"""
	oidSet = []
	while oids:
		set = tuple(oids[:2])
		if len(set) == 2:
			oidSet.append( set )
		oids = oids[2:]
	df = proxy.set(
		oidSet, timeout=.25, retryCount=5
	)
	df.addCallback( printResults )
	df.addCallback( exiter )
	df.addErrback( errorReporter )
	df.addErrback( exiter )
	return df

def printResults( result ):
	print 'Results:'
	pprint.pprint( result )
	return result

def errorReporter( err ):
	print 'ERROR', err.getTraceback()
	return err
def exiter( value ):
	reactor.stop()
	return value


if __name__ == "__main__":
	import sys, logging
	logging.basicConfig()
	# need to get the ip address
	usage = """Usage:
	simpleget ipAddress community baseoid...

ipAddress -- dotted IP address of the agent
community -- community string for the agent
baseoid -- dotted set of OIDs to retrieve from agent
"""
	if len(sys.argv) < 3:
		print usage
		sys.exit( 1 )
	ipAddress = sys.argv[1]
	# choose random port in range 25000 to 30000
	port = snmpprotocol.port()
	proxy = agentproxy.AgentProxy(
		ipAddress, 161,
		community = sys.argv[2],
		snmpVersion = 'v2',
		protocol = port.protocol,
	)
	if not sys.argv[3:]:
		oids = [
			'.1.3.6.1.2.1.1.1.0', 'New Description',
			'.1.3.6.1.2.1.1.3.0', '11111111',
		]
	else:
		oids = sys.argv[3:]
	reactor.callWhenRunning( main, proxy, oids )
	reactor.run()
