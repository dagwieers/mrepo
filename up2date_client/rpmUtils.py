#!/usr/bin/python
# some high level utility stuff for rpm handling

# Client code for Update Agent
# Copyright (c) 1999-2002 Red Hat, Inc.  Distributed under GPL.
#
# Author: Preston Brown <pbrown@redhat.com>
#         Adrian Likins <alikins@redhat.com>
#


#
#  FIXME: Some exceptions in here are currently in up2date.py
#         fix by moving to up2dateErrors.py and importing from there
#
#
        
import os
import sys
import re
import struct
        
import up2dateErrors
import up2dateUtils
import config
import rpm
import fnmatch
import gpgUtils
import transaction
import string


from rhpl.translate import _, N_
from up2date_client import up2dateLog            

# mainly here to make conflicts resolution cleaner
def findDepLocal(ts, dep):
    if dep[0] == '/':
        tagN = 'Basenames'
    else:   
        tagN = 'Providename'
    for h in ts.dbMatch(tagN, dep):
        return h
    else:   
        return None

# conv wrapper for gettting index of a installed package
# ie, for removing it
def installedHeaderIndexByPkg(pkg):
    return installedHeaderIndex(name=pkg[0],
                                version=pkg[1],
                                release=pkg[2],
                                arch=pkg[4])


# um, this doesnt actually seem to work with epoch
# becuase of some rpm issues (it wants a None, but
# doesnt except a none. Workaround by just not
# matching on epoch, the rest should be specific enough
def installedHeaderByPkg(pkg):
    return installedHeaderByKeyword(name=pkg[0],
                           version=pkg[1],
                           release=pkg[2],
                           arch=pkg[4])

# call like installedHeaderIndex(name="kernel", version="12312")
def installedHeaderIndex(**kwargs):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch()
    for keyword in kwargs.keys():
        mi.pattern(keyword, rpm.RPMMIRE_GLOB, kwargs[keyword])
        
    # we really shouldnt be getting multiples here, but what the heck
    instanceList = []
    for h in mi:
        instance = mi.instance()
        instanceList.append(instance)

    return instanceList

# just cause this is such a potentially useful looking method...
def installedHeaderByKeyword(**kwargs):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch()
    for keyword in kwargs.keys():
        mi.pattern(keyword, rpm.RPMMIRE_GLOB, kwargs[keyword])
    # we really shouldnt be getting multiples here, but what the heck
    headerList = []
    for h in mi:
        #print "%s-%s-%s.%s" % ( h['name'], h['version'], h['release'], h['arch'])
        
        headerList.append(h)

    return headerList

    
    
    
        
def installedHeadersNameVersion(pkgName,version):
    _ts = transaction.initReadOnlyTransaction()
    mi = _ts.dbMatch('Name', pkgName)
    for h in mi:
        if h['version'] == version:
            return h
    return None 

def installedHeader(someName, ts):
    if type(someName) == type([]):
        pkgName = someName[0]
    else:           
        pkgName = someName

    mi = ts.dbMatch('Name', pkgName)
    if not mi:          # not found
        return None
    for h in ts.dbMatch('Name', pkgName):
        name = h['name']
        epoch = h['epoch']
        if epoch == None:
            epoch = ""
        version = h['version']
        release = h['release']
        if type(someName) == type([]):
            if (pkgName == name and
                pkgName[2] == version and
                pkgName[3] == release and
                pkgName[4] == epoch):
                break
        else:
            if (pkgName == name):
                break
    else:
	return None
    return h

global obsHash
obsHash = None
def getInstalledObsoletes(msgCallback = None, progressCallback = None, getArch = None):
    _ts = transaction.initReadOnlyTransaction()
    obs_list = []
    global obsHash 

    if obsHash:
        return obsHash
    obsHash = {}
    
    count = 0
    total = 0
    for h in _ts.dbMatch():
        if h == None:
            break
        count = count + 1

    total = count
    
    for h in _ts.dbMatch():
        if h == None:
            break
        obsoletes = h['obsoletes']
        name = h['name']
        version = h['version']
        release = h['release']
        
        nvr = "%s-%s-%s" % (name, version, release)
        if obsoletes:
            obs_list.append((nvr, obsoletes))

        if progressCallback != None:
            progressCallback(count, total)
        count = count + 1
    
    for nvr,obs in obs_list:
        for ob in obs:
            if not obsHash.has_key(ob):
                obsHash[ob] = []
            obsHash[ob].append(nvr)

    
    return obsHash


