#!/usr/bin/env python
"""Installs twistedsnmp using distutils

Run:
	python setup.py install
to install the package from the source archive.
"""

if __name__ == "__main__":
	import sys,os, string
	from distutils.sysconfig import *
	from distutils.core import setup

	##############
	## Following is from Pete Shinners,
	## apparently it will work around the reported bug on
	## some unix machines where the data files are copied
	## to weird locations if the user's configuration options
	## were entered during the wrong phase of the moon :) .
	from distutils.command.install_data import install_data
	class smart_install_data(install_data):
		def run(self):
			#need to change self.install_dir to the library dir
			install_cmd = self.get_finalized_command('install')
			self.install_dir = getattr(install_cmd, 'install_lib')
			# should create the directory if it doesn't exist!!!
			return install_data.run(self)
	##############

	from sys import hexversion
	if hexversion >= 0x2030000:
		# work around distutils complaints under Python 2.2.x
		extraArguments = {
			'classifiers': [
				"""License :: OSI Approved :: BSD License""",
				"""Programming Language :: Python""",
				"""Topic :: Software Development :: Libraries :: Python Modules""",
				"""Intended Audience :: Developers""",
				"""Topic :: System :: Networking :: Monitoring""",
				"""Topic :: System :: Networking""",
			],
			'download_url': "https://sourceforge.net/project/showfiles.php?group_id=102250",
			'keywords': 'snmp,twisted,manager,agent,protocol,oid,oidstore',
			'long_description' : """SNMP Protocol for the Twisted Networking Framework

TwistedSNMP is a set of SNMP protocol implementations
for Python's Twisted Matrix networking framework using
the PySNMP project.  It provides the following:

    * get, set, getnext and getbulk Manager-side queries
    * get, set, getnext and getbulk Agent-side services

Eventual goals of the system (the project is just beginning):

    * provide access to all v1 and v2 SNMP functionality
      for writing Agent and Manager services
    * provide convenient testing mechanisms for SNMP
      Agent/Manager development (e.g. mirroring an SNMP
      Agent's OID tree for local query testing)
""",
			'platforms': ['Any'],
		}
	else:
		extraArguments = {
		}
	### Now the actual set up call
	setup (
		name = "TwistedSNMP",
		version = "0.3.0",
		url = "http://twistedsnmp.sourceforge.net/",
		description = "SNMP Protocol for the Twisted Networking Framework",
		author = "Mike C. Fletcher & Patrick K. O'Brien",
		author_email = "mcfletch@users.sourceforge.net",
		license = "BSD-style, see license.txt for details",

		package_dir = {
			'twistedsnmp':'.',
		},
		packages = [
			'twistedsnmp',
			'twistedsnmp.utilities',
			'twistedsnmp.test',
		],
		**extraArguments
	)
	
