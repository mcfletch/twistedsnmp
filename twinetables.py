"""Convert indexed tabular sets into convenient format

By default, getTable( [roots] ) returns a dictionary structure
like this:
	rootOID: { fullOID:value }

however, tables in SNMP Agents are often indexed by equal
extensions to the root OID, so that fullOIDs x.3 and y.3 will
refer to the same described phenomena.  twineTables processes
the returned structure into one of this form:

	extension: { rootOID: value }

where extension is fullOID[len(rootOID):]
"""

def twineTables( oidTable, oids ):
	"""Given oidTable with root OIDs, give per-item version

	oidTable -- raw results from getTable query
	oids -- oids to extract from oidTable and coerce to
		the result-table format.

	Common pattern in SNMP organisation is to have indexed
	tables such that, for a given set of tables, the id
	indexing into the table is identical across each table,
	so that ifWhatever.3 and ifWhenever.3 are describing the
	same phenomena.  This method returns from oidTable 
	extension-indexed records for each record in the tables.
	"""
	if not oids:
		raise ValueError( """Null oids argument specified, require at least 1 oid to twine""" )
	result = {}
	for oid in oids:
		table = oidTable.get( oid, {} )
		for key,value in table.iteritems():
			subKey = key[len(oid):]
			record = result.get( subKey ) or {}
			record[ oid ] = value
			result[subKey] = record
	return result