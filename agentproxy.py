"""Client/manager side object for querying Agent via SNMPProtocol"""
from twisted.internet import defer, reactor
from twisted.python import failure
from pysnmp.proto import v2c, v1, error
from pysnmp.proto.api import generic
from twistedsnmp import datatypes, tableretriever
import traceback, socket

__metaclass__ = type

class AgentProxy:
	"""Proxy object for querying a remote agent"""
	verbose = 0
	def __init__(self, ip, port=161, community='public', snmpVersion = '1', protocol=None):
		"""Initialize the SNMPProtocol object

		ip -- ipAddress for the protocol
		port -- port for the connection
		community -- community to use for SNMP conversations
		snmpVersion -- '1' or '2', indicating the supported version
		protocol -- SNMPProtocol object to use for actual connection
		"""
		self.ip = str(ip)
		self.port = int(port or 161)
		self.community = str(community)
		self.snmpVersion, self.implementation = self.resolveVersion( snmpVersion)
		self.protocol = protocol
	def resolveVersion( self, value ):
		"""Resolve a version specifier to a canonical version and an implementation"""
		if value in ("2",'2c','v2','v2c'):
			return 'v2c', v2c
		else:
			return 'v1', v1
	def __repr__( self ):
		"""Get nice string representation of the proxy"""
		ip,port,community,snmpVersion,protocol = self.ip,self.port,self.community,self.snmpVersion,self.protocol
		className = self.__class__.__name__
		try:
			snmpVersionName = snmpVersion.__name__
		except AttributeError:
			snmpVersionName = snmpVersion
		return """%(className)s(%(ip)s,%(port)s,%(community)s,%(snmpVersionName)s,%(protocol)r)"""%locals()
	def get(self, oids, timeout=2.0, retryCount=4):
		"""Retrieve a single set of OIDs from the remote agent

		oids -- list of dotted-numeric oids to retrieve
		retryCount -- number of retries
		timeout -- initial timeout, is multipled by 1.5 on each
			timeout iteration.

		return value is a defered for an { oid : value } mapping
		for each oid in requested set

		XXX Should be raising an error if the response has an
		error message, will raise error if the connection times
		out.
		"""
		if not self.protocol:
			raise ValueError( """Expected a non-null protocol object! Got %r"""%(protocol,))
		df = defer.Deferred()
		def asDictionary( value ):
			return dict(value)
		df.addCallback( self.getResponseResults )
		df.addCallback( asDictionary )
		request = self.encode(oids, self.community)
		key = self.getRequestKey( request )
		try:
			self.send(request.encode())
		except socket.error, err:
			return defer.fail(failure.Failure())
		oids = [str(oid) for oid in oids ]
		timer = reactor.callLater(timeout, self._timeout, key, df, oids, timeout, retryCount)
		self.protocol.requests[key] = df, timer
		return df
	def set( self, oids, timeout=2.0, retryCount=4):
		"""Set a variable on our connected agent

		oids -- dictionary of oid:value pairs, or a list of
			(oid,value) tuples to be set on the agent

		raises errors if the setting fails
		"""
		if not self.protocol:
			raise ValueError( """Expected a non-null protocol object! Got %r"""%(protocol,))
		df = defer.Deferred()
		if hasattr( oids, "items"):
			oids = oids.items()
		request = self.encode(oids, self.community, set=1)
		key = self.getRequestKey( request )
		def raiseOnError( response ):
			pdu = response.apiGenGetPdu()
			if pdu.apiGenGetErrorStatus():
				raise error.ProtoError( """Set failure""", pdu.apiGenGetErrorStatus() )
			return response
		df.addCallback( raiseOnError )
		try:
			self.send(request.encode())
		except socket.error, err:
			return defer.fail(failure.Failure())
		timer = reactor.callLater(timeout, self._timeout, key, df, oids, timeout, retryCount)
		self.protocol.requests[key] = df, timer
		return df
		
	def getTable( self, roots, includeStart=0, recordCallback=None, retryCount=4, timeout= 2.0 ):
		"""Convenience method for creating and running a TableRetriever

		roots -- root OIDs to retrieve
		includeStart -- whether to include the starting OID
			in the set of results, by default, return the OID
			*after* the root oids.
			Note:  Only implemented for v1 protocols, and likely
				to be dropped eventually, as it seems somewhat
				superfluous.
		recordCallback -- called for each new record discovered
			recordCallback( root, oid, value )
		retryCount -- number of retries
		timeout -- initial timeout, is multipled by 1.5 on each
			timeout iteration.

		Will use bulk downloading when available (i.e. if
		we have implementation v2c, not v1).

		return value is a defered for a { rootOID: { oid: value } } mapping
		"""
		if self.verbose:
			print 'getTable( %(roots)r, %(includeStart)r, %(recordCallback)r,%(retryCount)r )'%locals()
		if not self.protocol:
			raise ValueError( """Expected a non-null protocol object! Got %r"""%(self.protocol,))
		roots = [str(oid) for oid in roots ]
		retriever = tableretriever.TableRetriever(
			self, roots, includeStart=includeStart,
			retryCount=retryCount, timeout= timeout,
		)
		if self.verbose:
			retriever.verbose = 1
		return retriever( recordCallback = recordCallback )
	
	def send(self, request):
		"""Send a request (string) to the network"""
		return self.protocol.send(request, (self.ip, self.port))

	## Utility methods...
	def getImplementation( self ):
		"""Get the implementation module for this request

		returns v2c or v1 pysnmp modules depending on our
		snmpVersion property.
		"""
		return self.implementation
	def getRequestKey( self, request ):
		"""Get the request key from a request/response"""
		return self.protocol.getRequestKey( request, (self.ip, self.port) )
	def encode( self, oids, community, next=0, bulk=0, set=0 ):
		"""Encode a datagram message"""
		if self.verbose:
			print 'encode( %(oids)r, %(community)r, %(next)r, %(bulk)r, %(set)r)'%locals()
		implementation = self.getImplementation()
		if bulk:
			request = implementation.GetBulkRequest()
		elif set:
			request = implementation.SetRequest()
		elif next:
			request = implementation.GetNextRequest()
		else:
			request = implementation.GetRequest()
		request.apiGenSetCommunity( community )
		pdu = request.apiGenGetPdu()
		def oidFix( value, implementation=implementation ):
			if isinstance( value, tuple ) and len(value) == 2:
				oid,value = value
				value = datatypes.typeCoerce( value, implementation )
				return oid, value
			else:
				return value, None
		variables = [oidFix(oid) for oid in oids]
		pdu.apiGenSetVarBind(variables)
		return request
	def getResponseResults( self, response ):
		"""Get [(oid,value)...] list from response

		This callback is part of the callback chain for get
		response processing.  In essence, if you have a callback
		that wants [(oid,value)...] format instead of response
		objects register this callback before the needy callback.
		"""
		if self.verbose:
			print 'getResponseResults( %(response)r )'%locals()
		if response and not response.apiGenGetPdu().apiGenGetErrorStatus():
			pdu = response.apiGenGetPdu()
			answer = pdu.apiGenGetVarBind()
			return [
				(a,b.getTerminal().get())
				for a,b in answer
				if not isinstance( b, v2c.EndOfMibView)
			]
		return []
	def _timeout(self, key, df, oids, timeout, retryCount):
		try:
			try:
				del self.protocol.requests[ key ]
			except KeyError:
				pass
			if not df.called:
				if self.verbose:
					print 'timeout', self
				if retryCount:
					timeout *= 1.5
					retryCount -= 1
					if self.verbose:
						print '    trying again', timeout, retryCount
					request = self.encode(oids, self.community)
					key = self.getRequestKey( request )
					try:
						self.send(request.encode())
					except socket.error, err:
						df.errback( failure.Failure() )
						return
					else:
						timer = reactor.callLater(
							timeout,
							self._timeout, key, df, oids, timeout, retryCount
						)
						self.protocol.requests[key] = df, timer
						return
				if self.verbose:
					print '    RAISING ERROR'
				df.errback(defer.TimeoutError('SNMP request timed out'))
		except Exception, err:
			df.errback( failure.Failure() )
		