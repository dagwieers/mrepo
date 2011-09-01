#!/usr/bin/python
#
#  module containing all the shared messages used by up2date
#
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Adrian Likins <alikins@redhat.com
#
# $Id: up2dateMessages.py 87080 2005-11-04 20:49:52Z alikins $

from up2date_client import config

#cfg = config.initUp2dateConfig()

needToRegister = "You need to register this system by running `up2date --register` before using this option"

storageDirWarningMsg = """The storage directory %s could not be found, or was not
accessable.""" % "/var/spool/up2date"

rootWarningMsg = "You must run the Update Agent as root."

registeredWarningMsg = """You are not registered with Red Hat Network.  To use Update Agent,
You must be registered.

To register, run \"up2date --register\"."""


gpgWarningGuiMsg = """Your GPG keyring does not contain the Red Hat, Inc. public key.
Without it, you will be unable to verify that packages Update Agent downloads
are securely signed by Red Hat.

Your Update Agent options specify that you want to use GPG."""

gpgWarningMsg = """Your GPG keyring does not contain the Red Hat, Inc. public key.
Without it, you will be unable to verify that packages Update Agent downloads
are securely signed by Red Hat.

Your Update Agent options specify that you want to use GPG.

To install the key, run the following as root:
"""
