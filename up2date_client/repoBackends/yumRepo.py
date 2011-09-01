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
import urlUtils
import genericSolveDep

class YumSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "yum"


class YumRepoSource(rpmSource.PackageSource):
    def __init__(self, proxyHost=None,
                 loginInfo=None, cacheObject=None,
                 register=None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self._loginInfo=loginInfo
        self.headerCache = cacheObject
        self.pkglists = {}


    # stright out of yum/clientstuff.py
    # might as well use there code to parse there info
    def _stripENVRA(self,str):
        archIndex = string.rfind(str, '.')
        arch = str[archIndex+1:]
        relIndex = string.rfind(str[:archIndex], '-')
        rel = str[relIndex+1:archIndex]
        verIndex = string.rfind(str[:relIndex], '-')
        ver = str[verIndex+1:relIndex]
        epochIndex = string.find(str, ':')
        epoch = str[:epochIndex]
        name = str[epochIndex + 1:verIndex]
        return (epoch, name, ver, rel, arch)


    def getHeader(self, package, msgCallback = None, progressCallback = None):
        # yum adds the epoch into the filename of the header, so create the
        # approriate remotename, handling epoch=0 crap as well
        if package[3] == "":
            remoteFilename = "%s-%s-%s-%s.%s.hdr" % (package[0], "0", package[1], package[2],
                                        package[4])
        else:
            remoteFilename = "%s-%s-%s-%s.%s.hdr" % (package[0], package[3], package[1], package[2],
                                        package[4])

        if msgCallback:
            msgCallback(remoteFilename)

        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(package[6])
        url = "%s/headers/%s" % (channel['url'],remoteFilename )
	if msgCallback:
		msgCallback("Fetching %s" % url)
        # heck, maybe even borrow the one from yum

        
        nohdr = 1
        count = 0
        while ((nohdr) and (count < 5)):
            count = count + 1 
            try:
                # fix this to use fetchUrl and stringIO's for gzip
                (fn, h) = urllib.urlretrieve(url)
                
                #        print fn
                # the yum headers are gzip'ped
                fh = gzip.open(fn, "r")
                
                hdrBuf = fh.read()
                
                # FIXME: lame, need real callbacks
                if progressCallback:
                    progressCallback(1,1)
            
                hdr = rpmUtils.readHeaderBlob(hdrBuf)
                rpmSourceUtils.saveHeader(hdr)
                self.headerCache["%s-%s-%s" % (hdr['name'],
                                               hdr['version'],
                                               hdr['release'])] = hdr
                nohdr = 0
            except:
                print "There was an error downloading:", "%s"  % url
                nohdr = 1

        return hdr

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        filename = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2],
                                        pkg[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(pkg[6])

	#print "self.pkgNamePath: %s" % self.pkgNamePath
        #print "stored rpmpath: %s" % self.pkgNamePath[(pkg[0], pkg[1], pkg[2], pkg[3], pkg[4])]
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
	#rpmPath = self.pkgNamePath[(pkg[0], pkg[1], pkg[2], pkg[3], pkg[4])]
        rpmPath = pkg[7]

        url = "%s/%s" % (channel['url'],rpmPath )
        if msgCallback:
            # for now, makes it easier to debug
            #msgCallback(url)
            msgCallback(filename)


            
        
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Yum" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer


    def getPackageSource(self, channel, package, msgCallback = None, progressCallback = None):
        filename = package
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)

        if msgCallback:
            msgCallback(package)
            
        # interesting, yum doesnt seem to let you specify a path for the
        # source rpm...

        # Actually, it does now, but I need to download another meta data
        # file to do it, will do but not till .16 or so

        url = "%s/SRPMS/%s" % (channel['url'], filename)

               
        fd = open(filePath, "w+")
        (lmtime) = urlUtils.fetchUrlAndWriteFD(url, fd,
                                   progressCallback = progressCallback,
                                   agent = "Up2date %s/Yum" % up2dateUtils.version())
                                                                                
        fd.close()
        buffer = open(filePath, "r").read()
        
        return buffer
    

    def listPackages(self, channel,
                     msgCallback = None, progressCallback = None):

        # TODO: where do we implement cache validation? guess we
        # use http header time stamps to make a best guess since we
        # dont have any real info about the file format
        
        # a glob used to find the old versions to cleanup

        # FIXME: this is probabaly overkill... Should only have
        # one version of any given
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])
        oldLists = glob.glob(globPattern)
        channelTimeStamp = None
        if oldLists:
            filename = oldLists[0]
            filename = os.path.basename(filename)
            oldVersion = string.split(filename, '.')[-1]
            channelTimeStamp = time.strptime(oldVersion,"%Y%m%d%H%M%S")


        # for yum stuff, we assume that serverUrl is the base
        # path, channel is the relative path, and version isnt
        # user
        url = "%s/headers/header.info" % (channel['url'])
        if msgCallback:
            msgCallback("Fetching %s" % url)

        # oh, this lame, but implement a fancy url fetcher later
        # heck, maybe even borrow the one from yum
        #print urlUtils
        
        ret = urlUtils.fetchUrl(url, lastModified=channelTimeStamp,
                                progressCallback = progressCallback,
                                agent = "Up2date %s/Yum" % up2dateUtils.version())
        
        if ret:
            (buffer, lmtime) = ret
        else:
            return None

        if not lmtime:
            lmtime = time.gmtime(time.time())
        version = time.strftime("%Y%m%d%H%M%S", lmtime)
        
        # use the time stamp on the headerlist as the channel "version"
        filePath = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], version)

        # it's possible to get bogus data here, so at least try not
        # to traceback
        if buffer:
            lines = string.split(buffer)
        else:
            lines = []

        # this gives us the raw yum header list, which is _not_
        # in the pretty format up2date likes, so convert it
        # and sadly, I can no longer proudly state that up2date
        # at no points attempts to parse rpm filenames into something
        # useful. At least yum includes the epoch
        pkgList = []
        # yum can have a different path for each rpm. Not exactly
        # sure how this meets the "keep it simple" idea, but alas
        self.pkgNamePath = {}
        for line in lines:
            if line == "" or line[0] == "#":
                continue
            (envra, rpmPath) = string.split(line, '=')
            rpmPath = string.strip(rpmPath)
            (epoch, name, ver, rel, arch) = self._stripENVRA(envra)
            # quite possibly need to encode channel info here as well
	    if epoch == "0" or epoch == 0:
                epoch = ""

            # hmm, if an arch doesnt apply, guess no point in
            # keeping it around, should make package lists smaller
            # and cut down on some churn
            if rpm.archscore(arch) == 0:
                continue



            self.pkgNamePath[(name,ver,rel,epoch,arch)] = rpmPath
            # doh, no size info. FIXME
            size = "1000"  # er, yeah... thats not lame at all...
            pkgList.append([name, ver, rel, epoch, arch, size, channel['label'], rpmPath])

        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        pkgList.sort(lambda a, b: cmp(a[0], b[0]))
        
        count = 0
        total = len(pkgList)
        rd = repoDirector.initRepoDirector()
        
        for pkg in pkgList:
            # were deep down in the yum specific bits, but we want to call
            # the generic getHeader to get it off disc or cache
            
            hdr = rd.getHeader([name,ver,rel,epoch,arch, "0",channel['label']])
            if progressCallback:
                progressCallback(count, total)
            count = count + 1

        rpmSourceUtils.saveListToDisk(pkgList, filePath, globPattern)
        self.pkglists[channel['label']] = pkgList
        return pkgList

    def listAllPackages(self, channel,
                        msgCallback = None, progressCallback = None):
        # yum only knows about the most recent packages. Can't say
        # I blame them. I wish i only had to know about the most recent...
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        rd = repoDirector.initRepoDirector()
        pkgList = rd.listPackages(channel, msgCallback, progressCallback)

        list = pkgList[0]
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)
        return list

    
    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        # well, we've got the headers, might as well create a proper
        # obslist at this point
        
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])

        
        if msgCallback:
            msgCallback("Fetching obsoletes list for %s" % channel['url'])

        try:
            pkgList = self.pkglists[channel['label']]
        except KeyError:
            # we just hit the getObsoletes path, with no package info known
            # figure it out ourselves
            rd = repoDirector.initRepoDirector()
            pkgList = rd.listPackages(channel, msgCallback, progressCallback)
            self.pkglists[channel['label']] = pkgList

        obsList = []
        total = len(pkgList)
        count = 0
        for pkg in pkgList:
            baseFileName = "%s-%s-%s.%s.hdr" % (pkg[0], pkg[1], pkg[2], pkg[4])
            fileName = "%s/%s" % (self.cfg["storageDir"], baseFileName)
            
            if os.access(fileName, os.R_OK):
                fd = open(fileName, "r")
                try:
                    hdr = rpmUtils.readHeaderBlob(fd.read())
                except:
                    continue
                fd.close()
                if not hdr['obsoletes']:
                    continue
                obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
                if obs:
#                    print obs
                    obsList = obsList + obs

            if progressCallback:
                progressCallback(count, total)
            count = count + 1
            
        # now we have the package list, convert it to xmlrpc style
        # presentation and dump it
        obsList.sort(lambda a, b: cmp(a[0], b[0]))

        rpmSourceUtils.saveListToDisk(obsList, filePath,globPattern) 
#        print obsList
        return obsList
        

# since we use the diskcache secondary in yum/apt, and
# we dont know the version till after we look at the
# file, we glob for it, and use it 
class YumDiskCache(rpmSource.PackageSource):
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
            return 0

        # FIXME error handling and what not
        f = open(localFilename, "r")
        filecontents = f.read()
        # bump it full
        if progressCallback:
            progressCallback(100,100)

        tmp_args, tmp_method = xmlrpclib.loads(filecontents)
        
        # tmp_args[0] is the list of packages
        return tmp_args[0]


        

class YumRepo(genericRepo.GenericRepo):
    def __init__(self):
        self.login = None
        genericRepo.GenericRepo.__init__(self)
        self.yds = YumDiskCache()
        self.yrs = YumRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)

        # need a layer here to look in the yum cache dir in /var/cache/yum
        # so if someone is using yum and up2date, they can share caches
        # in at least one dir

        self.hds = rpmSource.DiskCache()
        self.hldc = rpmSource.LocalDisk()
        
        self.psc.headerCache = localHeaderCache
        # note that for apt/yum we check to see if the server has been modified
        # and if not, fall back to the diskcache... up2date is the opposite
        self.sources = {'listPackages':[{'name':'yum', 'object': self.yrs},
                                        {'name':'yumdiskcache', 'object':self.yds}],
                       'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'yum', 'object': self.yrs}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'yum', 'object': self.yrs}],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'yum-diskcache', 'object':self.hds},
                                     {'name':'yum-localdisk', 'object':self.hldc},
                                     {'name':'yum', 'object': self.yrs}],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'yum', 'object': self.yrs}
                                      ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'yum', 'object': self.yrs}
                                            ]
                        }

    def updateAuthInfo(self):
        pass

    

def register(rd):
    yumRepo = YumRepo()
    rd.handlers['yum'] = yumRepo
    yumSolveDep = YumSolveDep()
    rd.depSolveHandlers['yum'] = yumSolveDep
    
    
