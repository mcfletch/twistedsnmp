"""SNMP Logic for Agent(Server)-side implementations"""
from __future__ import generators
import weakref
from twistedsnmp import datatypes
from pysnmp.proto import v2c, v1, error

__metaclass__ = type

noError = 0
tooBig = 1 # Response message would have been too large
noSuchName = 2 #There is no such variable name in this MIB
badValue = 3 # The value given has the wrong type or length

try:
	enumerate
except NameError:
	def enumerate( seq ):
		i = 0
		for x in seq:
			yield i,x
			i += 1

class Agent:
	"""Implementation of SNMP Logic for Agent-side implementations

	This base-class is intended to interact with objects providing
	an OID-store interface.  It's primary purpose is to implement
	the iteration control mechanisms for querying that store.
	"""
	def __init__(self, dataStore, protocol=None):
		"""Initialise the MockAgent with OID list"""
		self.dataStore = dataStore
		if protocol is not None:
			self.setProtocol( protocol )
			protocol.setAgent( self )
	def setProtocol( self, protocol ):
		"""Set the protocol for the agent object"""
		self.protocol = protocol
	def get( self, request, address, implementation ):
		"""Get OID(s) for the request and return response

		request -- parsed (i.e. object-form) GET request
		address -- (ip,port) Internet address from which the
			request was received.
		implementation -- implementation module for the request,
			i.e. the v2c or v1 module

		sends response to the client as a side effect
		
		returns the sent response
		"""
		variables = request.apiGenGetPdu().apiGenGetVarBind()
		result = []
		for key,_ in variables:
			try:
				result.append( self.dataStore.getExactOID( key ) )
			except (IndexError,KeyError):
				# do error reporting here
				pass
		response = request.reply()
		pdu = response.apiGenGetPdu()
		pdu.apiGenSetVarBind([
			(key,datatypes.typeCoerce(value,implementation))
			for (key,value) in result
		])
		self.protocol.send( response.encode(), address )
		return response
	def getNext( self, request, address, implementation ):
		"""Respond to an iterative get-next request

		request -- parsed (i.e. object-form) GETNEXT request
		address -- (ip,port) Internet address from which the
			request was received.
		implementation -- implementation module for the request,
			i.e. the v2c or v1 module

		sends response to the client as a side effect
		
		returns the sent response

		XXX Doesn't currently check for message too long error
			condition

		(1)  If, for any object name in the variable-bindings field,
			that name does not lexicographically precede the name of
			some object available for get operations in the relevant
			MIB view, then the receiving entity sends to the
			originator of the received message the GetResponse-PDU of
			identical form, except that the value of the error-status
			field is noSuchName, and the value of the error-index
			field is the index of said object name component in the
			received message.

		(2)  If the size of the GetResponse-PDU generated as described
			below would exceed a local limitation, then the receiving
			entity sends to the originator of the received message
			the GetResponse-PDU of identical form, except that the
			value of the error-status field is tooBig, and the value
			of the error-index field is zero.

		(3)  If, for any object named in the variable-bindings field,
			the value of the lexicographical successor to the named
			object cannot be retrieved for reasons not covered by any
			of the foregoing rules, then the receiving entity sends
			to the originator of the received message the
			GetResponse-PDU of identical form, except that the value
			of the error-status field is genErr and the value of the
			error-index field is the index of said object name
			component in the received message.

		If none of the foregoing rules apply, then the receiving protocol
		entity sends to the originator of the received message the
		GetResponse-PDU such that, for each name in the variable-bindings
		field of the received message, the corresponding component of the

		GetResponse-PDU represents the name and value of that object whose
		name is, in the lexicographical ordering of the names of all objects
		available for get operations in the relevant MIB view, together with
		the value of the name field of the given component, the immediate
		successor to that value.  The value of the error-status field of the
		GetResponse-PDU is noError and the value of the errorindex field is
		zero.  The value of the request-id field of the GetResponse-PDU is
		that of the received message.

		http://www.faqs.org/rfcs/rfc1157.html
		Section: 4.1.3, GetNextRequest
		"""
		variables = request.apiGenGetPdu().apiGenGetVarBind()
		result = []
		errorCode = None
		errorIndex = None
		for index, (base,_) in enumerate(variables):
			try:
				result.append( self.dataStore.nextOID( base ))
			except NameError, err:
				errorCode = noSuchName
				errorIndex = index
				break
		response = request.reply()
		pdu = response.apiGenGetPdu()
		if errorCode:
			pdu.apiGenSetErrorStatus( errorCode )
			pdu.apiGenSetErrorIndex( errorIndex + 1 ) # 1-indexed
			pdu.apiGenSetVarBind(variables)
		else:
			pdu.apiGenSetVarBind([
				(key,datatypes.typeCoerce(value,implementation))
				for (key,value) in result
			])
		self.protocol.send( response.encode(), address )
		return response

	def getTable( self, request, address, implementation ):
		"""Respond to an all-at-once (v2) get request

		request -- parsed (i.e. object-form) GETBULK request
		address -- (ip,port) Internet address from which the
			request was received.
		implementation -- implementation module for the request,
			i.e. the v2c or v1 module

		sends response to the client as a side effect
		
		returns the sent response

		The get-bulk request has two elements, a set of non-repeating
		get-next OIDs (normally 0), and a set of repeating get-bulk
		OIDs.  Up to a specified number of ordered elements starting
		at the specified OIDs are returned for each of the bulk elements,
		with truncation of the entire set occuring if all tables are
		exhausted (reach the end of the OID tables), otherwise will
		include subsequent table values sufficient to fill in the
		message-size.

		http://www.faqs.org/rfcs/rfc1448.html
		Section 4.2.3, The GetBulkRequest-PDU
		"""
		from twistedsnmp import datatypes
		variables = request.apiGenGetPdu().apiGenGetVarBind()
		result = []
		errorCode = None
		errorIndex = None
		# Get the repetition counts...
		# if < 0, set to 0, though for maxRepetitions we set to 255 since
		# that's the default and 0 would mean no repetitions at all
		# nonRepeaters is the set of OIDs which are treated as get-next
		# requests, while the rest of the query OIDs are get-bulk, repeating
		# up to maxRepetitions times.
		nonRepeaters = max((request.apiGenGetPdu().apiGenGetNonRepeaters(),0))
		maxRepetitions = max((request.apiGenGetPdu().apiGenGetMaxRepetitions(),0)) or 255
		# Known as M, N and R in the spec...
		nextIter = []
		for index, (base,_) in enumerate(variables[:nonRepeaters]):
			try:
				oid,value = self.dataStore.nextOID( base )
			except NameError, err:
				oid = oid
				value = v2c.EndOfMibView()
			result.append( (oid,value) )
		nextIter = variables[nonRepeaters:]
		for repeat in range(maxRepetitions):
			variables = nextIter
			nextIter = []
			foundGood = 0
			for index, (base,_) in enumerate(variables):
				try:
					oid,value = self.dataStore.nextOID( base )
					nextIter.append( (oid,value) )
					foundGood = 1
				except NameError, err:
					oid = base
					value = v2c.EndOfMibView()
				result.append( (oid,value) )
			if not foundGood:
				break # just to save processing
		response = request.reply()
		pdu = response.apiGenGetPdu()
		if errorCode:
			pdu.apiGenSetErrorStatus( errorCode )
			pdu.apiGenSetErrorIndex( errorIndex + 1 ) # 1-indexed
			pdu.apiGenSetVarBind(variables)
		else:
			pdu.apiGenSetVarBind([
				(key,datatypes.typeCoerce(value,implementation))
				for (key,value) in result
			])
		self.protocol.send( response.encode(), address )
	def set( self, request, address, implementation ):
		"""Set OIDs as given by request

		request -- parsed (i.e. object-form) SET request
		address -- (ip,port) Internet address from which the
			request was received.
		implementation -- implementation module for the request,
			i.e. the v2c or v1 module

		XXX Spec requires a two-stage (or more) commit sequence with
		undo on failure even including the commit itself.  Not
		implemented.
		"""
		errorCode = 0
		errorIndex = 0
		variables = request.apiGenGetPdu().apiGenGetVarBind()
		for index, (oid,value) in enumerate(variables):
			errorCode = self.dataStore.validateSetValue( oid, value, request, address, implementation )
			if errorCode:
				errorIndex = index
				break
		response = request.reply()
		pdu = response.apiGenGetPdu()
		if errorCode:
			pdu.apiGenSetErrorStatus( errorCode )
			pdu.apiGenSetErrorIndex( errorIndex + 1 ) # 1-indexed
			pdu.apiGenSetVarBind(variables)
			return self.protocol.send( response.encode(), address )
		for index, (oid,value) in enumerate(variables):
			self.dataStore.setValue( oid, value  )
		response = request.reply()
		pdu.apiGenSetVarBind(variables)
		return self.protocol.send( response.encode(), address )