# check to see if a new file has a different MD5 sum
# from the package already on disk, and if true, if
# the on-disk file has been modified.
# this is a lot of args, but it helps...
def checkModified(index, fileNames, fileMD5s,installedFileNames,installedFileMD5s):
    ret = 0
    fileName = fileNames[index]

    #print "fileMD5s: %s: " % fileMD5s
    #print "installedFileMD5s: %s" % installedFileMD5s
    #this is a little ugly, but the order of the filelist in the old and the new
    # pacakges arent the same.
    for j in range(len(installedFileNames)):
        if (installedFileNames[j] == fileName):
            if installedFileMD5s[j] == fileMD5s[index]:
                # the md5 of the file in the local db  is the same as the one in the
                # incoming package, so skip the rest of the check and return 0
                continue
	    # grrr, symlinks marked as config files pointing to dirs are baaad, okay?
	    if not os.path.isdir(fileName):
            	if installedFileMD5s[j] != up2dateUtils.md5sum(fileName):
                    # the local file is different than the file in the local db
                    ret = 1
            	else:
                    # not changed on disk
                    pass
            break
    return ret


def checkHeaderForFileConfigExcludes(h,package,ts):
    fflag = 0

    cfg = config.initUp2dateConfig()
    # might as well just do this once...
    fileNames = h['filenames'] or []
    fileMD5s = h['filemd5s'] or []
    fileFlags = h['fileflags'] or []


    installedHdr = installedHeader(h['name'],ts)
    if not installedHdr:
        #throw a fault? should this happen?
        return None
        
    installedFileNames = installedHdr['filenames'] or []
    installedFileMD5s = installedHdr['filemd5s'] or []

    


    #    print "installedFileMD5s: %s" % installedFileMD5s

    removedList = []
    if cfg["forceInstall"]:
        return None

    # shrug, the apt headers dont have this, not much
    # we can do about it... Kind of odd considering how
    # paranoid apt is supposed to be about breaking configs...
    if not fileMD5s:
        return None

    if not fileFlags:
        return None

    fileSkipList = cfg["fileSkipList"]
    # bleah, have to use the index here because
    # of rpm's storing of filenames and their md5sums in parallel lists
    for f_i in range(len(fileNames)):
        # code to see if we want to disable this
        for pattern in fileSkipList:
            
            if fnmatch.fnmatch(fileNames[f_i],pattern):
                # got to get a better string to use here
                removedList.append((package, _("File Name/pattern")))
                fflag = 1
                break
            # if we found a matching file, no need to
            # examine the rest in this package         
            if fflag:
                break

    configFilesToIgnore = cfg["configFilesToIgnore"] or []

    # cfg reads are a little heavier in this code base, so
    # might as well avoid doing them for every single file
    noReplaceConfig = cfg["noReplaceConfig"]
    for f_i in range(len(fileNames)):
        # Deal with config files
        if noReplaceConfig:
            # check for files that are config files, but skips those that
            # arent going to be replaced anyway
            # (1 << 4) == rpm.RPMFILE_NOREPLACE if it existed
            if fileFlags[f_i] & rpm.RPMFILE_CONFIG and not \
               fileFlags[f_i] & (1 << 4):
                if fileNames[f_i] not in configFilesToIgnore:
                    # check if config file and if so, if modified
                    if checkModified(f_i, fileNames, fileMD5s,
                                     installedFileNames, installedFileMD5s):
                        removedList.append((package, _("Config modified")))
                        fflag = 1
                        break

        if fflag:
            break     

    if len(removedList):
        return removedList
    else:
        return None

def checkRpmMd5(fileName):
    _ts = transaction.initReadOnlyTransaction()
    # XXX Verify only header+payload MD5 with f*cked up contrapositive logic
    _ts.pushVSFlags(~(rpm.RPMVSF_NOMD5|rpm.RPMVSF_NEEDPAYLOAD))
    
    fdno = os.open(fileName, os.O_RDONLY)
    try:
        h = _ts.hdrFromFdno(fdno)
    except rpm.error, e:
        _ts.popVSFlags()
        return 0
    os.close(fdno)
    _ts.popVSFlags()
    return 1

