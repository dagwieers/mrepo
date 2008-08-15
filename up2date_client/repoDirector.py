#!/usr/bin/python

import os
import sys
import rhnChannel
import config
import sourcesConfig
import up2dateLog


class RepoDirector:
    handlers = {}
    depSolveHandlers = {}
    def __init__(self, handlers=None, depSolveHandlers=None):
        if handlers:
            self.handlers = handlers
        if depSolveHandlers:
            self.depSolveHandlers = depSolveHandlers
        self.channels = rhnChannel.getChannels()

    def listPackages(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].listPackages(channel, msgCallback, progressCallback)

    def listAllPackages(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].listAllPackages(channel, msgCallback, progressCallback)


    def getObsoletes(self, channel, msgCallback, progressCallback):
        return self.handlers[channel['type']].getObsoletes(channel, msgCallback, progressCallback)

    def getHeader(self, pkg,  msgCallback = None, progressCallback = None):
        channel = self.channels.getByLabel(pkg[6])
        return self.handlers[channel['type']].getHeader(pkg, msgCallback, progressCallback)

    def getPackage(self, pkg, msgCallback = None, progressCallback = None):
        channel = self.channels.getByLabel(pkg[6])
        return self.handlers[channel['type']].getPackage(pkg, msgCallback, progressCallback)

    def getPackageSource(self, channel, pkg,  msgCallback = None, progressCallback = None):
        return self.handlers[channel['type']].getPackageSource(channel, pkg, msgCallback, progressCallback)

    def getDepSolveHandlers(self):
        return self.depSolveHandlers

    def updateAuthInfo(self):
        for channeltype in self.handlers.keys():
            self.handlers[channeltype].updateAuthInfo()




def initRepoDirector():
    global rd
    try:
        rd = rd
    except NameError:
        rd = None
        
    if rd:
        return rd

    cfg = config.initUp2dateConfig()
    sources = sourcesConfig.getSources()
    
    rd = RepoDirector()
    if cfg['useRhn']:
        from repoBackends import up2dateRepo
        up2dateRepo.register(rd)
    from repoBackends import yumRepo
    yumRepo.register(rd)
    from repoBackends import aptRepo
    aptRepo.register(rd)
    from repoBackends import dirRepo
    dirRepo.register(rd)

    # Don't try to import repomdRepo unless we need it. Cuts down on the log
    # messages
    if sourcesConfig.configHasRepomd(sources):
        # bz #158256 (allow up2date to continue if yum repomd support isnt
        # found)
        try:
            from repoBackends import repomdRepo
            repomdRepo.register(rd)
        except ImportError:
            log = up2dateLog.initLog()
            log.log_me("Unable to import repomd support so repomd support will not be available")
        
    return rd
