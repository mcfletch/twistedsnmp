"""BSDDB BTree-based Shelve OID Storage"""
import bsddb, shelve, traceback, sys
from twistedsnmp import oidstore, errors
import struct

def oidToSortable( oid ):
	"""Convert a dotted-format OID to a sortable string"""
	return "".join([struct.pack('>I',int(i)) for i in oid.split('.') if i ])
def sortableToOID( sortable ):
	"""Convert sortable rep to a dotted-string representation"""
	result = []
	while sortable:
		(i,) = struct.unpack( '>I', sortable[:4])
		result.append( str(i) )
		sortable = sortable[4:]
	return '.%s'%( ".".join(result))


class BSDOIDStore(oidstore.OIDStore):
	"""OIDStore implemented using (on-disk) BSDDB files

	This OID store is appropriate for middle-sized OID
	tables which require persistence across Python sessions.
	
	The store uses a BSDDB BTree database provided by the
	Python optional bsddb module wrapped by the standard
	shelve module.
	"""
	def __init__( self, filename, OIDs = None ):
		"""Initialise the storage with appropriate OIDs"""
		self.btree = self.open( filename )
		self.update( OIDs )
	def __del__( self ):
		"""Close the OID store (save to disk)"""
		self.close()
	def open( self, filename, mode='c' ):
		"""Open the given shelf as a BSDDB btree shelf

		XXX patches bug in Python 2.3.x set_location for
		bsddb objects as a side-effect
		"""
		if isinstance( filename, (str,unicode)):
			filename = bsddb.btopen( filename, mode )
			if sys.version >= '2.3':
				# need to patch bug in 2.3's set_location
				# XXX need to have a < as well once fixed!
				bsddb._DBWithCursor.set_location = set_location
			filename = shelve.BsdDbShelf( filename )
		return filename
	open = classmethod( open )
	def close( self ):
		"""Close the OIDStore"""
		if self.btree:
			self.btree.close()
			self.btree = None
	def getExactOID( self, base ):
		"""Get the given OID,value pair for the given base

		This method is responsible for implementing the GET
		request, (or a GETBULK request which specifies
		inclusive operation).
		"""
		encoded = oidToSortable( base )
		if self.btree.has_key( encoded ):
			return base, self.btree[ encoded ]
		raise errors.OIDNameError( base, message="No such OID" )
	def setValue( self, oid, value):
		"""Set the given oid,value pair, returning old value

		This method is responsible for implementing the SET
		request.
		"""
		old = None
		oid = oidToSortable( oid )
		if self.btree.has_key( oid ):
			try:
				old = self.btree[ oid ]
			except KeyError:
				pass
		self.btree[ oid ] = value
		self.btree.sync()
		return old
	def nextOID( self, base ):
		"""Get next OID,value pair after given base OID

		This method is responsible for implementing GETNEXT,
		and GETBULK requests.
		"""
		try:
			encoded = oidToSortable( base )
			oid, value = self.btree.set_location(encoded)
			oid = sortableToOID( oid )
		except KeyError, err:
			raise errors.OIDNameError(
				base,
				message="OID not found in database"
			)
		if oid == base:
			try:
				oid,value = self.btree.next()
				oid = sortableToOID( oid )
			except KeyError, err:
				raise errors.OIDNameError(
					base,
					message="OID appears to be last in database"
				)
		return oid, value


def set_location(self, key):
	"""Patched version of _DBWithCursor.set_location for Python 2.3.x"""
	self._checkOpen()
	self._checkCursor()
	return self.dbc.set_range(key)
