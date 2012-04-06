#
# __init__.py
#
# Copyright (c) 2005 Red Hat, Inc.
# 
# $Id: __init__.py 191145 2010-03-01 10:21:24Z msuchy $
"""
rhn - A collection of modules used by Red Hat Network
"""

import rpclib
xmlrpclib = rpclib.xmlrpclib

__all__ = ["rpclib", "xmlrpclib"]
