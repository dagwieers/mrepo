#!/usr/bin/python
#
# a chain of responsibilty class for stacking package sources
# for up2date
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Adrian Likins <alikins@redhat.com>
#
"""A chain of responsibility class for stacking package sources for up2date"""

#import timeoutsocket
#timeoutsocket.setDefaultSocketTimeout(1)
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

import up2dateUtils
import up2dateLog
import up2dateErrors
import glob
import socket
import re
import os
import rpm
import string
import time
import struct
import config
import rpmUtils
import up2dateAuth
import up2dateUtils
#import headers
#import rpcServer
import transaction
#import timeoutsocket
import urllib
import gzip
import rhnChannel
import sys
import rpmSourceUtils

from rhn import rpclib

from rhpl.translate import _, N_


BUFFER_SIZE = 8092


def factory(aClass, *args, **kwargs):
    return apply(aClass, args, kwargs)


class HeaderCache:
    def __init__(self):
        self.cfg = config.initUp2dateConfig()
        # how many headers to cache in ram
        if self.cfg["headerCacheSize"]:
            self.cache_size = self.cfg["headerCacheSize"]
        else:
            self.cache_size = 30
        self.__cache = {}
        self.__cacheLite = {}

    def set_cache_size(self, number_of_headers):
        self.cache_size = number_of_headers

    def __liteCopy(self, header):
        tmp = {}
        tmp['name'] = header['name']
        tmp['version'] = header['version']
        tmp['release'] = header['release']
        tmp['arch'] = header['arch']
        tmp['summary'] = header['summary']
        tmp['description'] = header['description']
        tmp['size'] = header['size']
        return tmp

    def __setitem__(self,item,value):
        if len(self.__cache) <= self.cache_size:
            self.__cache[item] = value
            self.__cacheLite[item] = self.__liteCopy(value)
        else:
            # okay, this is about as stupid of a cache as you can get
            # but if we hit the max cache size, this is as good as
            # any mechanism for freeing up space in the cache. This
            # would be a good place to put some smarts
            bar = self.__cache.keys()
            del self.__cache[bar[self.cache_size-1]]
            self.__cache[item] = value
            self.__cacheLite[item] = self.__liteCopy(value)

    def __getitem__(self, item):
        return self.__cache[item]
    

    def getLite(self, item):
        return self.__cacheLite[item]

    def __len__(self):
        return len(self.__cache)

    def keys(self):
        return self.__cache.keys()

    def values(self):
        return self.__cache.keys()

    def has_key(self, item,lite=None):
#        print "\n########\nhas_key called\n###########\n"
#        print "item: %s" % item
#        print self.__cache.keys()
        
        if lite:
            return self.__cacheLite.has_key(item)
        else:
            return self.__cache.has_key(item)

    def __delitem__(self, item):
        del self.__cache[item]

    def printLite(self):
        print self.__cacheLite


# this is going to be a factory. More than likely, it's input for
# it's init is going to be read from a config file. 
#
#  goals... easy "stacking" of data sources with some sort of priority
#      make the goal oblivous to the "names" of the data sources
class PackageSourceChain:
    def __init__(self, headerCacheObject = None, metainfolist = None):
        self.log = up2dateLog.initLog()
        self.metainfo = {}
        # lame, need to keep a list to keep the order
        self.source_list = []
        if metainfolist != None:
            for source in metainfolist:
                self.addSourceClass(source)

        self.headerCache = headerCacheObject


    def addSourceClass(self, metainfo):
        source = metainfo
        name = source['name']
        self.log.log_debug("add source class name", name)
        self.source_list.append(name)
        self.metainfo[name] = factory(
            source['class'], source['args'], source['kargs'])

        # automagically associated the header cache for the stack with each
        # object in the chain so we can populate the cache if need be
        self.metainfo[name].addHeaderCacheObject(self.headerCache)
        #log.log_debug("class: %s args: %s kargs %s" % (
        #    source['class'], source['args'], source['kargs']))


    def clearSourceInstances(self):
        self.metainfo = {}
        self.source_list = []

    def setSourceInstances(self, metainfoList):
        self.clearSourceInstances()
        for metainfo in metainfoList:
            self.addSourceInstance(metainfo)

    def addSourceInstance(self, metainfo):
        source = metainfo
        name = source['name']
        #        self.log.log_debug("add instance class name", name)
        self.source_list.append(name)
        self.metainfo[name] = source['object']

        # automagically associated the header cache for the stack with each
        # object in the chain so we can populate the cache if need be
        self.metainfo[name].addHeaderCacheObject(self.headerCache)
        self.metainfo[name]['name'] =  name       
        #log.log_debug("object: %s name: %s" % (source['object'], name))

    def getPackage(self, pkg, MsgCallback = None, progressCallback = None):
        self.log.log_debug("getPackage", pkg)
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            # FIXME: wrap in approriate exceptions
            package = source.getPackage(pkg, MsgCallback, progressCallback)
            if package != None:
                self.log.log_debug("Package %s Fetched via: %s" % (
                    pkg, source['name']))
                #self.fetchType[pkg] = source['name']
                return package
        return None

    def getPackageSource(self, channel, pkg,
                         MsgCallback = None, progressCallback = None):
        self.log.log_debug("getPackageSource", channel, pkg)
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            # FIXME: wrap in approriate exceptions
            package = source.getPackageSource(channel, pkg,
                                              MsgCallback, progressCallback)
            if package != None:
                self.log.log_debug("Source %s Package Fetched via: %s" %(
                    pkg, source['name']))
                return package
        return None
    

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        # if the package source is specified, use it
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            header = source.getHeader(pkg, progressCallback = progressCallback)
            # return the first one we find
            if header != None:
#                self.log.log_debug("Header for %s Fetched via: %s" % (
#                    pkg, source['name']))
                #print "source: %s" % source['name']
                # FIXME, the normal one only returns the header
                return (header,source['name'])
        return None

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            packageList = source.listPackages(channel,
                                              msgCallback, progressCallback)
            if packageList != None:
                self.log.log_debug("listPackages Fetched via:", source['name'])
                return (packageList, source['name'])
        return None

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        for source_key in self.source_list:
            source = self.metainfo[source_key]
            packageList = source.listAllPackages(channel,
                                              msgCallback, progressCallback)
            if packageList != None:
                self.log.log_debug("listAllPackages Fetched via:", source['name'])
                return (packageList, source['name'])
        return None

    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        for source_key in self.source_list:
            source = self.metainfo[source_key]
            obsoletesList = source.getObsoletes(channel,
                                                msgCallback, progressCallback)
            if obsoletesList != None:
                self.log.log_debug("getObsoletes Fetched via:", source['name'])
                return (obsoletesList, source['name'])
        return None


# template class for all the sources in the chain
class PackageSource:
    def __init__(self, cacheObject = None):
        self.headerCache = None
        self.info = {}
        
    def getHeader(self, pkg):
        ""
        pass
    
    def getPackage(self, pkg):
        ""
        pass
    
    def addHeaderCacheObject(self, cacheObject):
        ""
        self.headerCache = cacheObject
        
    def __setitem__(self, item, value):
        self.info[item] = value

    def __getitem__(self, item):
        return self.info[item]
        
class HeaderMemoryCache(PackageSource):
    def __init__(self, cacheObject = None):
        PackageSource.__init__(self,cacheObject)
    
    def getHeader(self, pkg, lite = None,
                  msgCallback = None, progressCallback = None):
        if lite:
            if self.headerCache.has_key(up2dateUtils.pkgToStringArch(pkg), lite = 1):
                return self.headerCache.getLite(up2dateUtils.pkgToStringArch(pkg))

        if self.headerCache.has_key(up2dateUtils.pkgToStringArch(pkg)):
            return self.headerCache[up2dateUtils.pkgToStringArch(pkg)]


