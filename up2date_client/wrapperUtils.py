#!/usr/bin/python
#
# $Id: wrapperUtils.py 87091 2005-11-15 17:25:11Z alikins $

import os   
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")
import time
import string

import rpm

import up2dateErrors
import up2dateMessages
import rpmUtils
import rhnErrata
import up2dateUtils
import rpcServer
import config

# used for rpmCallbacks, hopefully better than having
# lots of globals lying around...
class RpmCallback:
    def __init__(self):
        self.fd = 0
        self.hashesPrinted = None
        self.progressCurrent = None
        self.progressTotal = None
        self.hashesPrinted = None
        self.lastPercent = None
        self.packagesTotal = None
        self.cfg = config.initUp2dateConfig()

    def callback(self, what, amount, total, hdr, path):
#        print "what: %s amount: %s total: %s hdr: %s path: %s" % (
#          what, amount, total, hdr, path)

        if what == rpm.RPMCALLBACK_INST_OPEN_FILE:
            fileName = "%s/%s-%s-%s.%s.rpm" % (path,
                                               hdr['name'],
                                               hdr['version'],
                                               hdr['release'],
                                               hdr['arch'])
            try:
                self.fd = os.open(fileName, os.O_RDONLY)
            except OSError:
                raise up2dateErrors.RpmError("Error opening %s" % fileName)

            return self.fd
        elif what == rpm.RPMCALLBACK_INST_CLOSE_FILE:
            os.close(self.fd)
            self.fd = 0

        elif what == rpm.RPMCALLBACK_INST_START:
            self.hashesPrinted = 0
            self.lastPercent = 0
            if type(hdr) == type(""):
                print "     %-23.23s" % ( hdr),
                sys.stdout.flush()

            else:
                fileName = "%s/%s-%s-%s.%s.rpm" % (path,
                                                   hdr['name'],
                                                   hdr['version'],
                                                   hdr['release'],
                                                   hdr['arch'])
                if self.cfg["isatty"]:
                    if self.progressCurrent == 0:
                        printit("Installing") 
                    print "%4d:%-23.23s" % (self.progressCurrent + 1,
                                            hdr['name']),
                    sys.stdout.flush()
                else:
                    printit("Installing %s" % fileName)


        # gets called at the start of each repackage, with a count of
        # which package and a total of the number of packages aka:
        # amount: 2 total: 7 for the second package being repackages
        # out of 7. That sounds obvious doesnt it?
        elif what == rpm.RPMCALLBACK_REPACKAGE_PROGRESS:
            pass
