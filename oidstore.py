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

	def update( self, valueSet ):
		"""Given a valueSet, load given values into storage

		valueSet -- A set of OID:value mappings in these forms
			[ (oid,value) ] # value can also be a dictionary of oid:value mappings
			{ rootOID : { oid : value }}

		XXX Should allow for passing in another OIDStore, but that
			Will require a first() method for all OIDStores
		"""
		if hasattr( valueSet, 'items' ):
			return self.update( valueSet.items())
		if not valueSet:
			return 0
		# okay, now should be list of tuples
		count = 0
		for key, value in valueSet:
			if isinstance( value, dict ):
				count += self.update( value.items())
			else:
				count += 1
				self.setValue( key, value )
		return count

def dumbPrefix( key, oid ):
	"""Is the key == oid or a parent of OID?

	This function is used by sub-classes to do a simple
	check for oid inheritence.
	"""
	return oid[:len(key)] == key
