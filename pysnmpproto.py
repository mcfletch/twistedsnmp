"""Create single import location for v2c and v1 protocols

These can get moved around inside PySNMP, so we need this
code to determine where the prototypes are, so we can reliably
and simply import them throughout TwistedSNMP.
"""
try:
	from pysnmp.proto import v2c, v1, error, rfc1155, rfc1902
	# generic appears to have side effects we need...
	from pysnmp.proto.api import generic
except ImportError, err:
	from pysnmp.v4.proto.omni import v2c,v1, error, rfc1157, rfc1905
	
