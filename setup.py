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

	### Now the actual set up call
	setup (
		name = "TwistedSNMP",
		version = "0.2.6",
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
	)
	
