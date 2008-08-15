#!/usr/bin/python


import os
import re
import sys
import time
import glob
import string
import fnmatch
import time  #remove

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import rpmSource
from up2date_client import rpmSourceUtils
from up2date_client import rhnChannel
from up2date_client import repoDirector
from up2date_client import config
from up2date_client import rpcServer
from up2date_client import rpmUtils
from up2date_client import up2dateUtils
from up2date_client import transaction

import genericRepo
import genericSolveDep

class DirSolveDep(genericSolveDep.SolveByHeadersSolveDep):
    def __init__(self):
        genericSolveDep.SolveByHeadersSolveDep.__init__(self)
        self.type = "dir"



#from http://aspn.activestate.com/ASPN/Cookbook/Python/Recipe/52664
def walk( root, recurse=0, pattern='*', return_folders=0 ):
    # initialize
    result = []
    
    # must have at least root folder
    try:
        names = os.listdir(root)
    except os.error:
        return result

    # expand pattern
    pattern = pattern or '*'
    pat_list = string.splitfields( pattern , ';' )
    
    # check each file
    for name in names:
        fullname = os.path.normpath(os.path.join(root, name))

        # grab if it matches our pattern and entry type
        for pat in pat_list:
            if fnmatch.fnmatch(name, pat):
                if os.path.isfile(fullname) or (return_folders and os.path.isdir(fullname)):
                    result.append(fullname)
                continue

        # recursively scan other folders, appending results
        if recurse:
            if os.path.isdir(fullname) and not os.path.islink(fullname):
                result = result + walk( fullname, recurse, pattern, return_folders )

    return result



class DirRepoSource(rpmSource.PackageSource):
    def __init__(self, proxyHost=None,
                 loginInfo=None, cacheObject=None):
        self.cfg = config.initUp2dateConfig()
        rpmSource.PackageSource.__init__(self, cacheObject = cacheObject)
        self.headerCache = cacheObject
        self.obsList = []

        try:
            cmd = os.popen('uname -m')
            self._arch = cmd.read().strip('\n')
        except IOError:
            self._arch = 'unknown'

    def __getHeader(self, path):
        fd = os.open(path, os.R_OK)
        ts = transaction.initReadOnlyTransaction()
        
        try:
            hdr = ts.hdrFromFdno(fd)
        except:
            os.close(fd)
            return None
        os.close(fd)
        return hdr
   
    def _is_compatible_arch(self, arch):
        if rpm.archscore(arch) == 0:
            # Itanium special casing.
            if self._arch == 'ia64' and re.match('i.86', arch):
                return True
            else:
                return False
        else:
            return True

    def _get_all_packages_dict(self, path, label):
        rpmpaths = walk(path, recurse=0, pattern="*.rpm", return_folders=0)

        pkgsDict = {}
        for rpmpath in rpmpaths:
            filename = os.path.basename(rpmpath)
            bits = string.split(filename, ".")
            arch = bits[-2]
           
            if not self._is_compatible_arch(arch):
                continue

            # might as well collect the filesize 
            hdrBuf = self.__getHeader(rpmpath)
            # busted package of some sort, skip it
            if hdrBuf == None:
                continue
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())
            size = os.stat(rpmpath)[6]
            
            epoch = hdr['epoch']
            if epoch == None:
                epoch = ""
            else:
                epoch = str(epoch)
            
            pkg = [hdr['name'], hdr['version'], hdr['release'], epoch,
                hdr['arch'], size, label, rpmpath]

            # group packages by nvre and store the different arches in a list
            pkgNvre = tuple(pkg[:4])
            if not pkgsDict.has_key(pkgNvre):
                pkgsDict[pkgNvre] = []
            pkgsDict[pkgNvre].append(pkg)

        return pkgsDict

    def _package_list_from_dict(self, pkgsDict, storage_dir, label, name_suffix,
        version):
        pkgList = []
        names = pkgsDict.keys()
        names.sort()
        for name in names:
            pkgs = pkgsDict[name]
            for pkg in pkgs:
                pkgList.append(pkg)

        # nowi we have the package list, convert it to xmlrpc style
        # presentation and dump it
        filePath = "%s/%s%s.%s" % (storage_dir, label, name_suffix, version)
        fileGlobPattern = "%s/%s.*" % (storage_dir, label)
        
        rpmSourceUtils.saveListToDisk(pkgList, filePath, fileGlobPattern)

        return pkgList


    def listPackages(self, channel, msgCallback = None,
        progressCallback = None):
        pkgsDict = self._get_all_packages_dict(channel['path'],
            channel['label'])
            
        latestPkgsDict = {}
        for pkgNvre in pkgsDict.keys():
            # first version of this package, continue
            pkgName = pkgNvre[0]
            tupNvre = tuple(pkgNvre)
            if not latestPkgsDict.has_key(pkgName):
                latestPkgsDict[pkgName] = pkgsDict[tupNvre]
                continue


            ret = up2dateUtils.comparePackages(latestPkgsDict[pkgName][0],
                list(pkgNvre))
            if ret > 0:
                # don't care, we already have a better version
                continue
            if ret < 0:
                # Better version
                latestPkgsDict[pkgName] = pkgsDict[pkgNvre]
                continue
            # if it's 0, we already have it

        pkgList = self._package_list_from_dict(latestPkgsDict,
            self.cfg["storageDir"], channel['label'], "", channel['version'])

        # since were talking local file, and we are already
        # loading them up and poking at the headers, lets figure
        # out the obsoletes stuff now too while were at it
        self.obsList = []

        for pkg in pkgList:
            rpmpath = pkg[7]
            hdrBuf = self.__getHeader(rpmpath)
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())

            
            # look for header info
            if not hdr['obsoletes']:
                continue
            
            obs = up2dateUtils.genObsoleteTupleFromHdr(hdr)
            if obs:
                self.obsList = self.obsList + obs

        return pkgList

    def listAllPackages(self, channel, msgCallback = None,
        progressCallback = None):
        pkgs_dict = self._get_all_packages_dict(channel['path'],
            channel['label'])
        pkg_list = self._package_list_from_dict(pkgs_dict,
            self.cfg["storageDir"], channel['label'], "-all", 
            channel['version'])

        return pkg_list
   
    def getObsoletes(self, channel, msgCallback = None, progressCallback = None):
        filePath = "%s/%s-obsoletes.%s" % (self.cfg["storageDir"],
                                           channel['label'], channel['version'])
        globPattern = "%s/%s-obsoletes.*" % (self.cfg["storageDir"],
                                             channel['label'])


        # if we already founf the list, just statsh it. However it
        # is possible for it to not exist (ie, user just delets the obsList
        # from the cache, but since the package list exists we never hit the
        # above code path. A FIXME
        if self.obsList:
            self.obsList.sort(lambda a, b: cmp(a[0], b[0]))
            rpmSourceUtils.saveListToDisk(self.obsList, filePath, globPattern)
            if progressCallback:
                progressCallback(1,1)
        else:
            if progressCallback:
                progressCallback(1,1)

        if self.obsList:
            return self.obsList
        return []
            

    
    def __saveHeader(self, hdr):
        tmp = rpmUtils.readHeaderBlob(hdr.unload())
        rpmSourceUtils.saveHeader(tmp)

    def getHeader(self, pkg, msgCallback = None, progressCallback = None):
        channels = rhnChannel.getChannels()
        channel = channels.getByName(pkg[6])
        
        #filename = "%s/%s-%s-%s.%s.rpm" % (channel['path'],  pkg[0], pkg[1],
        #                                   pkg[2], pkg[4])
        filename = pkg[7]

        # package doesnt exist
        if not os.access(filename, os.R_OK):
            return None
        hdrBuf = self.__getHeader(filename)
        try:
            hdr = rpmUtils.readHeaderBlob(hdrBuf.unload())
        except:
            return None
        rpmSourceUtils.saveHeader(hdr)
        self.headerCache[up2dateUtils.pkgToStringArch(pkg)] = hdr
        self.__saveHeader(hdr)
        return hdr

            
    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        pkgFileName = "%s-%s-%s.%s.rpm" % (pkg[0], pkg[1], pkg[2],
                                        pkg[4])
        channels = rhnChannel.getChannels()
        channel = channels.getByLabel(pkg[6])