# JBJ: there's an rpmlib internal string that's probably more what you want.
# JBJ: You might have multiple rpm packages installed ...
def getRpmVersion():
    _ts = transaction.initReadOnlyTransaction()
    for h in _ts.dbMatch('Providename', "rpm"):
        version = ("rpm", h['version'], h['release'], h['epoch'])
        return version
    else:
        raise up2dateErrors.RpmError("Couldn't determine what version of rpm you are running.\nIf you get this error, try running \n\n\t\trpm --rebuilddb\n\n")



#rpm_version = getRpmVersion()
def getGPGflags():
    cfg = config.initUp2dateConfig()
    keyring_relocatable = 0
    rpm_version = getRpmVersion()
    if up2dateUtils.comparePackages(rpm_version, ("rpm", "4.0.4", "0", None)) >= 0:
        keyring_relocatable = 1

    if keyring_relocatable and cfg["gpgKeyRing"]:
        gpg_flags = "--homedir %s --no-default-keyring --keyring %s" % (gpgUtils.gpg_home_dir, cfg["gpgKeyRing"])
    else:
        gpg_flags = "--homedir %s" % gpgUtils.gpg_home_dir
    return gpg_flags


# given a list of package labels, run rpm -V on them
# and return a dict keyed off that data
def verifyPackages(packages):
    data = {}
    missing_packages = []                                                                            
    # data structure is keyed off package
    # label, with value being an array of each
    # line of the output from -V


    retlist = []
    for package in packages:
        (n,v,r,e,a) = package
        # we have to have at least name...

        # Note: we cant reliable match on epoch, so just
        # skip it... two packages that only diff by epoch is
        # way broken anyway
        name = version = release = arch = None
        if n != "":
            name = n
        if v != "":
            version = v
        if r != "":
            release = r
        if a != "":
            arch = a

        keywords = {}
        for token, value  in (("name", name),
                              ("version", version),
                              ("release",release),
#                              ("epoch",epoch),
                              ("arch", arch)):
            if value != None:
                keywords[token] = value

        headers = installedHeaderByKeyword(**keywords)
	if len(headers) == 0:            
	    missing_packages.append(package)

        for header in headers:
            epoch = header['epoch']
            if epoch == None:
                epoch = ""
            # gpg-pubkey "packages" can have an arch of None, see bz #162701
            h_arch = header["arch"] 
            if h_arch == None:
                h_arch = ""
                
            pkg = (header['name'], header['version'],
                   header['release'], epoch,
                   h_arch)

            # dont include arch in the label if it's a None arch, #162701
            if pkg[4] == "":
                packageLabel = "%s-%s-%s" % (pkg[0], pkg[1], pkg[2])
            else:
                packageLabel = "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])
                
            verifystring = "/usr/bin/rpmverify -V %s" % packageLabel
                                                                                
            fd = os.popen(verifystring)
            res = fd.readlines()
            fd.close()
                                                                                
            reslist = []
            for line in res:
                reslist.append(string.strip(line))
            retlist.append([pkg, reslist])

    return retlist, missing_packages


# run the equiv of `rpm -Va`. It aint gonna
# be fast, but...
def verifyAllPackages():
    data = {}

    packages = getInstalledPackageList(getArch=1)

    ret,missing_packages =  verifyPackages(packages)
    return ret

def rpmCallback(what, amount, total, key, cb):
    if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
        pass
        #fd = os.open(key, os.O_RDONLY)
        #return fd
    elif what == rpm.RPMCALLBACK_INST_START:
        pass
    elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
        print
    elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
        if cb:
            cb(amount, total)
        else:
            print "transaction %.5s%% done\r" % ((float(amount) / total) * 100),
    elif what == rpm.RPMCALLBACK_INST_PROGRESS:
        print "installation %.5s%% done\r" % ((float(amount) / total) * 100),

    if (rpm.__dict__.has_key("RPMCALLBACK_UNPACK_ERROR")):
        if ((what == rpm.RPMCALLBACK_UNPACK_ERROR) or
                   (what == rpm.RPMCALLBACK_CPIO_ERROR)):
            pkg = "%s-%s-%s" % (key[rpm.RPMTAG_NAME],
                                key[rpm.RPMTAG_VERSION],
                                key[rpm.RPMTAG_RELEASE])

            raise up2dateErrors.RpmInstallError, "There was a fatal error installing a package", pkg



    