class LocalDisk(PackageSource):
    def __init__(self, cacheObject = None, packagePath = None):
        self.cfg = config.initUp2dateConfig()
        self.log = up2dateLog.initLog()
        self.dir_list = up2dateUtils.getPackageSearchPath()
        if packagePath:
            self.dir_list = self.dir_list + packagePath

        self.ts = transaction.initReadOnlyTransaction()
        PackageSource.__init__(self, cacheObject = cacheObject)

    def addPackageDir(self, packagePath):
        self.dir_list = self.dir_list + packagePath

    def __saveHeader(self, hdr):
        tmp = rpmUtils.readHeaderBlob(hdr.unload())
        rpmSourceUtils.saveHeader(tmp)
        

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)

        fileNames = tmpFileNames
        if len(fileNames):
            if os.access(fileNames[0], os.R_OK):
                if not re.search("rpm$", fileNames[0]):
                    # it wasnt an rpm, so must be a header
                    if os.stat(fileNames[0])[6] == 0:
                        return None
                    fd = open(fileNames[0], "r")
                    # if this header is corrupt, rpmlib exits and we stop ;-<
                    try:
                        hdr = rpmUtils.readHeaderBlob(fd.read())
                    except:
                        return None
                    self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                    fd.close()
                    self.__saveHeader(hdr)
                    return hdr
                else:
                    fd = os.open(fileNames[0], 0)
                    # verify just the md5
                    self.ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
                    try:
                        #hdr = rpm.headerFromPackage(fd)
                        hdr = self.ts.hdrFromFdno(fd)
                    except:
                        os.close(fd)
                        self.ts.popVSFlags()
                        raise up2dateErrors.RpmError(_("Error reading header"))
                    self.ts.popVSFlags()
                    os.close(fd)
                    self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                    self.__saveHeader(hdr)
                    return hdr
                    
            else:
                 return None        
        else:
            for dir in self.dir_list:
                fileNames = glob.glob("%s/%s.noarch.*" %
                                      (dir,
                                       up2dateUtils.pkgToString(pkg)))
            if len(fileNames):
                if os.access(fileNames[0], os.R_OK):
                    if not re.search("rpm$", fileNames[0]):
                        # it's not an rpm, must be a header
                        if os.stat(fileNames[0])[6] == 0:
                            return None
                        fd = open(fileNames[0], "r")
                        try:
                            hdr = rpmUtils.readHeaderBlob(fd.read())
                        except:
                            self.log.log_me("Corrupt header %s, skipping, "\
                                       "will download later..." % fileNames[0])
                            return None
                        fd.close()
                        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                        return hdr
                    else:
                        if os.access(fileNames[0], os.R_OK):
                            fd = os.open(fileNames[0], 0)
                            try:
                                #hdr = rpm.headerFromPackage(fd)
                                hdr = self.ts.hdrFromFdno(fd)
                            except:
                                os.close(fd)
                                raise up2dateErrors.RpmError(_(
                                    "Error reading header"))
                            os.close(fd)
                            self.log.log_me("Reading header from: %s" % fileNames)
                            self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
                            return hdr
                        else:
                            return None
                else:
                    return None
            else:
                return None
    
    # this is kind of odd, since we actually just symlink to the package from
    # the cache dir, instead of copying it around, or keeping track of where
    # all the packages are from
    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            # if the file is in the storageDir, dont symlink it to itself ;->
            if len(tmpFileNames) and not (dir == self.cfg["storageDir"]):
                try:
                    os.remove(fileName)
                except OSError:
                    pass
                # no callback, since this will have to fall back to another repo to actually get
                os.symlink(tmpFileNames[0], fileName)
                fd = open(tmpFileNames[0], "r")
                buffer = fd.read()
                fd.close()
                return buffer

            
    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        baseFileName = "%s" % (srcpkg)
        for dir in self.dir_list:
            tmpFileNames = glob.glob("%s/%s" % (dir, baseFileName))
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            # if the file is in the storageDir, dont symlink it to itself ;->
            if len(tmpFileNames) and not (dir == self.cfg["storageDir"]):
                try:
                    os.remove(fileName)
                except OSError:
                    # symlink doesnt exist, this is fine
                    pass
                if msgCallback:
                    msgCallback(fileName)
                os.symlink(tmpFileNames[0], fileName)
                break


