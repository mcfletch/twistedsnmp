"""Helper object for the AgentProxy object"""
from twisted.internet import defer, protocol, reactor
from pysnmp.proto import v2c, v1, error
from pysnmp.proto.api import generic
import traceback

class TableRetriever( object ):
	"""Object for retrieving an entire table from an SNMP agent

	This is the (loose) equivalent of the SNMPWalk examples in
	pysnmp.  It also includes the code for the SNMPBulkWalk, which
	is a generalisation of the SNMPWalk code.
	"""
	# By default, we always try to use bulk retrieval, as
	# it's so much faster if it's available.  Set to 0 to always
	# use iterative retrieval even on v2c ports.
	bulk = 1
	finished = 0
	def __init__( self, proxy, roots, includeStart=0, retryCount=4, timeout= 2.0 ):
		"""Initialise the retriever

		proxy -- the AgentProxy instance we want to use for
			retrieval of the data
		roots -- root OIDs to retrieve
		includeStart -- whether to include the starting OID
			in the set of results, by default, return the OID
			*after* the root oids
		retryCount -- number of retries
		timeout -- initial timeout, is multipled by 1.5 on each
			timeout iteration.
		"""
		self.proxy = proxy
		self.roots = roots
		self.includeStart = includeStart
		self.retryCount = retryCount
		self.timeout = timeout
		self.values = {} # {rootOID: {OID: value}} mapping
	def __call__( self, recordCallback=None ):
		"""Collect results, call recordCallback for each retrieved record

		recordCallback -- called for each new record discovered

		Will use bulk downloading when available (i.e. if
		we have implementation v2c, not v1) and self.bulk is true.

		return value is a defered for a { rootOID: { oid: value } } mapping
		"""
		self.recordCallback = recordCallback
		self.df = defer.Deferred()
		self.getTable( includeStart= self.includeStart)
		return self.df
	def integrateNewRecord( self, oidValues, rootOIDs ):
		"""Integrate a record-set into the table"""
		OID = self.proxy.getImplementation().ObjectIdentifier
		while oidValues:
			oidSet = oidValues[:len(rootOIDs)]
			del oidValues[:len(rootOIDs)]
			for (root,(key,value)) in zip(rootOIDs, oidSet):
				# we haven't yet filtered this copy of the oidValues,
				# so need to filter to make sure we haven't gone beyond
				# the end of the root values
				
				# XXX See note in areWeDone regarding problem with
				# having a single root no longer continuing, likely
				# indexing problems eventually
