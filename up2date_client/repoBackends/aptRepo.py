#!/usr/bin/python

import os
import sys
import time
import glob
import gzip
import string
import urllib
import xmlrpclib

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import rpmUtils
from up2date_client import config
from up2date_client import rpcServer
from up2date_client import up2dateUtils

import genericRepo
import genericSolveDep
import urlUtils


class AptSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "apt"


class AptRepoSource(rpmSource.PackageSource):
    def __init__(self,  proxyHost=None,
                 loginInfo = None, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self_loginInfo=loginInfo


    def listAllPackages(self, channel,
                        msgCallback = None, progressCallback = None):
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        rd = repoDirector.initRepoDirector()
        pkgList = rd.listPackages(channel, msgCallback, progressCallback)

        list = pkgList[0]
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)
        return list
    
    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        # TODO: implement cache invalidations, Last-Modified
        filePath =  "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])

        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])
        oldLists = glob.glob(globPattern)
        channelTimeStamp = None
        if oldLists:
            filename = oldLists[0]
            filename = os.path.basename(filename)
            oldVersion = string.split(filename, '.')[-1]
            channelTimeStamp = time.strptime(oldVersion,"%Y%m%d%H%M%S")

        # assuming this is always bz2?
        url = "%s/base/pkglist.%s.bz2" % (channel['url'], channel['dist'])
        if msgCallback:
	    msgCallback("Fetching %s" % url)


        ret = urlUtils.fetchUrl(url, lastModified=channelTimeStamp,
                                progressCallback = progressCallback,
                                agent = "Up2date %s/Apt" % up2dateUtils.version())
        if ret:
            (buffer, lmtime) = ret
        else:
            return None

        symlinkname =  "%s/link-%s" % (self.cfg["storageDir"], channel['label'])
        try:
            os.unlink(symlinkname)
        except OSError:
            # file doesnt exist, shrug
            pass

        

        self.version = time.strftime("%Y%m%d%H%M%S", lmtime)
        filePath =  "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], self.version)
        
        # sigh, no native bzip2 module... do it the old fashioned way
        tmpfilename = "%s/tmp-%s-%s" % (self.cfg['storageDir'], channel['label'], self.version)
        #print "timefilename: %s" % tmpfilename
        f = open("%s.bz2" % tmpfilename, "w")
        f.write(buffer)
        f.close()
        
        # FIXME, um, lame... once we settle on what url/http lib
        # we use, plugin in proper callbacks
        if progressCallback:
            progressCallback(1, 1)

        # well, since we dont have any knowledge about what the
        # channel version is supposed to be, I'cant really rely
        # on that (with up2date, the login tells me what channel
        # versions to look for). So we need a generic name
        # we symlink to the latest version.


        pipe = os.popen("/usr/bin/bunzip2 %s.bz2" % tmpfilename)
        tmp = pipe.read()

        os.symlink(tmpfilename, symlinkname)

        hdrList = rpm.readHeaderListFromFile(tmpfilename)
        # a list of rpm hdr's, handy!!

        pkgList = []

        for hdr in hdrList:
            epoch = hdr['epoch']
            if epoch == None or epoch == "0" or epoch == 0:
                epoch = ""
            pkgList.append([hdr['name'], hdr['version'],
                            hdr['release'], epoch, hdr['arch'],
                            # we want the actual filesize, but alas...
                            str(hdr['size']),
                            channel['label']])

            # what the hell, this is a little bit of a side effect, but
            # were already poking at headers, lets just save them while
            # were at it to same us some trouble
            rpmSourceUtils.saveHeader(hdr)
            self.headerCache["%s-%s-%s.%s" % (hdr['name'], hdr['version'],
                                              hdr['release'], hdr['arch'])] = hdr
             
        # nowwe have the package list, convert it to xmlrpc style
        # presentation and dump it
        pkgList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(pkgList, filePath, globPattern)


        return pkgList
        
    def getObsoletes(self, channel,
                     msgCallback = None,
                     progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])

        if msgCallback:
            msgCallback("Fetching obsoletes list for %s" % channel['url'])
            
        fileHdrList = "%s/link-%s" % (self.cfg['storageDir'], channel['label'])
        #print "fhl: %s" % fileHdrList

        
        hdrList = rpm.readHeaderListFromFile(fileHdrList)

        # FIXME: since we have the package list, and the headers, we dont
        # have to reload the headerlist...
        
        obsList = []
        total = len(hdrList)
        count = 0
        for hdr in hdrList:

            if progressCallback:
                progressCallback(count,total)
            count = count + 1
            # FIXME: we should share this logic somewhere...
            #   up2dateUtils maybe?
            if not hdr['obsoletes']:
                continue
            obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
            if obs:
                obsList = obsList + obs
                
        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        obsList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(obsList, filePath,globPattern) 

        return obsList


    def getHeader(self, package, msgCallback = None, progressCallback = None):
        # there are weird cases where this can happen, mostly as a result of
        # mucking with things in /var/spool/up2date
        #
        # not a particularly effiencent way to get the header, but we should
        # not get hit very often

        return None
        
 ##       channel =  rhnChannel.selected_channels.getByName(package[6])