class DiskCache(PackageSource):
    def __init__(self, cacheObject = None):
        # this is the cache, stuff here is only in storageDir
        self.cfg = config.initUp2dateConfig()
        self.log = up2dateLog.initLog()
        self.dir_list = [self.cfg["storageDir"]]
        self.ts =  transaction.initReadOnlyTransaction()
        PackageSource.__init__(self, cacheObject = cacheObject)

    def __readHeaderFromRpm(self, fileNames, pkg):

        
        fd = os.open(fileNames[0], 0)
        self.ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
        try:
            hdr = self.ts.hdrFromFdno(fd)
        except:
             os.close(fd)
             self.ts.popVSFlags()
             raise up2dateErrors.RpmError(_("Error reading header"))
        self.ts.popVSFlags()
        os.close(fd)
        self.log.log_me("Reading header from: %s" % fileNames)
        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
        return hdr
     

    def __readHeaderFromFile(self, fileNames, pkg):
        if os.access(fileNames[0], os.R_OK):
            if os.stat(fileNames[0])[6] == 0:
                print "stat failed", fileNames[0]
                return None
            hdr = rpmUtils.readHeader(fileNames[0])
            if hdr == None:
                return None
            self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
            return hdr
        else:
            return None
        
    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        for dir in self.dir_list:
            fileNames = glob.glob(
                "%s/%s.%s.hdr" % (dir, up2dateUtils.pkgToString(pkg), pkg[4]))
            # if we find anything, bail
            if len(fileNames):
                break


        if len(fileNames):
            hdr = self.__readHeaderFromFile(fileNames, pkg)
            if hdr:
                return hdr
            else:
                # the header aint there, return none so the rest
                # of the crap will go fetch it again
                return None

        else:
            for dir in self.dir_list:
                fileNames = glob.glob(
                    "%s/%s.noarch.hdr" % (dir, up2dateUtils.pkgToString(pkg)))

            # see if it is a .hdr file, if not try reading it as an rpm
            if len(fileNames):
                hdr = self.__readHeaderFromFile(fileNames, pkg)
                if hdr:
                    return hdr
                else:
                    hdr = self.__readHeaderFromRpm(fileNames,pkg)
                    return hdr

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):

        baseFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2], pkg[4])
        # check if we already have package and that they are valid
        fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)

        if os.access(fileName, os.R_OK) and \
               rpmUtils.checkRpmMd5(fileName):
            if msgCallback:
                msgCallback(baseFileName)
            if progressCallback != None:
                progressCallback(1, 1)
            return 1
        else:
            return None

    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        baseFileName = "%s" % (srcpkg)
        fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
        
        # check if we already have package and that they are valid
        if os.access(fileName, os.R_OK):
        # if os.access(fileName, os.R_OK) and \
        #    not rpmUtils.checkRpmMd5(fileName):
            if msgCallback:
                msgCallback(baseFileName)
            if progressCallback != None:
                progressCallback(1, 1)
            return 1
        else:
            return None


    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        localFilename = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)
        
        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        localFilename = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)
        
        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]


    def getObsoletes(self, channel, version,
                     msgCallback = None, progressCallback = None):
        localFilename = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                                channel['label'],
                                                channel['version'])
        if not os.access(localFilename, os.R_OK):
            return None

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        try:
            tmp_args, tmp_method = rpclib.xmlrpclib.loads(filecontents)
        except:
            # if there was an error decoding return as if we didnt find it
	    # the odd thing is, in testing, it's actually pretty hard to get
	    # a file to show as corrupt, I think perhaps the xmlrpclib parser
	    # is a bit too lenient...
	    return None

        # tmp_args[0] is the list of packages
        return tmp_args[0]

        
    
# need a ton of helper functions for this one, but then, it's the main one
class Up2datePackageSource(PackageSource):
    def __init__(self, server, proxyHost, cacheObject = None):
        self.s = server
        PackageSource.__init__(self, cacheObject = cacheObject)
        

    # fetch it from the network, no caching of any sort
    def getHeader(self, pkg, lite = None,
                  msgCallback = None, progressCallback = None):
        hdr = None

        try:
            ret = self.s.up2date.header(up2dateAuth.getSystemId(), pkg)
        except KeyboardInterrupt:
            raise up2dateErrors.CommunicationError(_(
                "Connection aborted by the user"))
        except (socket.error, socket.sslerror), e:
            if len(e.args) > 1:
                raise up2dateErrors.CommunicationError(e.args[1])
            else:
                raise up2dateErrors.CommunicationError(e.args[0])
        except rpclib.ProtocolError, e:
            raise up2dateErrors.CommunicationError(e.errmsg)
        except rpclib.ResponseError:
            raise up2dateErrors.CommunicationError(
                "Broken response from the server.");
        except rpclib.Fault, f:
            raise up2dateErrors.CommunicationError(f.faultString)

        bin = ret[0]
        hdr = rpmUtils.readHeaderBlob(bin.data)
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache["%s-%s-%s.%s" % (hdr['name'],
                                          hdr['version'],
                                          hdr['release'],
                                          hdr['arch'])] = hdr
        return hdr


def callback(total, complete):
    print "-- %s bytes of %s" % (total, complete)

# FIXME: super ugly hack that deserves to die
def updateHttpServer(packageSourceChain, logininfo, serverSettings):

    httpServer = getGETServer(LoginInfo.logininfo, serverSettings)

    hds = HttpGetSource(httpServer, None, loginInfo = logininfo)
    packageSourceChain.addSourceInstance({'name':'get', 'object': hds})

    return packageSourceChain


