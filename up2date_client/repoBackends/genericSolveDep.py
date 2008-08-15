#!/usr/bin/python
import sys
import fnmatch
import UserDict
import pprint

import rpm

sys.path.append("/usr/share/rhn/")
from up2date_client import config
from up2date_client import rpmUtils
from up2date_client import rhnChannel
from up2date_client import rpcServer
from up2date_client import up2dateLog
from up2date_client import repoDirector



class DictOfLists(UserDict.UserDict):
    def __init__(self, dict=None):
        UserDict.UserDict.__init__(self, dict)
    def __setitem__(self, key, value):
        if not self.data.has_key(key):
            self.data[key] = []
        self.data[key].append(value)
                                                                                                                                                      
    def getFlatList(self):
        x = self.keys()
        blip = []
        for i in x:
            for j in self[i]:
                blip.append((i, j))
        return blip



class GenericSolveDep:
    # so, what exactly does this do? well...
    # this is basically all to work around the fact that
    # when we solve a dep, we know what NVRE solves it
    # but not what arch. This used to not be a problem,
    # as you simply picked the best arch.
    #
    # However, with multilib/biarch, it means we have
    # to do some guessing. Basically, sometimes we only
    # want one arch, sometimes both, sometimes 1 or two
    # of the many arches available
    #
    # the cases where we only want one arch are:
    #    1. the other arch is already installed
    #    2. there is only one arch of that package available
    #    3. the user has specified a --arch, which means
    #       they want a particular arch install overriding 1&2
    #    4. We have both arches isntalled, and one of them
    #       is not the latest
    
    # the cases where we want to install "both" arches
    #    1. we have both arches installed, and there are
    #       newer versions available for both arches
    #    2. we have neither arch installed, but we need
    #       to install both to satisfy deps
    #          a. the same dep applies to both (aka, "libselinux")
    #          b. we have seperate deps that require each arch
    #              (aka, foo.i386 requires libbar.so,
    #                    foo.x86_64 requires libbar.so(64bit)
    #       (to some degree, the later gets done for seperate deps
    #        so doesnt factor into this particular function so
    #        much)
    
    # the cases where we want to install "some" of the arches
    #   These are kernel, glibc, gzip etc where there are
    #   two arch "colors" and more than one arch per color.
    #    aka, glibc.x86_64, glibc.i386, glibc.i686

    # Theres a few basket cases as well, for example when
    # you need to install "foobar" to solve a dep from
    # an x86_64 package and an i386 package. Doing this
    # correctly is further confused by the fact that we
    # dont know what arch of package raises a dep since it
    # is on the transaction as a whole, but we might be
    # able to change that?  WELL... we could... sorta
    # at least on RHEL4/FC3... the release of the package
    # that raises the deps is now actually "release.arch"
    # so thats a possibity, though it doesnt really help
    # us on RHEL2.1/RHEL3. But on RHEL4 we could pass it
    # in as part of the dep and use it as a hint...

    
    def __init__(self):
	self.selectedPkgs = []
        pass



    def __getSolutionsInstalled(self, solutions):
        solutionsInstalled = []
        for p in solutions:
            if self.installedPkgHash.has_key(p[0]):
                iList = self.installedPkgHash[p[0]]
                for iPkg in iList:
                    if self.availListHash.has_key(tuple(iPkg[:4])):
                        # find the avail packages as the same arch
                        # as the installed ones
                        for i in self.availListHash[tuple(p[:4])]:
                            solutionsInstalled.append(p)
        return solutionsInstalled
    
    def solveDep(self, unknowns, availList,
                 msgCallback = None,
                 progressCallback = None,
                 refreshCallback = None):
        self.cfg = config.initUp2dateConfig()
        self.log =  up2dateLog.initLog()
        self.log.log_me("solving dep for: %s" % unknowns)

        self.refreshCallback = refreshCallback
        self.progressCallback = progressCallback
        self.msgCallback = msgCallback
        self.availList = availList

        availList.sort()
        self.availListHash = {}
        for p in self.availList:
            if self.availListHash.has_key(tuple(p[:4])):
                self.availListHash[tuple(p[:4])].append(p)
            else:
                self.availListHash[tuple(p[:4])] = [p]
                
        self.retDict = {}
        self.getSolutions(unknowns,
                          progressCallback = self.progressCallback,
                          msgCallback = self.msgCallback)
        reslist = []

        self.depToPkg = DictOfLists()
        self.depsNotAvailable = DictOfLists()
