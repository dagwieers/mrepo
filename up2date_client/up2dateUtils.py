#/usr/bin/python
# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Preston Brown <pbrown@redhat.com>
#         Adrian Likins <alikins@redhat.com>
#
"""utility functions for up2date"""

import re
import os
import sys
import time
import rpm
import string

# Python >= 2.5
try:
    from hashlib import md5 as md5hash
# Python <= 2.4
except ImportError:
    from md5 import new as md5hash

sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")
import rpmUtils
import up2dateErrors
import transaction
import config


from rhpl.translate import _, N_

def rpmFlagsToOperator(flags):
    flags = flags & 0xFF
    buf = ""
    if flags != 0:
        if flags & rpm.RPMSENSE_LESS:
            buf = buf + "<"
        if flags & rpm.RPMSENSE_GREATER:
            buf = buf + ">"
        if flags & rpm.RPMSENSE_EQUAL:
            buf = buf + "="
        if flags & rpm.RPMSENSE_SERIAL:
            buf = buf + "S"
    return buf

def getPackageSearchPath():
    dir_list = []
    cfg = config.initUp2dateConfig()
    dir_list.append(cfg["storageDir"])

    dir_string = cfg["packageDir"]
    if dir_string:
        paths = string.split(dir_string, ':')
        fullpaths = []
        for path in paths:
            fullpath = os.path.normpath(os.path.abspath(os.path.expanduser(path)))
            fullpaths.append(fullpath)
    	dir_list = dir_list + fullpaths
    return dir_list

def pkgToString(pkg):
    return "%s-%s-%s" % (pkg[0], pkg[1], pkg[2])

def pkgToStringArch(pkg):
    return "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])

def pkglistToString(pkgs):
    packages = "("
    for pkg in pkgs:
	packages = packages + pkgToString(pkg) + ","
    packages = packages + ")"
    return packages

def restartUp2date():
    print _("Restarting up2date")
    args = sys.argv[:]
    return_code = os.spawnvp(os.P_WAIT, sys.argv[0], args)
    sys.exit(return_code)

def comparePackagesArch(pkg1, pkg2):
    arch1 = pkg1[4]
    arch2 = pkg2[4]

    score1 = rpm.archscore(arch1)
    score2 = rpm.archscore(arch2)

    if score1 > score2:
        return 1
    if score1 < score2:
        return -1
    if score1 == score2:
        return 0

# compare two RPM packages
def comparePackages(pkgLabel1, pkgLabel2):
    version1 = pkgLabel1[1]
    release1 = pkgLabel1[2]
    epoch1 = pkgLabel1[3]
    version2 = pkgLabel2[1]
    release2 = pkgLabel2[2]
    epoch2 = pkgLabel2[3]

    if epoch1 == "" or epoch1 == 0 or epoch1 == "0":
        epoch1 = None
    else:
        epoch1 = "%s" % epoch1
        
    if epoch2 == "" or epoch2 == 0 or epoch2 == "0":
            epoch2 = None
    else:
        epoch2 = "%s" % epoch2
        
    return rpm.labelCompare((epoch1, version1, release1),
                            (epoch2, version2, release2))
    

def parseObsoleteVersion(ver):
    s = ver
    epoch = ""
    if string.find(s, ":") >= 0:
        arr = string.split(s, ":", 1)
        epoch = arr[0]
        s = arr[1]
    release = "0"
    if string.find(s, '-') >= 0:
        arr = string.split(s, "-", 1)
        release = arr[1]
        s = arr[0]
    return s, release, epoch


def cmp2rpmSense(value):
    if value < 0:
        return rpm.RPMSENSE_LESS
    if value > 0:
        return rpm.RPMSENSE_GREATER
    return rpm.RPMSENSE_EQUAL

# see if a package is obsoleted by a given
# obsolete version and sense
def isObsoleted(obs, pkg, package=None):
    # if the obsoleting package and the package
    # to be obsoleted are different arches, it doesnt count
    if package:
        if pkg[4] != "noarch" and package[4] != "noarch":
            if pkg[4] != package[4]:
                return 0
    (n,v,r,e,a,obsName, obsVersion,obsSense) = obs
    if obsSense == "0":
        return 1
    candidate = (pkg[0], pkg[1], pkg[2], pkg[3])
    vv, rr, ee = parseObsoleteVersion(obsVersion)
    obsCandidate = (obsName, vv, rr, ee)
    ret = comparePackages(candidate, obsCandidate)
    op = cmp2rpmSense(ret)
    if op & int(obsSense):
        return 1

    return 0
    
    
    

def md5sum(fileName):
    hashvalue = md5hash()
    
    try:
        f = open(fileName, "r")
    except:
        return ""

    fData = f.read()
    hashvalue.update(fData)
    del fData
    f.close()
    
    hexvalue = string.hexdigits
    md5res = ""
    for c in hashvalue.digest():
        i = ord(c)
        md5res = md5res + hexvalue[(i >> 4) & 0xF] + hexvalue[i & 0xf]

    return md5res

