from twistedsnmp.test import basetestcase
from pysnmp.proto import v1
import unittest

class SetRetrieverV1( basetestcase.BaseTestCase ):
	version = 'v1'
	oidsForTesting = [
		('.1.3.6.1.2.1.1.1.0', 'Hello world!'),
		('.1.3.6.1.2.1.1.2.0', 32),
		('.1.3.6.1.2.1.1.3.0', v1.IpAddress('127.0.0.1')),
		('.1.3.6.1.2.1.1.4.0', v1.OctetString('From Octet String')),
	]
	def test_setEndOfOIDs( self ):
		"""After a set, is the set value retrieved?"""
		d = self.client.set(
			[('.1.3.6.1.2.1.1.5.0',3)],
		)
		self.doUntilFinish( d )
		d = self.client.get(
			['.1.3.6.1.2.1.1.5.0',],
		)
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == { '.1.3.6.1.2.1.1.5.0':3 }

	def test_setReplaceAnOID( self ):
		"""After a replace-set, is the set value retrieved?"""
		d = self.client.set(
			[('.1.3.6.1.2.1.1.4.0',3)],
		)
		self.doUntilFinish( d )
		d = self.client.get(
			['.1.3.6.1.2.1.1.4.0',],
		)
		self.doUntilFinish( d )
		assert self.success, self.response
		assert self.response == { '.1.3.6.1.2.1.1.4.0':3 }
class SetRetrieverV2C( SetRetrieverV1 ):
	version = 'v2c'

if basetestcase.bsdoidstore:
	class SetRetrieverV1BSD( basetestcase.BSDBase, SetRetrieverV1 ):
		pass
	class SetRetrieverV2CBSD( basetestcase.BSDBase, SetRetrieverV2C ):
		pass

if __name__ == "__main__":
	unittest.main()
	