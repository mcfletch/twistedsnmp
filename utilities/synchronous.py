from twisted.internet import reactor, defer

__metaclass__ = type
class Holder:
	"""Class allowing synchronous calling of deferred functions"""
	success = 0
	finished = 0
	timeout = 0
	result = None
	def __init__( self, callable, *arguments, **named ):
		self.callable = callable
		self.arguments = arguments
		self.named = named
	def __call__( self, timeout=None ):
		"""Call the held callable, timeout after timeout seconds"""
		print 'call'
		df = self.callable( *self.arguments, **self.named )
		df.addCallback( self.OnSuccess )
		df.addErrback( self.OnFailure )
		if timeout:
			reactor.callLater( timeout, self.OnTimeout )
		return df
	def OnTimeout( self ):
		"""On a timeout condition, raise an error"""
		print 'OnTimeout'
		if not self.finished:
			self.finished = 1
			self.result = defer.TimeoutError('SNMP request timed out')
			self.success = 0
		reactor.stop()
	def OnSuccess( self, result ):
		print 'OnSuccess'
		if not self.finished:
			self.finished = 1
			self.result = result
			self.success = 1
		reactor.stop()
	def OnFailure( self, errorMessage ):
		print 'OnFailure'
		if not self.finished:
			self.finished = 1
			self.result = errorMessage
			self.success = 0
		reactor.stop()
	def doUntilFinish( self ):
		"""Given a defered, add our callbacks and iterated until completed"""
		while not self.finished:
			reactor.iterate()

def synchronous( timeout, callable, *arguments, **named ):
	"""Call callable in twisted

	timeout -- timeout in seconds, specify 0 or None to disable
	callable -- defer-returning callable object
	arguments, named -- passed to callable within reactor

	returns (success, result/error)
	"""
	holder = Holder( callable, *arguments, **named )
	reactor.callLater(
		0.0000005,
		holder,
		timeout,
	)
	holder.doUntilFinish( )
	return holder.success, holder.result

if __name__ == "__main__":
	import sys
	if not sys.argv[1:]:
		print """For testing run:
	synchronous server
or
	synchronous client
from the command line."""
		sys.exit( 1 )
		
	if sys.argv[1] == 'server':
		# just setup something to serve a response
		from twistedsnmp import agent, agentprotocol, bisectoidstore
		from pysnmp.proto import v2c, v1, error
		agentObject = reactor.listenUDP(
			20161, agentprotocol.AgentProtocol(
				snmpVersion = 'v1',
				agent = agent.Agent(
					dataStore = bisectoidstore.BisectOIDStore(
						OIDs = [
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
					),
				),
			),
		)
		print 'Starting listening agent'
		reactor.run()
	else:
		from twistedsnmp import agentproxy, snmpprotocol
		port = reactor.listenUDP(
			20000, snmpprotocol.SNMPProtocol(),
		)
		proxy = agentproxy.AgentProxy(
			ip = '127.0.0.1',
			community = 'public',
			protocol = port.protocol,
			port = 20161,
		)
		print synchronous( 0, proxy.get, ('.1.3.6.1.2.1.1.2.0',) )
		