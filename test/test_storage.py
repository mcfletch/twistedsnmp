from twistedsnmp import bisectoidstore, agent
import unittest
from pysnmp.proto import v2c, v1, error
try:
	from twistedsnmp import bsdoidstore
except ImportError:
	bsdoidstore = None
if not hasattr( bsdoidstore, 'BSDOIDStore' ):
	# some weird bug is creating the module even though
	# it's failing with an ImportError :(
	bsdoidstore = None

class StorageTest( unittest.TestCase ):
	def createStorage( self, oids ):
		return bisectoidstore.BisectOIDStore(
			OIDs = oids,
		)
	def testExact( self ):
		store = self.createStorage(
			[
				('.1.3.6.1.2.1.1.1.0', 'Hello world!'),
				('.1.3.6.1.2.1.1.2.0', 32),
				('.1.3.6.1.2.1.1.3.0', v1.IpAddress('127.0.0.1')),
				('.1.3.6.1.2.1.1.4.0', v1.OctetString('From Octet String')),
			]
		)
		result = store.getExactOID( '.1.3.6.1.2.1.1.1.0' )
		assert result[0] == '.1.3.6.1.2.1.1.1.0', result
		assert result[1] == 'Hello world!', result
	def testNext( self ):
		store = self.createStorage(
			[
				('.1.3.6.1.2.1.1.1.0', 'Hello world!'),
				('.1.3.6.1.2.1.1.2.0', 32),
				('.1.3.6.1.2.1.1.3.0', v1.IpAddress('127.0.0.1')),
				('.1.3.6.1.2.1.1.4.0', v1.OctetString('From Octet String')),
			]
		)
		result = store.nextOID( '.1.3.6.1.2.1.1.1.0' )
		assert result[0] == '.1.3.6.1.2.1.1.2.0', result
		assert result[1] == 32, result
		
if bsdoidstore:
	class BSDTest( object ):
		def createStorage( self, oids ):
			return bsdoidstore.BSDOIDStore(
				bsdoidstore.BSDOIDStore.open( 'temp.bsd', 'n'),
				OIDs = oids,
			)
	class BSDStorageTest( BSDTest, StorageTest ):
		pass


if __name__ == "__main__":
	unittest.main()