#        self.depToPkg = {}
        #FIXME: this should be cached, I dont really need to query the db
        # for this everytime
        self.installedPkgList = rpmUtils.getInstalledPackageList(getArch=1)
        self.installedPkgHash = {}
        for pkg in self.installedPkgList:
            if self.installedPkgHash.has_key(pkg[0]):
                self.installedPkgHash[pkg[0]].append(pkg)
	    else:
            	self.installedPkgHash[pkg[0]] = [pkg]

        # we didnt get any results, bow out...
        if not len(self.retDict):
            return (reslist, self.depToPkg)
        
  


        newList = []
        availListNVRE = map(lambda p: p[:4], self.availList)

        failedDeps = []
        solutionPkgs = []
        pkgs = []
        for dep in self.retDict.keys():
            # skip the rest if we didnt get a result
            if len(self.retDict[dep]) == 0:
                continue

            solutions = self.retDict[dep]
            # fixme, grab the first package that satisfies the dep
            #   but make sure we match nvre against the list of avail packages
            #   so we grab the right version of the package
            # if we only get one soltution, use it. No point in jumping
            # though other hoops
            if len(solutions) == 1:
                for solution in solutions:
                    pkgs.append(solution)

            # we've got more than one possible solution, do some work
            # to figure out if I want one, some, or all of them
            elif len(solutions) > 1:
                # try to install the new version of whatever arch is
                # installed
                solutionsInstalled = self.__getSolutionsInstalled(solutions)
                found = 0

                if len(solutionsInstalled):
                    for p in solutionsInstalled:
                        pkgs.append(p)
                        self.depToPkg[dep] = p
                        found = 1
                    if found:
                        break
                # we dont have any of possible solutions installed, pick one
                else:
                    # this is where we could do all sort of heuristics to pick
                    # best one. For now, grab the first one in the list thats
                    # available

                    #FIXME: we need to arch score here for multilib/kernel
                    # packages that dont have a version installed

                    # This tends to happen a lot when isntalling into
                    # empty chroots (aka, pick which of the kernels to
                    # install).

                    # ie, this is the pure heuristic approach...

                    shortest = solutions[0]
                    for solution in solutions:
                        if len(shortest[0]) > len(solution[0]):
                            shortest = solution

                    # if we get this far, its still possible that we have package
                    # that is multilib and we need to install both versions of
                    # this is a check for that...
                    if self.installedPkgHash.has_key(shortest[0]):
                        iList = self.installedPkgHash[shortest[0]]
                        for iPkg in iList:
                            if self.availListHash.has_key(tuple(shortest[:4])):
                                for i in self.availListHash[tuple(shortest[:4])]:
                                    if self.cfg['forcedArch']:
                                        arches = self.cfg['forcedArch']
                                        if i[4] in arches:
                                            pkgs.append(i)
                                            self.depToPkg[dep] = i
                                            break
                                    else:
                                        # its not the same package we have installed
                                        if iPkg[:5] != i[:5]:
                                            # this arch matches the arch of a package
                                            # installed
                                            if iPkg[4] == i[4]:
                                                pkgs.append(i)
                                                self.depToPkg[dep] = i
                                        break


                    # you may be asking yourself, wtf is that madness that follows?
                    # well, good question...
                    # its basically a series of kluges to work around packaging problems
                    # in RHEL-3 (depends who you ask... But basically, its packages doing
                    # stuff that was determined to be "unsupported" at the time of the
                    # initial multilib support, but packages did it later anyway

                    # Basically, what we are trying to do is pick the best arch of
                    # a package to solve a  dep. Easy enough. The tricky part is
                    # what happens when we discover the best arch is already in
                    # transation and is _not_ solving the dep, so we need to look
                    # at the next best arch. So we check to see if we added it to
                    # the list of selected packges already, and if so, add the
                    # next best arch to the set. To make it uglier, the second best
                    # arch might not be valid at all, so in that case, dont use it
                    # (which will cause an unsolved dep, but they happen...)

                    if self.availListHash.has_key(tuple(shortest[:4])):
                        avail = self.availListHash[tuple(shortest[:4])]                            
                        bestArchP = None
                        useNextBestArch = None
                        bestArchP2 = None

                        # a saner approach might be to find the applicable arches,
                        # sort them, and walk over them in order

                        # remove the items with archscore <= 0
                        app_avail = filter(lambda a: rpm.archscore(a[4]), avail)
                        # sort the items by archscore, most approriate first
                        app_avail.sort(lambda a,b: cmp(rpm.archscore(a[4]),rpm.archscore(b[4])))

                        # so, whats wrong with this bit? well, if say "libgnutls.so(64bit)" doesn't
                        # find a dep, we'll try to solve it with gnutls.i386
                        # its because "gnutls" and "libgnutls.so(64bit)" are in the same set of
                        # deps. Since gnutls.x86_64 is added for the "gnutls" dep, its in the
                        # list of already selected for 
                        for i in app_avail:
                            if i in self.selectedPkgs:
                                continue
                            pkgs.append(i)
                            self.depToPkg[dep] = i
                            # we found something, stop iterating over available
                            break
                        # we found something for this dep, stop iterating
                        continue


            else:
                # FIXME: in an ideal world, I could raise an exception here, but that will break the current gui
                pkgs.append(p)                    
                self.depToPkg[dep] = p
                # raise UnsolvedDependencyError("Packages %s provide dep %s but are not available for install based on client config" % (pkgs,dep), dep, pkgs )

        for pkg in pkgs:
            self.selectedPkgs.append(pkg)
            if pkg[:4] in availListNVRE:
                newList.append(pkg)
            else:
                newList.append(pkg)
            reslist = newList
        # FIXME: we need to return the list of stuff that was skipped
        # because it wasn't on the available list and present it to the
        # user something like:
        # blippy-1.0-1  requires barpy-2.0-1 but barpy-3.0-1 is already isntalled
        #print "\n\nself.depsNotAvailable"
        #pprint.pprint(self.depsNotAvailable)
        #pprint.pprint(self.depToPkg)
        return (reslist, self.depToPkg)

