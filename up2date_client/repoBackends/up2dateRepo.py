#!/usr/bin/python

import os
import sys

import rpm
sys.path.append("/usr/share/rhn/")
import genericRepo
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import up2dateAuth
from up2date_client import rpcServer
from up2date_client import config
from up2date_client import up2dateUtils
from up2date_client import up2dateErrors
from up2date_client import rpmUtils
from up2date_client import rpcServer

import genericSolveDep

from rhn import rpclib, xmlrpclib



#FIXME: split it it so we seperate the "pick the best of the options"
#       and the "get the options" stuff and then share "pick the best of the options" stuff
class RhnSolveDep(genericSolveDep.GenericSolveDep):
    def __init__(self):
        genericSolveDep.GenericSolveDep.__init__(self)
        
    def getSolutions(self, unknowns, progressCallback = None, msgCallback = None):
        s = rpcServer.getServer(refreshCallback=self.refreshCallback)
        try:
            tmpRetList = rpcServer.doCall(s.up2date.solveDependencies,
                                            up2dateAuth.getSystemId(),
                                            unknowns)
        except rpclib.Fault, f:
            if f.faultCode == -26:
                #raise RpmError(f.faultString + _(", depended on by %s") % unknowns)
                raise up2dateErrors.RpmError(f.faultString)
            else:
                 raise up2dateErrors.CommunicationError(f.faultString)


        self.retDict = {}
        for unknown in tmpRetList.keys():
            if len(tmpRetList[unknown]) == 0:
                continue
            solutions = tmpRetList[unknown]

            # solution at this point is just [n,v,r,e]
            # so we find all the packages of that nvre, download the headers
            # and walk over the headers looking for more exact matches
            for solution in solutions:
                deppkgs = []
                hdrlist = []
                p = solution
                if self.availListHash.has_key(tuple(p[:4])):
                    for i in self.availListHash[tuple(p[:4])]:
                        deppkgs.append(i)

                for i in deppkgs:
                    hdr = self.getHeader(i)
                    hdrlist.append(hdr)

                answerlist = []
                for hdr in hdrlist:
                    fullprovideslist = hdr[rpm.RPMTAG_PROVIDES]
                    if hdr[rpm.RPMTAG_FILENAMES] != None:
                        fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_FILENAMES]
                    if hdr[rpm.RPMTAG_DIRNAMES] != None:
                        fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_DIRNAMES]
                    for item in fullprovideslist:
                        if unknown == item:
                            answerlist.append(hdr)

                for a in answerlist:
                    epoch = a['epoch']
                    if epoch == None:
                        epoch = ""
                    for i in self.availListHash[(a['name'], a['version'], a['release'], "%s" % epoch)]:
                        #                    print "\nI ", i
                        # just use the right arches
                        if a['arch'] == i[4]:
#                            print "SOLVING %s with %s" % (unknown, i)
                            if not self.retDict.has_key(unknown):
                                self.retDict[unknown] = []
                            self.retDict[unknown].append(i)

    def getHeader(self, pkg,
                  msgCallback = None,
                  progressCallback = None ):
        self.repos = repoDirector.initRepoDirector()
        hdr, type = rpcServer.doCall(self.repos.getHeader, pkg,
                                     msgCallback = msgCallback,
                                     progressCallback = progressCallback)
        return hdr
        

