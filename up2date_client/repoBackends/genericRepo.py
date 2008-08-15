#!/usr/bin/python


import os
import sys

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource

class GenericRepo:
    def __init__(self):
        self.psc = rpmSource.PackageSourceChain()
        self.sources = {}
        self.headerCache = None
        
    def __getattr__(self, name):
        self.psc.setSourceInstances(self.sources[name])
        if self.headerCache:
            self.psc.headerCache = self.headerCache
        return getattr(self.psc, name)