##				print 'root', root
##				print 'key', key
##				print 'value', value
				if OID(str(root)).isaprefix(str(key)) and not isinstance(value, v2c.EndOfMibView):
					table = self.values.setdefault(root,{})
					if not table.has_key(key):
						table[key] = value
						if self.recordCallback is not None and callable(self.recordCallback):
							self.recordCallback( root, key, value )
		if self.finished and self.finished < 2:
			self.finished = 2
			if not self.df.called:
				self.df.callback( self.values )
				
	def getTable( self, oids=None, roots=None, includeStart=0, retryCount=None, delay=None):
		"""Retrieve all sub-oids from these roots

		recordCallback -- called for *each* OID:value pair retrieved
			recordCallback( root, oid, value )
		includeStart -- at the moment, only implemented for v1 protocols,
			ignored for v2c.  Should likely be avoided entirely.  Would
			be implemented with a seperate get call anyway, which may as
			well be explicitly coded when you want it.

		This is the "walk" example from pysnmp re-cast...
		"""
		if retryCount is None:
			retryCount = self.retryCount
		if delay is None:
			delay = self.timeout
		if oids is None:
			oids = self.roots
		if roots is None:
			roots = self.roots
		df = defer.Deferred()
		request = self.proxy.encode(
			oids,
			self.proxy.community,
			next= not includeStart,
			bulk = (self.bulk and self.proxy.getImplementation() is v2c),
		)

		roots = roots[:]

		df.addCallback( self.areWeDone, roots=roots, request=request )
		df.addCallback( self.proxy.getResponseResults )
		df.addCallback( self.integrateNewRecord, rootOIDs = roots[:] )

		self.proxy.send(request.encode())

		key = self.proxy.getRequestKey( request )

		timer = reactor.callLater(
			self.timeout,
			self.tableTimeout,
			df, key, oids, roots, includeStart, retryCount-1, delay
		)
		self.proxy.protocol.requests[key] = df, timer

		return df
	def tableTimeout( self, df, key, oids, roots, includeStart, retryCount, delay ):
		"""Table timeout implementation

		Table queries timeout if a single retrieval
		takes longer than retryCount * self.timeout
		"""
		if not df.called:
			try:
				if retryCount > 0:
					try:
						if self.proxy.protocol.requests[key] is df:
							del self.proxy.protocol.requests[ key ]
					except KeyError:
						pass
					return self.getTable( oids, roots, includeStart, retryCount-1, delay*1.5 )
				try:
					if not self.finished:
						self.df.errback( defer.TimeoutError('SNMP request timed out'))
				except defer.AlreadyCalledError:
					pass
			except Exception, err:
				if not self.df.called:
					self.df.errback( err )
				else:
					traceback.print_exc()
	def areWeDone( self, response, roots, request, recordCallback=None ):
		"""Callback which checks to see if we're done

		if not, passes on request & schedules next iteration
		if so, returns None
		"""
		newOIDs = response.apiGenGetPdu().apiGenGetVarBind()
		if response.apiGenGetPdu().apiGenGetErrorStatus():
			errorIndex = response.apiGenGetPdu().apiGenGetErrorIndex() - 1
			# SNMP agent (v.1) reports 'no such name' when walk is over
			repeatingRoots = roots[:]
			if response.apiGenGetPdu().apiGenGetErrorStatus() == 2:
				# One of the tables exceeded
				for l in newOIDs, repeatingRoots:
					if errorIndex < len(l):
						del l[errorIndex]
					else:
						raise error.ProtoError('Bad ErrorIndex %s vs length of queried items in VarBind in %s' %( errorIndex, response))
				# okay, now newOIDs is just the set of old OIDs with the
				# exhausted ones removed...
			else:
				errorStatus = str(response['pdu'].values()[0]['error_status'])
				if errorIndex < len(newOIDs):
					raise error.ProtoError(errorStatus + ' at ' + \
										   str(newOIDs[errorIndex][0]))
				raise error.ProtoError(errorStatus)
		else:
			# The following is taken from RFC1905 (fixed not to depend on repetitions)
			# N should be retrieved from the response, the non-repeating set
			# XXX Note, that there seems to be a problem with this
			# algorithm, it assumes that the repeating OID-set remains
			# of constant-size.  AFAICS the spec says it should reduce
			# as each table ends, which makes sense, as you want the remainder
			# of the OIDs to only be those which are still valid at the end
			# of the iteration.

			if isinstance( request, v2c.GetBulkRequest ):
				N = request.apiGenGetPdu().apiGenGetNonRepeaters()
			else:
				N = 0
			assert N == 0, """Not yet sure that non-repeaters are handled correctly!"""
			# R is the number of repeating OIDs
			R = len(roots) - N
			# M is the number of repetitions...
			if R:
				M = len(newOIDs) / R
			else:
				M = 0
			# Leave the last instance of each requested repeating OID
			newOIDs = newOIDs[-R:]

			# Exclude completed var-binds
			repeatingRoots = roots[-R:]
			for idx in range(R):
				try:
					root = self.proxy.getImplementation().ObjectIdentifier(repeatingRoots[idx])
					if (
						not root.isaprefix(newOIDs[idx][0]) or
						isinstance(newOIDs[idx][1], v2c.EndOfMibView)
					):
						# One of the tables exceeded
						for l in newOIDs, repeatingRoots:
							del l[idx]
						break # XXX check logic here, can't more than one end at the same time?
				except IndexError, err:
					raise error.ProtoError( """Incorrectly formed table response: %s : %s"""%(newOIDs,err))

		# Decide whether to request next item...
		if newOIDs and repeatingRoots: # still something to do...
			nextIteration = reactor.callLater(
				0.0,
				self.getTable,
				[x[0] for x in newOIDs],
				roots=repeatingRoots,
				includeStart=0,
			)
		else:
			# actually, this should wait for this last record
			# to get updated before it does the callback :(
			self.finished = 1
		# XXX should return newOIDs with the bad results filtered out
		return response
