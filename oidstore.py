"""Abstract interface for OID Storage objects"""
__metaclass__ = type

class OIDStore:
	"""Interface for the OID Storage mechanism

	The role of this mechanism is to store and retrieve
	OID: value pairs.  Since most of the common queries
	involve finding, not a specific OID, but rather the
	next OID following a given OID, it is necessary for
	OID stores to use an ordered storage format with
	fast retrieval characteristics, such as a bisect list,
	or a BSDDB BTree database.
	"""
	def close( self ):
		"""Close the OIDStore"""
	def getExactOID( self, base ):
		"""Get the given OID,value pair for the given base

		This method is responsible for implementing the GET
		request, (or a GETBULK request which specifies
		inclusive operation).
		"""
	def nextOID( self, base ):
		"""Get next OID,value pair after given base OID

		This method is responsible for implementing GETNEXT,
		and GETBULK requests.
		"""
	def validateSetValue( self, oid, value, request, address, implementation ):
		"""Validate that given oid & value can be set

		returns 0 on success, returns errorID on failure
		
		This implementation just returns 0 in all cases
		"""
		return 0
	def setValue( self, oid, value):
		"""Set the given oid,value pair, returning old value

		This method is responsible for implementing the SET
		request.
		"""

def dumbPrefix( key, oid ):
	"""Is the key == oid or a parent of OID?

	This function is used by sub-classes to do a simple
	check for oid inheritence.
	"""
	return oid[:len(key)] == key