#FIXME: this looks like a good candidate for caching, since it takes a second
# or two to run, and I can call it a couple of times
def getInstalledPackageList(msgCallback = None, progressCallback = None,
                            getArch=None, getInfo = None):
    pkg_list = []

    
    if msgCallback != None:
        msgCallback(_("Getting list of packages installed on the system"))
 
    _ts = transaction.initReadOnlyTransaction()   
    count = 0
    total = 0
    
    for h in _ts.dbMatch():
        if h == None:
            break
        count = count + 1
    
    total = count
    
    count = 0
    for h in _ts.dbMatch():
        if h == None:
            break
        name = h['name']
        epoch = h['epoch']
        if epoch == None:
            epoch = ""
        version = h['version']
        release = h['release']
        if getArch:
            arch = h['arch']
            # the arch on gpg-pubkeys is "None"...
            if arch:
                pkg_list.append([name, version, release, epoch, arch])
        elif getInfo:
            arch = h['arch']
            cookie = h['cookie']
            if arch and cookie:
                pkg_list.append([name, version, release, epoch, arch, cookie])
        else:
            pkg_list.append([name, version, release, epoch])

        
        if progressCallback != None:
            progressCallback(count, total)
        count = count + 1
    
    pkg_list.sort()
    return pkg_list

def runTransaction(ts, rpmCallback, transdir=None):
    cfg = config.initUp2dateConfig()
    if transdir == None:
        transdir = cfg['storageDir']
    deps = ts.check()
    if deps:
        raise up2dateErrors.DependencyError(_(
            "Dependencies should have already been resolved, "\
            "but they are not."), deps)
    rc = ts.run(rpmCallback, transdir)
    if rc:
        errors = "\n"
        for e in rc:
            try:
                errors = errors + e[1] + "\n"
            except:
                errors = errors + str(e) + "\n"
        raise up2dateErrors.TransactionError(_(
            "Failed running transaction of  packages: %s") % errors, deps=rc)
    elif type(rc) == type([]) and not len(rc):
        # let the user know whats wrong
        log = up2dateLog.initLog()
        log.log_me("Failed running rpm transaction - %pre %pro failure ?.")
        raise up2dateErrors.RpmError(_("Failed running rpm transaction"))

def readHeader(filename):
    if not os.access(filename, os.R_OK):
        return None
    blob = open(filename, "r").read()
#    print "reading blob for %s" % filename
    return readHeaderBlob(blob)

def readHeaderBlob(blob, filename=None):
    # Read two unsigned int32
    #print "blob: %s" % blob

#FIXME: for some reason, this fails alot
# not, but with current rpm, we dont really
# need it that much...
#    i0, i1 = struct.unpack("!2I", blob[:8])
#    if len(blob) != i0 * 16 + i1 + 8:
#        # Corrupt header
#        print "ugh, the header corruption test fails:"
#        log.trace_me()
#        return None
    # if this header is corrupt, rpmlib exits and we stop ;-<
    try:
        hdr = rpm.headerLoad(blob)
    except:
        if filename:
            print _("rpm was unable to load the header: %s" % filename)
        else:
            print _("rpm was unable to load a header")
        return None
    # Header successfully read
    #print hdr['name']
    return hdr

def main():


    pkg = ["gpg-pubkey", "db42a60e", "37ea5438" , "", None]

    print verifyPackages([pkg])
    sys.exit()
    # zsh-4.0.4-8
    h = installedHeader("zsh", _ts)
    print
    if h['epoch'] == None:
        epoch = '0'
    pkg = [h['name'], h['version'] , h['release'], epoch, h['arch']]
    print installedHeaderIndexByPkg(pkg)

    pkg = ['kernel', '2.4.18', '7.93', '0','i686']
    print installedHeaderIndexByPkg(pkg)

    pkg = ['kernel', '2.4.18', '3', '0', 'i686']
    print installedHeaderIndexByPkg(pkg)


    print installedHeaderIndex(name="up2date")

    print installedHeaderIndex(epoch="1")

    print installedHeaderByKeyword(version="1.0")
if __name__ == "__main__":
    main()
