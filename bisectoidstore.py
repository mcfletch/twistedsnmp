"""In-memory OIDStore based on the standard bisect module"""
from __future__ import generators
import bisect
from twistedsnmp import agent, oidstore
from pysnmp.proto import v2c, v1, error

noError = 0
tooBig = 1 # Response message would have been too large
noSuchName = 2 #There is no such variable name in this MIB
badValue = 3 # The value given has the wrong type or length

try:
	enumerate
except NameError:
	def enumerate( seq ):
		"""Enumerate stand-in for Python 2.2.x"""
		i = 0
		for x in seq:
			yield i,x
			i += 1

class BisectOIDStore(oidstore.OIDStore):
	"""In-memory OIDStore based on the standard bisect module

	This OID store is for use primarily in testing situations,
	where a small OID set is to be loaded and tested against.

	It should be available on any Python installation.
	"""
	def __init__( self, OIDs=None ):
		"""Initialise the storage with appropriate OIDs"""
		self.OIDs = OIDs or []
	def getExactOID( self, base ):
		"""Get the given OID,value pair for the given base

		This method is responsible for implementing the GET
		request, (or a GETBULK request which specifies
		inclusive operation).
		"""
		start = bisect.bisect( self.OIDs, (base,) )
		try:
			return (base, self.OIDs[start][1])
		except (IndexError,KeyError):
			# do error reporting here
			pass
	def setValue( self, oid, value):
		"""Set the given oid,value pair, returning old value

		This method is responsible for implementing the SET
		request.
		"""
		start = bisect.bisect( self.OIDs, (oid,) )
		if start < len(self.OIDs):
			oldOID, oldValue = self.OIDs[ start ]
			if oldOID == oid:
				self.OIDs[start] = (oid,value)
				return oldValue
			else:
				self.OIDs.insert( start, (oid,value))
		else:
			self.OIDs.append( (oid,value))
		return None
	def nextOID( self, base ):
		"""Get next OID,value pair after given base OID

		This method is responsible for implementing GETNEXT,
		and GETBULK requests.
		"""
		start = bisect.bisect( self.OIDs, (base,) )
		if start < len( self.OIDs ):
			# require for all OIDs that they precisely match
			# an OID in the OID set we publish...
			oid,value = self.OIDs[start]
			if oid != base and not oidstore.dumbPrefix( base, oid ):
				raise NameError( """OID %r does not exist in the agent space""" )
			elif oid != base and oidstore.dumbPrefix( base, oid ):
				# if the found OID is prefixed by key, we want to return this OID
				# otherwise we want to return the *next* item
				pass
			else:
				# otherwise return the item *after* the found OID (exact match)
				start += 1
			# now get the real value...
			if start < len(self.OIDs ):
				return self.OIDs[start]
			else:
				# overflow error, reached end of our OID table with this OID
				raise NameError( """OID is beyond end of table""" )
		else:
			# starting OID is beyond end of table
			raise NameError( """OID is beyond end of table""" )