# return a glob for your particular architecture.
def archGlob():
    if re.search("i.86", os.uname()[4]):
        return "i?86"
    elif re.search("sparc", os.uname()[4]):
        return "sparc*"
    else:
        return os.uname()[4]

def getProxySetting():
    cfg = config.initUp2dateConfig()
    proxy = None
    proxyHost = cfg["httpProxy"]
    # legacy for backwards compat
    if proxyHost == "":
        try:
            proxyHost = cfg["pkgProxy"]
        except:
            proxyHost = None

    if proxyHost:
        if proxyHost[:7] == "http://":
            proxy = proxyHost[7:]
        else:
            proxy = proxyHost

    return proxy

def getOSVersionAndRelease():
    cfg = config.initUp2dateConfig()
    ts = transaction.initReadOnlyTransaction()
    for h in ts.dbMatch('Providename', "redhat-release"):
        if cfg["versionOverride"]:
            version = cfg["versionOverride"]
        else:
            version = h['version']

        releaseVersion = (h['name'], version)
        return releaseVersion
    else:
       raise up2dateErrors.RpmError(
           "Could not determine what version of Red Hat Linux you "\
           "are running.\nIf you get this error, try running \n\n"\
           "\t\trpm --rebuilddb\n\n")



def getVersion():
    release, version = getOSVersionAndRelease()

    return version

def getOSRelease():
    release, version = getOSVersionAndRelease()
    return release

def getArch():
    if not os.access("/etc/rpm/platform", os.R_OK):
        return os.uname()[4]

    fd = open("/etc/rpm/platform", "r")
    platform = string.strip(fd.read())

    return platform

# FIXME: and again, ripped out of r-c-packages
# FIXME: ripped right out of anaconda, belongs in rhpl
def getUnameArch():
    arch = os.uname()[4]
    if (len (arch) == 4 and arch[0] == 'i' and
        arch[2:4] == "86"):
        arch = "i386"
                                                                                
    if arch == "sparc64":
        arch = "sparc"
                                                                                
    if arch == "s390x":
        arch = "s390"
                                                                                
    return arch



def version():
    # substituted to the real version by the Makefile at installation time.
    return "4.5.5-8.el3"

def pprint_pkglist(pkglist):
    if type(pkglist) == type([]):
        foo = map(lambda a : "%s-%s-%s" % (a[0],a[1],a[2]), pkglist)
    else:
        foo = "%s-%s-%s" % (pkglist[0], pkglist[1], pkglist[2])
    return foo

def genObsoleteTupleFromHdr(hdr):
    epoch = hdr['epoch']
    if epoch == None:
        epoch = ""
    # I think this is right, check with misa
    obsname =  hdr['obsoletename']
    obsvers = hdr['obsoleteversion']
    obsflags = hdr['obsoleteflags']
    name = hdr['name']
    version = hdr['version']
    release =  hdr['release']
    arch = hdr['arch']

    if type(obsname) == type([]) and len(obsname) > 1:
        obs = []
        for index in range(len(obsname)):
            obs.append([name, version, release, epoch, arch,
                   obsname[index], obsvers[index], obsflags[index]])
        return obs
    else:
        vers = ""
        if obsvers:
            vers = obsvers[0]
        flags = 0
        if obsflags:
	    if type(obsflags) == type([]):
               flags = obsflags[0]
	    else:
	       flags = obsflags	
        obs = [name, version, release, epoch, arch,
               obsname[0], vers, flags]
        return [obs]
    return None


def freeDiskSpace():
    cfg = config.initUp2dateConfig()
    import statvfs

    dfInfo = os.statvfs(cfg["storageDir"])
    return long(dfInfo[statvfs.F_BAVAIL]) * (dfInfo[statvfs.F_BSIZE])

# file used to keep track of the next time rhn_check 
# is allowed to update the package list on the server
LAST_UPDATE_FILE="/var/lib/up2date/dbtimestamp"
 
# the package DB expected to change on each RPM list change
#dbpath = "/var/lib/rpm"
#if cfg['dbpath']:
#    dbpath = cfg['dbpath']
#RPM_PACKAGE_FILE="%s/Packages" % dbpath 

def touchTimeStamp():
    try:
        file_d = open(LAST_UPDATE_FILE, "w+")
        file_d.close()
    except:
        return (0, "unable to open the timestamp file", {})
    # Never update the package list more than once every hour.
    t = time.time()
    try:
        os.utime(LAST_UPDATE_FILE, (t, t))

    except:
        return (0, "unable to set the time stamp on the time stamp file %s" % LAST_UPDATE_FILE, {})