class SolveByHeadersSolveDep(GenericSolveDep):
    def __init__(self):
        GenericSolveDep.__init__(self)

    def getHeader(self, pkg,
                  msgCallback = None,
                  progressCallback = None ):
        self.repos = repoDirector.initRepoDirector()
        hdr, type = rpcServer.doCall(self.repos.getHeader, pkg,
                                     msgCallback = msgCallback,
                                     progressCallback = progressCallback)
        return hdr
        
    def getSolutions(self, unknowns, msgCallback = None, progressCallback = None):
        channels = rhnChannel.getChannels()
        repoChannels = channels.getByType(self.type)
        repoPackages = []
        channelNames = []

        for channel in repoChannels:
            channelNames.append(channel['label'])

        for pkg in self.availList:
            if pkg[6] in channelNames:
                repoPackages.append(pkg)

        solutions = {}
        totalLen = len(repoPackages)
        count = 0
        # dont show the message if were not going to do anything
        if msgCallback and totalLen:
            msgCallback("Downloading headers to solve dependencies")
        for pkg in repoPackages:
            hdr = self.getHeader(pkg)
            if progressCallback:                
                progressCallback(count, totalLen)
            count = count + 1 
            # this bit basically straight out of yum/pkgaction.py GPL Duke Univeristy 2002
            fullprovideslist = hdr[rpm.RPMTAG_PROVIDES]
            if hdr[rpm.RPMTAG_FILENAMES] != None:
                fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_FILENAMES]
            if hdr[rpm.RPMTAG_DIRNAMES] != None:
                fullprovideslist = fullprovideslist + hdr[rpm.RPMTAG_DIRNAMES]
            unknownsCopy = unknowns[:]
            for unknown in unknowns:
                for item in fullprovideslist:
                    if unknown == item:
                        if solutions.has_key(unknown):
                            solutions[unknown].append(pkg)
                        else:
                            solutions[unknown] = [pkg]
                        try:
                            unknownsCopy.remove(unknown)
                        except ValueError:
                            # already removed from list
                            pass
                        if len(unknownsCopy) == 0:
                            break
            del fullprovideslist
                

        self.retDict = solutions


##class YumSolveDep(SolveByHeadersSolveDep):
##    def __init__(self):
##        SolveByHeadersSolveDep.__init__(self)
##        self.type = "yum"
        


class AptSolveDep(SolveByHeadersSolveDep):
    def __init__(self):
        SolveByHeadersSolveDep.__init__(self)
        self.type = "apt"

##class DirSolveDep(SolveByHeadersSolveDep):
##    def __init__(self):
##        SolveByHeadersSolveDep.__init__(self)
##        self.type = "dir"