#            print "what: %s amount: %s total: %s hdr: %s path: %s" % (
#            what, amount, total, hdr, path)
#            self.printRpmHash(amount, total, noInc=1)
            
        elif what == rpm.RPMCALLBACK_REPACKAGE_START:
            printit( "Repackaging")
            #sys.stdout.flush()
            #print "what: %s amount: %s total: %s hdr: %s path: %s" % (
            # what, amount, total, hdr, path)
            
        elif what == rpm.RPMCALLBACK_INST_PROGRESS:
            if type(hdr) == type(""):
                # repackage...
                self.printRpmHash(amount,total, noInc=1)
            else:
                self.printRpmHash(amount,total)


        elif what == rpm.RPMCALLBACK_TRANS_PROGRESS:
            self.printRpmHash(amount, total, noInc=1)

            
        elif what == rpm.RPMCALLBACK_TRANS_START:
            self.hashesPrinted = 0
            self.lastPercent = 0
            self.progressTotal = 1
            self.progressCurrent = 0
            print "%-23.23s" % "Preparing",
            sys.stdout.flush()

        elif what == rpm.RPMCALLBACK_TRANS_STOP:
            self.printRpmHash(1, 1)
            self.progressTotal = self.packagesTotal
            self.progressCurrent = 0
            
        elif (what == rpm.RPMCALLBACK_UNINST_PROGRESS or
              what == rpm.RPMCALLBACK_UNINST_START or
              what == rpm.RPMCALLBACK_UNINST_STOP):
            pass
        
        if hasattr(rpm, "RPMCALLBACK_UNPACK_ERROR"):
            if ((what == rpm.RPMCALLBACK_UNPACK_ERROR) or
                (what == rpm.RPMCALLBACK_CPIO_ERROR)):
                pkg = "%s-%s-%s" % (hdr[rpm.RPMTAG_NAME],
                                    hdr[rpm.RPMTAG_VERSION],
                                    hdr[rpm.RPMTAG_RELEASE])

                if what == rpm.RPMCALLBACK_UNPACK_ERROR:
                    raise up2dateErrors.RpmInstallError, (
                        "There was a rpm unpack error "\
                        "installing the package: %s" % pkg, pkg)
                elif what == rpm.RPMCALLBACK_CPIO_ERROR:
                    raise up2dateErrors.RpmInstallError, (
                        "There was a cpio error "\
                        "installing the package: %s" % pkg, pkg)

    # ported from C code in RPM 2/28/01 -- PGB
    def printRpmHash(self,amount, total, noInc=0):
        hashesTotal = 44

        if total:
            percent = int(100 * (float(amount) / total))
        else:
            percent = 100
    
        if percent <= self.lastPercent:
            return

        self.lastPercent = percent

        if (self.hashesPrinted != hashesTotal):
            if total:
                hashesNeeded = int(hashesTotal * (float(amount) / total))
            else:
                hashesNeeded = hashesTotal

            if self.cfg["isatty"]:
                for i in range(hashesNeeded):
                    sys.stdout.write('#')

                for i in range(hashesNeeded, hashesTotal):
                    sys.stdout.write(' ')

                print "(%3d%%)" % percent, 
                for i in range(hashesTotal + 6):
                    sys.stdout.write("\b")

            self.hashesPrinted = hashesNeeded
            
            if self.hashesPrinted == hashesTotal:
                if self.cfg["isatty"]: 
                    #global progressCurrent, progressTotal
                    for i in range(1,hashesTotal):
                        sys.stdout.write("#")
                    # I dont want to increment the progress count for
                    # repackage info. Bit of a kluge
                    if not noInc:
                        self.progressCurrent = self.progressCurrent + 1
                    if self.progressTotal:
                        print " [%3d%%]" % int(100 * (float(self.progressCurrent) /
                                                      self.progressTotal))
                    else:
                        print " [%3d%%]" % 100

        sys.stdout.flush()


# this is used outside of rpmCallbacks, so
# cant really make it a method of rpmCallback
lastPercent = 0
def percent(amount, total, speed = 0, sec = 0):
    cfg = config.initUp2dateConfig()
    hashesTotal = 40

    if total:
        hashesNeeded = int(hashesTotal * (float(amount) / total))
    else:
        hashesNeeded = hashesTotal

    global lastPercent
    # dont print if were not running on a tty
    if cfg["isatty"] and (hashesNeeded > lastPercent or amount == total):
        for i in range(hashesNeeded):
            sys.stdout.write('#')

        sys.stdout.write('\r')

        if amount == total:
            print

    if amount == total:
        lastPercent = 0
    else:
        lastPercent = hashesNeeded



def printRetrieveHash(amount, total, speed = 0, secs = 0):
    cfg = config.initUp2dateConfig()
    hashesTotal = 26
    
    if total:
        percent = int(100 * (float(amount) / total))
        hashesNeeded = int(hashesTotal * (float(amount) / total))
    else:
        percent = 100
        hashesNeeded = hashesTotal

    if cfg["isatty"]:
        for i in range(hashesNeeded):
            sys.stdout.write('#')

        for i in range(hashesNeeded, hashesTotal):
            sys.stdout.write(' ')

    if cfg["isatty"]:
        if amount == total:
            print "%-25s" % " Done."
        else:
            print "%4d k/sec, %02d:%02d:%02d rem." % \
                  (speed / 1024, secs / (60*60), (secs % 3600) / 60,
                   secs % 60),
            for i in range(hashesTotal + 25):
                sys.stdout.write("\b")
    elif amount == total:
        print "Retrieved."

def printPkg(name, shortName = None):
    if shortName:
        print "%-27.27s " % (shortName + ":"),
    else:
        print "%-27.27s " % (name + ":"),

def printit(a):
    print "\n" + a + "..."


# generic warning dialog used in several places in wrapper
def warningDialog(message, hasGui):
    if hasGui:
        try:
            from up2date_client import gui
            gui.errorWindow(message)
        except:
            print "Unable to open gui. Try `up2date --nox`"
            print message
    else:
        print message