class HttpGetSource(rpmSource.PackageSource):
    def __init__(self, server, proxyHost,
                 loginInfo = None, cacheObject = None):
        self.cfg = config.initUp2dateConfig()
        self.s = server
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self._loginInfo=up2dateAuth.loginInfo

    # we need to relogin if we get a an auth time out, plus we need to
    # create a new server object with that auth info
    def updateAuthInfo(self):
        li = up2dateAuth.updateLoginInfo()
        self._loginInfo=li
        serverSettings = ServerSettings()
        self.s = getGETServer(li, serverSettings)

    def _readFD(self, fd, filename, fileflags, pdLen, status, startpoint=0):
        # Open the storage file
        f = open(filename, fileflags)

        # seek to the start point, overwriting the last bits
        if pdLen and status != 200:
            f.seek(startpoint)

        while 1:
            chunk = fd.read(rpmSource.BUFFER_SIZE)
            l = len(chunk)
            if not l:
                break
            f.write(chunk)
            
        f.flush()
        # Rewind
        f.seek(0, 0)
        return f.read()
            

    def getHeader(self, package, msgCallback = None, progressCallback = None):
        hdr = None
        # package list format
        # 0        1        3       4     5     6      7
        # name, version, release, epoch, arch, size, channel

        filename = "%s-%s-%s.%s.hdr" % (package[0], package[1], package[2],
            package[4])
        channel = package[6]

        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        self.s.set_progress_callback(progressCallback,rpmSource.BUFFER_SIZE )
        
        fd = self.s.getPackageHeader(channel, filename)

        pkgname = "%s-%s-%s" % (package[0], package[1], package[2])
        if msgCallback:
            msgCallback(filename)

        buffer = fd.read()
        open(filePath, "w+").write(buffer)
        fd.close()

        hdr = rpmUtils.readHeaderBlob(buffer)
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache["%s-%s-%s.%s" % (hdr['name'],
                                       hdr['version'],
                                       hdr['release'],
                                       hdr['arch'])] = hdr
        return hdr

    
    def getPackage(self, package, msgCallback = None, progressCallback = None):
 #       print "gh 232423423423"
        filename = "%s-%s-%s.%s.rpm" % (package[0], package[1], package[2],
                                        package[4])

        partialDownloadPath = "%s/%s" % (self.cfg["storageDir"], filename)
        if os.access(partialDownloadPath, os.R_OK):
            pdLen = os.stat(partialDownloadPath)[6]
        else:
            pdLen = None

        self.s.set_transport_flags(allow_partial_content=1)

        startpoint = 0
        if pdLen:
            size = package[5]
            # trim off the last kb since it's more likely to
            # be trash on a reget
            startpoint = long(pdLen) - 1024
            
        channel = package[6]

        if msgCallback:
            msgCallback(filename)

#        print progressCallback
#        print "\nself.s", self.s, progressCallback
        self.s.set_progress_callback(progressCallback, rpmSource.BUFFER_SIZE )
        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        if pdLen:
            fd = self.s.getPackage(channel, filename, offset=startpoint)
        else:
            fd = self.s.getPackage(channel, filename)
         
        if pdLen:
            fflag = "r+"
        else:
            fflag = "w+"

        status = self.s.get_response_status()
        f = open(filePath, fflag)
        if pdLen and status != 200:
            f.seek(startpoint)
        f.write(fd.read())
        f.flush()
        f.close()

#        self._readFD(fd,filePath,fflag, pdLen, status, startpoint)
        
        fd.close()

        # verify that the file isnt corrupt, if it,
        # download it again in its entirety
        if not rpmUtils.checkRpmMd5(filePath):
            f = open(filePath, "w+")
            fd = self.s.getPackage(channel, filename)
            buffer = fd.read()
            f.write(buffer)
            f.close()
            fd.close()
        
        buffer = open(filePath, "r").read()    
        return buffer

    
    def getPackageSource(self, channel, package,
                         msgCallback = None, progressCallback = None):
        filename = package

        filePath = "%s/%s" % (self.cfg["storageDir"], filename)
        self.s.set_progress_callback(progressCallback,rpmSource.BUFFER_SIZE )
        fd = self.s.getPackageSource(channel['label'], filename)

        if msgCallback:
            msgCallback(package)

        channel = package[6]

        startpoint = 0
        pdLen = None
        fflag = "w+"
        status = self.s.get_response_status()
        buffer = self._readFD(fd, filePath, fflag, pdLen, status, startpoint)
        fd.close()
        return buffer
        

    def listPackages(self, channel,msgCallback = None, progressCallback = None):
        filePath = "%s/%s.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s.*" % (self.cfg["storageDir"], channel['label'])

        self.s.set_progress_callback(progressCallback)

        # FIXME: I still dont like the seemingly arbitrary fact that this
        # method returns a python structure, and all the other gets return
        # a file descriptor.
        list = self.s.listPackages(channel['label'], channel['version'])
        

        # do something to save it to disk.
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)

        return list

    def listAllPackages(self, channel,
                     msgCallback = None, progressCallback = None):
        filePath = "%s/%s-all.%s" % (self.cfg["storageDir"], channel['label'], channel['version'])
        # a glob used to find the old versions to cleanup
        globPattern = "%s/%s-all.*" % (self.cfg["storageDir"], channel['label'])

        self.s.set_progress_callback(progressCallback)

        # FIXME: I still dont like the seemingly arbitrary fact that this
        # method returns a python structure, and all the other gets return
        # a file descriptor.
        list = self.s.listAllPackages(channel['label'], channel['version'])
        

        # do something to save it to disk.
        rpmSourceUtils.saveListToDisk(list, filePath,globPattern)

        return list


    def getObsoletes(self, channel,
                     msgCallback = None, progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                            channel['label'])
        self.s.set_progress_callback(progressCallback)
        obsoletes = self.s.getObsoletes(channel['label'], channel['version'])
        
       
        rpmSourceUtils.saveListToDisk(obsoletes, filePath, globPattern)
        return obsoletes

