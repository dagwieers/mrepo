#!/usr/bin/python

import os
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

import config
import up2dateErrors
import up2dateMessages
import rpmUtils
import transaction
import re
import string
import distrotype



# directory to look for .gnupg/options, etc
gpg_home_dir = "/root/.gnupg"

# the fingerprints of our keys
redhat_gpg_fingerprint =      "219180CDDB42A60E"
redhat_beta_gpg_fingerprint = "FD372689897DA07A"
fedora_gpg_fingerprint =      "B44269D04F2A6FD2"
fedora_test_gpg_fingerprint = "DA84CBD430C9ECF8"

# basically determines if we care about the
# beta key or not.


def checkGPGInstallation():
    # return 1, gpg not installed
    # return 2, key not installed
    if not findKey(redhat_gpg_fingerprint):
        return 2

    if hasattr(distrotype, "fedora") and not findKey(fedora_gpg_fingerprint):
        return 2

    if hasattr(distrotype, "rawhide"):
        if not findKey(redhat_beta_gpg_fingerprint):
            return 2
	if hasattr(distrotype, "fedora") and not findKey(fedora_test_gpg_fingerprint):
	    return 2
    
    return 0

def checkGPGSanity():
    cfg = config.initUp2dateConfig()
    if cfg["useGPG"] and checkGPGInstallation() == 2:
        errMsg = up2dateMessages.gpgWarningMsg 
        raise up2dateErrors.GPGKeyringError(errMsg)

def findGpgFingerprints():
    # gpg is really really annoying the first time you run it
    # do this so the bits we care about are always atleast the second running
                                             # shut... up... gpg...
    command = "/usr/bin/gpg -q --list-keys > /dev/null 2>&1"
    fdno = os.popen(command)
    fdno.close()
    
    command  = "/usr/bin/gpg %s --list-keys --with-colons" % rpmUtils.getGPGflags()
    fdno = os.popen(command)
    lines = fdno.readlines()
    fdno.close()

    fingerprints = []
    for line in lines:
        parts = string.split(line, ":")
        if parts[0] == "pub":
            fingerprint = parts[4]
            fingerprints.append(fingerprint)

    return fingerprints

def findKey(fingerprint):
    version = string.lower("%s" % fingerprint[8:])
    return rpmUtils.installedHeadersNameVersion("gpg-pubkey", version)

def importKey(filename):
    fdno = open(filename, "r")
    pubkey = fdno.read()
    fdno.close()
    # need method to import ascii keys

    foo = os.popen("/bin/rpm --import %s  > /dev/null 2>&1" % filename)
    foo.read()
    foo.close()
    # I dont know, this doesnt seem to want to work
#    _ts.pgpImportPubkey(pubkey)

def importRedHatGpgKeys():
    keys = ["/usr/share/rhn/RPM-GPG-KEY"]
    if hasattr(distrotype, 'fedora') and distrotype.fedora:
        keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora")
    if hasattr(distrotype, 'rawhide') and distrotype.rawhide:
        keys.append("/usr/share/rhn/BETA-RPM-GPG-KEY")
        if hasattr(distrotype, 'fedora') and distrotype.fedora:
	    keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora-test")

    for key in keys:
        importKey(key)

def keysToImport():
    keys = ["/usr/share/rhn/RPM-GPG-KEY"]
    if hasattr(distrotype, 'fedora') and distrotype.fedora:
        keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora")
    if hasattr(distrotype, 'rawhide') and distrotype.rawhide:
        keys.append("/usr/share/rhn/BETA-RPM-GPG-KEY")
        if hasattr(distrotype, 'fedora') and distrotype.fedora:
	    keys.append("/usr/share/rhn/RPM-GPG-KEY-fedora-test")

    return keys

def importGpgKeyring():
    # gpg is really really annoying the first time you run it
    # do this so the bits we care about are always atleast the second running
    command = "/usr/bin/gpg -q --list-keys > /dev/null 2>&1"
    fdno  = os.popen(command)
    fdno.close()
    # method to import an existing keyring into the new
    # rpm mechanism of storing supported keys as virtual
    # packages in the database
    for fingerprint in findGpgFingerprints():
        if findKey(fingerprint):
            continue

        command = "/usr/bin/gpg %s --export %s" % (
            rpmUtils.getGPGflags(), fingerprint)
        #    print command
        fdno = os.popen(command)
        pubkey = fdno.read()
        fdno.close()
        _ts = transaction.initReadOnlyTransaction()
        _ts.pgpImportPubkey(pubkey)
        #_ts.pgpPrtPkts(pubkey)
    return 0

# wrapper function for importing existing keyring, and
# adding the redhat keys if they are there already
def addGPGKeys():
    cfg = config.initUp2dateConfig()
    if os.access(cfg["gpgKeyRing"], os.R_OK):
        # if they have a keyring like 7.3 used, import the keys off
        # of it
        importGpgKeyring()

    # the red hat keys still arent there
    if not checkGPGInstallation():
        importRedHatGpgKeys()
        






def main():
    #importGpgKeyring()

##    print "checkGPGInstallation()"
##    print checkGPGInstallation()
##    print
##    sys.exit(1)

##    print "checkGPGSanity()"
##    try:
##        print checkGPGSanity()
##    except up2dateErrors.GPGKeyringError,e :
##        print e.errmsg
##    print
    
    print "findGpgFingerprints()"
    fingerprints = findGpgFingerprints()
    print fingerprints
    print

    print "findKeys"
    for fingerprint in fingerprints:
        print "findKey(%s)" % fingerprint
        print findKey(fingerprint)
    print

    #print """importKey("/usr/share/rhn/RPM-GPG-KEY")"""
    #print importKey("/usr/share/rhn/RPM-GPG-KEY")
    #print

    print "findKey(%s) RPM-GPG-KEY fingerprint" % redhat_gpg_fingerprint
    print findKey(redhat_gpg_fingerprint)
    print

    print "importGpgKeyring()"
    print importGpgKeyring()
    print

    print "findKey(%s) RPM-GPG-KEY fingerprint" % redhat_gpg_fingerprint
    print findKey(redhat_gpg_fingerprint)
    print
    

    

if __name__ == "__main__":
    main()
