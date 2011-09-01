#!/usr/bin/python

import config
import rpm
import string
import os
import struct
import sys
import glob

from rhn import rpclib


def factory(aClass, *args, **kwargs):
    return apply(aClass, args, kwargs)


def saveHeader(hdr):
#    print hdr
#    print type(hdr)
    cfg = config.initUp2dateConfig()
    fileName = "%s/%s.%s.hdr" % (cfg["storageDir"],
                                 string.join( (hdr['name'],
                                               hdr['version'],
                                               hdr['release']),
                                              "-"),
                                 hdr['arch'])

#    print fileName
    fd = os.open(fileName, os.O_WRONLY|os.O_CREAT, 0600)

    os.write(fd, hdr.unload())
    os.close(fd)

    return 1



def saveListToDisk(list, filePath, globstring):

     # delete any existing versions
     filenames = glob.glob(globstring)
     for filename in filenames:
          # try to be at least a little paranoid
          # dont follow symlinks...
          # not too much to worry about, unless storageDir is
          # world writeable
          if not os.path.islink(filename):
               os.unlink(filename)

     # since we have historically used xmlrpclib.dumps() to do
     # this, might as well continue
     infostring = rpclib.xmlrpclib.dumps((list, ""))

     f = open(filePath, "w")
     f.write(infostring)
     f.close()