def getGETServer(logininfo, serverSettings):
    server= rpcServer.RetryGETServer(serverSettings.serverList.server(),
                                     proxy = serverSettings.proxyUrl,
                                     username = serverSettings.proxyUser,
                                     password = serverSettings.proxyPassword,
                                     headers = logininfo)
    server.add_header("X-Up2date-Version", up2dateUtils.version())
    server.addServerList(serverSettings.serverList)
    return server


# containment class for handling server config info
class ServerSettings:
    def __init__(self):
        self.cfg = config.initUp2dateConfig()
        self.xmlrpcServerUrl = self.cfg["serverURL"]
        refreshServerList = 0
	if self.cfg["useNoSSLForPackages"]:
            self.httpServerUrls = self.cfg["noSSLServerURL"]
            refreshServerList = 1
	else:
	    self.httpServerUrls = self.cfg["serverURL"]

        if type(self.httpServerUrls) == type(""):
            self.httpServerUrls = [self.httpServerUrls]

        self.serverList = rpcServer.initServerList(self.httpServerUrls)
        # if the list of servers for packages and stuff is different,
        # refresh
        if refreshServerList:
            self.serverList.resetServerList(self.httpServerUrls)

        self.proxyUrl = None
        self.proxyUser = None
        self.proxyPassword = None
        
        if self.cfg["enableProxy"] and up2dateUtils.getProxySetting():
            self.proxyUrl = up2dateUtils.getProxySetting()
            if self.cfg["enableProxyAuth"]:
                if self.cfg["proxyUser"] and self.cfg["proxyPassword"]:
                    self.proxyPassword = self.cfg["proxyPassword"]
                    self.proxyUser = self.cfg["proxyUser"]
                    
    def settings(self):
        return self.xmlrpcServerUrl, self.httpServerUrls, \
               self.proxyUrl, self.proxyUser, self.proxyPassword

class Up2dateRepo(genericRepo.GenericRepo):
    def __init__(self):
        self.login = None
        genericRepo.GenericRepo.__init__(self)
        self.cfg = config.initUp2dateConfig()
        li = up2dateAuth.getLoginInfo()

        serverSettings = ServerSettings()
        self.httpServer = getGETServer(li,
                                       serverSettings)
        localHeaderCache = rpmSource.HeaderCache()
        self.gds = HttpGetSource(self.httpServer, None)
        self.hds = rpmSource.DiskCache()
        self.lds = rpmSource.LocalDisk()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
#        localHeaderCache = rpmSource.HeaderCache()
        self.psc.headerCache = localHeaderCache

        # header needs to be a shared object between several
        # different classes and isntances, so it's a bit weird.
        # should maybe reimplement it as class level storage
        # bits and shared onjects...

        
        self.sources = {'listPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'get', 'object':self.gds}],
                        'getPackage':[{'name':'localdisk','object':self.lds},
                                      {'name':'diskcache', 'object':self.hds},
                                      {'name':'get', 'object': self.gds},
                                     ],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hds},
                                     {'name':'get', 'object': self.gds}
                                     ],
                        'getPackageSource':[{'name':'localdisk','object':self.lds},
                                            {'name':'diskcache', 'object':self.hds},
                                            {'name':'get', 'object': self.gds},
                                     ],
                        }

    def updateAuthInfo(self):
        self.gds.updateAuthInfo()

        
def register(rd):
    up2dateRepo = Up2dateRepo()
    rd.handlers['up2date']=up2dateRepo
    rhnSolveDep = RhnSolveDep()
    rd.depSolveHandlers['up2date'] = rhnSolveDep
    
    
    



