#
# __init__.py
#
# Copyright (c) 2005 Red Hat, Inc.
# 
# $Id: __init__.py 89042 2005-07-05 22:05:02Z wregglej $
"""
rhn - A collection of modules used by Red Hat Network
"""

import rpclib
xmlrpclib = rpclib.xmlrpclib

__all__ = ["rpclib", "xmlrpclib"]