##        fileHdrList = "/var/spool/up2date/link-%s" % (channel.name)
##        print "fhl: %s" % fileHdrList
##        hdrList = rpm.readHeaderListFromFile(fileHdrList)
##        for hdr in hdrList:
##            if package[0] != hdr['name']:
##                continue
##            if package[1] != hdr['version']:
##                continue
##            if package[2] != hdr['release']:
##                continue
##            if package[4] != hdr['arch']:
##                continue
            
##            rpmSourceUtils.saveHeader(hdr)
##            self.headerCache["%s-%s-%s.%s" % (hdr['name'], hdr['version'],
##                                              hdr['release'], hdr['arch'])] = hdr

##            return hdr
            
            

    def getPackage(self, package, msgCallback = None, progressCallback = None):
        filename = "%s-%s-%s.%s.rpm" % (package[0], package[1], package[2],
                                        package[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(package[6])
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        # FIXME: apt has some more sophisticated logic for actually finding
        # the package that this, probabaly need to implement to support
        # most repos
        url = "%s/RPMS.%s/%s" % (channel['url'], channel['dist'], filename)

        if msgCallback:
            #DEBUG
            msgCallback(filename)

        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Apt" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer
        
    def getPackageSource(self, channel, package, msgCallback = None, progressCallback = None):
        filename = package
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        if msgCallback:
            msgCallback(filename)
        url = "%s/SRPMS.%s/%s" % (channel['url'], channel['dist'], filename)

        
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Apt" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer

# see comment about YumDiskCache in yumRepo.py
class AptDiskCache(rpmSource.PackageSource):
    def __init__(self, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        globPattern = "%s/%s.*" %  (self.cfg["storageDir"], channel['label'])
        lists = glob.glob(globPattern)

        # FIXME?
        # we could sort and find the oldest, but there should
        # only be one
        
        if len(lists):
            localFilename = lists[0]
        else:
            # for now, fix PackageSourceChain to not freak
            # when everything returns None

            #FIXME
            return 12344444444444

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        tmp_args, tmp_method = xmlrpclib.loads(filecontents)
        
        # tmp_args[0] is the list of packages
        return tmp_args[0]
        

class AptRepo(genericRepo.GenericRepo):
    def __init__(self):
        genericRepo.GenericRepo.__init__(self)
        self.hds = rpmSource.DiskCache()
        self.ars = AptRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
        self.ads = AptDiskCache()
        self.hldc = rpmSource.LocalDisk()

        self.psc.headerCache = localHeaderCache

        

        self.sources = {'listPackages':[{'name':'apt', 'object': self.ars},
                                        {'name':'aptdiskcache', 'object':self.ads},
                                        ],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'apt', 'object': self.ars}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'apt', 'object': self.ars}],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hldc},
                                     {'name':'apt', 'object': self.ars}],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'apt', 'object': self.ars}
                                      ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'apt', 'object': self.ars}
                                            ]
                        
                        }

    def updateAuthInfo(self):
        pass

def register(rd):
    aptRepo = AptRepo()
    rd.handlers['apt']= aptRepo
    aptSolveDep = AptSolveDep()
    rd.depSolveHandlers['apt'] = aptSolveDep
    
