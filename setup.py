#!/usr/bin/python

### This program is free software; you can redistribute it and/or modify
### it under the terms of the GNU Library General Public License as published by
### the Free Software Foundation; version 2 only
###
### This program is distributed in the hope that it will be useful,
### but WITHOUT ANY WARRANTY; without even the implied warranty of
### MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
### GNU Library General Public License for more details.
###
### You should have received a copy of the GNU Library General Public License
### along with this program; if not, write to the Free Software
### Foundation, Inc., 59 Temple Place - Suite 330, Boston, MA 02111-1307, USA.
### Copyright 2004-2006 Dag Wieers <dag@wieers.com>

### FIXME: distutils is pretty clueless for tools (no globs, no renames, ...)
import sys
print 'Distutils installation not enabled. Please use Makefile for now.'
sys.exit(1)

# if someday we want to *require* setuptools, uncomment this:
# (it will cause setuptools to be automatically downloaded)
#import ez_setup
#ez_setup.use_setuptools()

try:
	from setuptools import setup
except ImportError:
	from distutils.core import setup

setup(
	name = 'depo',
	version = '0.8.4svn',
	description = 'RPM repository mirroring tool',
	author = 'Dag Wieers',
	author_email ='dag@wieers.com',
	url = "http://dag.wieers.com/home-made/depo/",
	scripts=['depo', 'gensystemid'],
	data_files=[
		('/etc', ['config/depo.conf']),
		('/etc/init.d', ['config/depo']),
		('/etc/httpd/conf.d', ['config/httpd/depo.conf']),
		('/var/cache/depo', []),
		('/var/www/depo', []),
		('/var/depo/all/local', []),
		('/usr/share/depo/html', ['html/HEADER.index.shtml', 'html/HEADER.repo.shtml', 'html/README.index.shtml', 'html/README.repo.shtml']),
	],
	download_url = 'http://dag.wieers.com/home-made/depo/depo-0.8.1.tar.gz',
	license = 'GPL',
	platforms = 'Posix',
	classifiers = [
		'Internet :: WWW/HTTP :: Site Management',
		'System :: Archiving :: Mirroring',
		'System :: Archiving :: Packaging',
		'System :: Installation/Setup',
		'System :: Software Distribution',
		'System :: Software Distribution Tools',
		'System :: Systems Administration',
	],
	long_description = '''
Depo builds a local APT/Yum RPM repository from local ISO files, downloaded
updates, and extra packages from RHN (Red Hat Network) and 3rd party
repositories. It takes care of setting up the ISO files, downloading the
RPMs, configuring HTTP access, and providing PXE/TFTP resources for remote
installations.

It was primarily intended for doing remote network installations of various
distributions from a laptop without the need for CD media or floppies, but
is equally suitable for an organization's centralized update server.

Depending on the use it may require:
	apt, up2date, yum, createrepo, repoview, hardlink and/or hardlink++
''',
)

# vim:ts=4:sw=4