#        if msgCallback:
#            msgCallback(pkgFileName)

        storageFilePath = "%s/%s" % (self.cfg["storageDir"], pkgFileName)


        # symlink the file from /var/spool/up2date to whereever it is...
#        fileName = "%s/%s" % (channel['path'], pkgFileName)
        fileName = pkg[7]
        if (channel['path'] != self.cfg['storageDir']):
            try:
                os.remove(storageFilePath)
            except OSError:
                pass
            os.symlink(fileName, storageFilePath)

        if progressCallback:
            progressCallback(1,1)
        return 1


    # FIXME: need to add a path to SRPMS as well
    def getPackageSource(self, channel, srcpkg,
                         msgCallback = None, progressCallback = None):
        fileName = "%s/%s" % (channel['srpmpath'], srcpkg)
        if (channel['path'] != self.cfg['storageDir']):
            try:
                os.remove(fileName)
            except OSError:
                pass
            if msgCallback:
                msgCallback(fileName)
                os.symlink(tmpFileNames[0], fileName)
        
        return 1


class DirRepo(genericRepo.GenericRepo):
    def __init__(self):
        genericRepo.GenericRepo.__init__(self)
        self.hds = rpmSource.DiskCache()
        self.ds = DirRepoSource()
        localHeaderCache =  rpmSource.HeaderCache()
        self.hldc = rpmSource.LocalDisk()
        self.hcs = rpmSource.HeaderMemoryCache(cacheObject = localHeaderCache)
        self.hds = rpmSource.DiskCache()

        #FIXME: this functionality collides with the localDisk/-k stuff
        # a bit, need to figure out what to keep/toss
        self.hldc = rpmSource.LocalDisk()
        self.psc.headerCache = localHeaderCache

        # FIMXE: we need a way to figure out when a cached package list
        # is stale

        self.sources = {'listPackages':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'dir', 'object':self.ds},
                                        ],
                        'getObsoletes':[{'name':'diskcache', 'object':self.hds},
                                        {'name':'dir', 'object':self.ds},
                                        ],
                        'getPackage':[{'name':'localdisk','object':self.hldc},
                                       {'name':'diskcache', 'object':self.hds},
                                       {'name':'dir', 'object':self.ds},
                                       ],
                        'getHeader':[{'name':'memcache', 'object': self.hcs},
                                     {'name':'diskcache', 'object':self.hds},
                                     {'name':'localdisk', 'object':self.hldc},
                                     {'name':'dir', 'object':self.ds},
                                     ],
                        'getPackageSource':[{'name':'localdisk','object':self.hldc},
                                             {'name':'diskcache', 'object':self.hds},
                                             {'name':'dir', 'object':self.ds},
                                             ],
                        'listAllPackages':[{'name':'diskcache', 'object':self.hds},
                                           {'name':'dir', 'object':self.ds}
                                           ]
                        }

    def updateAuthInfo(self):
        pass

def register(rd):
    dirRepo = DirRepo()
    rd.handlers['dir'] = dirRepo
    dirSolveDep = DirSolveDep()
    rd.depSolveHandlers['dir'] = dirSolveDep
        