def printDepPackages(depPackages):
    print "The following packages were added to your selection to satisfy dependencies:"
    print """
Name                                    Version        Release
--------------------------------------------------------------"""
    for pkg in depPackages:
        print "%-40s%-15s%-20s" % (pkg[0], pkg[1], pkg[2])
    print
    
def stdoutMsgCallback(msg):
    print msg

warningCallback = stdoutMsgCallback


# these functions are kind of ugly but...
def printVerboseList(availUpdates):
    cfg = config.initUp2dateConfig()
    if cfg['showChannels']:
        print """
Name                          Version        Rel             Channel     
----------------------------------------------------------------------"""
        for pkg in availUpdates:
            print "%-30s%-15s%-15s%-20s" % (pkg[0], pkg[1], pkg[2], pkg[6])
            if cfg["debug"]:
                time.sleep(.25)
                advisories = rhnErrata.getAdvisoryInfo(pkg)
                if advisories:
                    for a in advisories:
                        topic = string.join(string.split(a['topic']), ' ')
                        print "[%s] %s\n" % (a['advisory'], topic)
                else:
                    print "No advisory information available\n"
        print
        return
    print """
Name                                    Version        Rel     
----------------------------------------------------------"""
    for pkg in availUpdates:
        print "%-40s%-15s%-18s%-6s" % (pkg[0], pkg[1], pkg[2], pkg[4])
        if cfg["debug"]:
            time.sleep(.25)
            advisories = rhnErrata.getAdvisoryInfo(pkg)
            if advisories:
                for a in advisories:
                    topic = string.join(string.split(a['topic']), ' ')
                    print "[%s] %s\n" % (a['advisory'], topic)
            else:
                print "No advisory information available\n"
    print

def printSkippedPackages(skippedUpdates):
    cfg = config.initUp2dateConfig()
    print "The following Packages were marked to be skipped by your configuration:"
    print """
Name                                    Version        Rel  Reason
-------------------------------------------------------------------------------"""
    for pkg,reason in skippedUpdates:
        print "%-40s%-15s%-5s%s" % (pkg[0], pkg[1], pkg[2], reason)
        if cfg["debug"]:
            time.sleep(.25)
            advisories = rhnErrata.getAdvisoryInfo(pkg)
            if advisories:
                for a in advisories:
                    topic = string.join(string.split(a['topic']), ' ')
                    print "[%s] %s\n" % (a['advisory'], topic)
            else:
                print "No advisory information available\n"
    print

def printEmptyGlobsWarning(listOfGlobs):
    print "The following wildcards did not match any packages:"
    for token in listOfGlobs:
        print token

def printEmptyCompsWarning(listOfComps):
    print "The following groups did not match any packages:"
    for token in listOfComps:
        print token

def printObsoletedPackages(obsoletedPackages):
    print "The following Packages are obsoleted by newer packages:"
    print """
Name-Version-Release        obsoleted by      Name-Version-Release
-------------------------------------------------------------------------------"""
    for (obs,newpackages) in obsoletedPackages:
        obsstr = "%s-%s-%s" % (obs[0],obs[1],obs[2])
        newpackage = newpackages[0]
        newstr = "%s-%s-%s" % (newpackage[0], newpackage[1], newpackage[2])
        print "%-40s%-40s" % (obsstr, newstr)
        # we can have more than one package obsoleting something
        for newpackage in newpackages[1:]:
            newstr = "%s-%s-%s" % (newpackage[0], newpackage[1], newpackage[2])
            print "%-40s%-40s\n" % ("", newstr)
                                       
def  printInstalledObsoletingPackages(installedObsoletingPackages):
    print "The following packages were not installed because they are obsoleted by installed packages:"
    print """
Name-Version-Release       obsoleted by      Name-Version-Release
-------------------------------------------------------------------------------"""
    for (obsoleted, obsoleting) in installedObsoletingPackages:
        obsstr = "%s-%s-%s" % (obsoleted[0],obsoleted[1],obsoleted[2])
        print "%-40s%-40s" % (obsstr, obsoleting[0])
        for obsoletingstr in obsoleting[1:]:
            print "%-40s%-40s" % (obsstr, obsoletingstr)

def printAvailablePackages(availablePackages):
    print "The following packages are not installed but available from Red Hat Network:"
    print """
Name                                    Version        Release  
--------------------------------------------------------------"""
    for pkg in availablePackages:
        print "%-40s%-14s%-14s" % (pkg[0], pkg[1], pkg[2])
    print
