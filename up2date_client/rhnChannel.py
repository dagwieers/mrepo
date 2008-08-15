#!/usr/bin/python

# all the crap that is stored on the rhn side of stuff
# updating/fetching package lists, channels, etc

import os
import time
import random

import up2dateAuth
import up2dateErrors
import config
import up2dateLog
import rpcServer
import sourcesConfig
import urlMirrors
from rhn import rpclib


from rhpl.translate import _, N_



global channel_blacklist
channel_blacklist = []


# FIXME?
# change this so it doesnt import sourceConfig, but
# instead sourcesConfig imports rhnChannel (and repoDirector)
# this use a repoDirector.repos.parseConfig() or the like for
# each line in "sources", which would then add approriate channels
# to rhnChannel.selected_channels and populate the sources lists
# the parseApt/parseYum stuff would move to repoBackends/*Repo.parseConfig()
# instead... then we should beable to fully modularize the backend support


# heh, dont get much more generic than this...
class rhnChannel:
    # shrug, use attributes for thetime being
    def __init__(self, **kwargs):
        self.dict = {}

        for kw in kwargs.keys():
            self.dict[kw] = kwargs[kw]
               
    def __getitem__(self, item):
        return self.dict[item]

    def __setitem__(self, item, value):
        self.dict[item] = value

    def keys(self):
        return self.dict.keys()

    def values(self):
        return self.dict.values()

    def items(self):
        return self.dict.items()

class rhnChannelList:
    def __init__(self):
        # probabaly need to keep these in order for
        #precedence
        self.list = []

    def addChannel(self, channel):
        self.list.append(channel)


    def channels(self):
        return self.list

    def getByLabel(self, channelname):
        for channel in self.list:
            if channel['label'] == channelname:
                return channel
    def getByName(self, channelname):
        return self.getByLabel(channelname)

    def getByType(self, type):
        channels = []
        for channel in self.list:
            if channel['type'] == type:
                channels.append(channel)
        return channels

# for the gui client that needs to show more info
# maybe we should always make this call? If nothing
# else, wrapper should have a way to show extended channel info
def getChannelDetails():

    channels = []
    sourceChannels = getChannels()

    useRhn = None
    for sourceChannel in sourceChannels.channels():
        if sourceChannel['type'] == "up2date":
            useRhn = 1

    if useRhn:
        s = rpcServer.getServer()
        up2dateChannels = rpcServer.doCall(s.up2date.listChannels, up2dateAuth.getSystemId())

    for sourceChannel in sourceChannels.channels():
        if sourceChannel['type'] != 'up2date':
            # FIMXE: kluge since we dont have a good name, maybe be able to fix
            sourceChannel['name'] = sourceChannel['label']
            sourceChannel['description'] = "%s channel %s from  %s" % (sourceChannel['type'],
                                                                           sourceChannel['label'],
                                                                           sourceChannel['url'])
            channels.append(sourceChannel)
            continue
    
        if useRhn:
            for up2dateChannel in up2dateChannels:
                if up2dateChannel['label'] != sourceChannel['label']:
                    continue
                for key in up2dateChannel.keys():
                    sourceChannel[key] = up2dateChannel[key]
                channels.append(sourceChannel)
            

    return channels

def getMirror(source,url):

    mirrors = urlMirrors.getMirrors(source,url)

#    print "mirrors: %s" % mirrors
    length  = len(mirrors)
    # if we didnt find any mirrors, return the
    # default
    if not length:
        return url
    random.seed(time.time())
    index = random.randrange(0, length)
    randomMirror = mirrors[index]
    print "using mirror: %s" % randomMirror
    return randomMirror
    

cmdline_pkgs = []

global selected_channels
selected_channels = None
def getChannels(force=None, label_whitelist=None):
    cfg = config.initUp2dateConfig()
    log = up2dateLog.initLog()
    global selected_channels
    #bz:210625 the selected_chs is never filled
    # so it assumes there is no channel although
    # channels are subscribed
    selected_channels=label_whitelist
    if not selected_channels and not force:

        useRhn = 0
        sources = sourcesConfig.getSources()
        for source in sources:
            if source['type'] == "up2date":
                useRhn = 1

        if cfg.has_key('cmdlineChannel'):
            sources.append({'type':'cmdline', 'label':'cmdline'}) 

        selected_channels = rhnChannelList()
        cfg['useRhn'] = useRhn
        if useRhn:
            li = up2dateAuth.getLoginInfo()
            # login can fail...
            if not li:
                return []
        
            tmp = li.get('X-RHN-Auth-Channels')
            if tmp == None:
                tmp = []
            for i in tmp:
                if label_whitelist and not label_whitelist.has_key(i[0]):
                    continue
                
                channel = rhnChannel(label = i[0], version = i[1],
                                     type = 'up2date', url = cfg["serverURL"])
                selected_channels.addChannel(channel)

            if len(selected_channels.list) == 0:
                raise up2dateErrors.NoChannelsError(_("This system may not be updated until it is associated with a channel."))
        # doesnt do much at the moment, but I've got the feeling
        # it's going to get much more complicated

        #  ^ Indeed...
        sources = sourcesConfig.getSources()

        # create a virutal "source" that is just the packages specified on the commandline
        if cfg.has_key('cmdlineChannel'):
            sources.append({'type':'cmdline', 'label':'cmdline'}) 

        useMirrors = {}
        mirrorSources = []
        #figure out mirrorInfo first:
        for source in sources:
            if source['type'] in ('apt-mirror', 'yum-mirror'):
                label = source['label']
                mirrorUrl = source['url']
                useMirrors[label] = mirrorUrl
                mirrorSources.append(source)

        for source in mirrorSources:
            sources.remove(source)
        
        for source in sources:
            url = ""
            channel = None
            
            if source['type'] == "up2date":
                # FIXME: need better logic here
                continue
            if source['type'] == "yum":
                url = source['url']
                if useMirrors.has_key(source['label']):
                    url = getMirror(source,useMirrors[source['label']])
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     version = "1000",
                                     url = url)

            if source['type'] == "apt":
                url = source['url']
                if useMirrors.has_key(source['label']):
                    url = getMirror(source, useMirrors[source['label']])
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     version = "1000",
                                     url = url,
                                     dist = source['dist'])

            if source['type'] == 'repomd':
                url = source['url']
                if useMirrors.has_key(source['label']):
                    url = getMirror(source, useMirrors[source['label']])
		     #url = getMirror(source)
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     version = "1000",
                                     url = url)

            if source['type'] == "dir":
                if not os.access(source['path'], os.R_OK):
                    # FIXME: this should probabaly be an exception we catch somewhere
                    # and present a pretty erorr message, but this is better than a traceback
                    print _("%s is not a valid directory") % source['path']
                    continue
                timestamp = os.stat(source['path'])[8]
                version = time.strftime("%Y%m%d%H%M%S", time.gmtime(timestamp))
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     version = version,
                                     url = "file:/%s" % source['path'],
                                     path = source['path'])

            if source['type'] == 'bt':
                # version doesnt really matter since we only use
                # it as a possible source to download packages
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     version = "1000",
                                     url = source['url'])

            if source['type'] == "cmdline":
                channel = rhnChannel(label = source['label'],
                                     type = source['type'],
                                     # whatever...
                                     version = "1000",
                                     url = "cmdline")

            if label_whitelist and not label_whitelist.has_key(channel['label']):
                    continue
                
            selected_channels.addChannel(channel)


    return selected_channels
            

def setChannels(tempchannels):
    global selected_channels
    selected_channels = None
    whitelist = dict(map(lambda x: (x,1), tempchannels))
    return getChannels(label_whitelist=whitelist)



def subscribeChannels(channels,username,passwd):
    s = rpcServer.getServer()
    try:
        channels = rpcServer.doCall(s.up2date.subscribeChannels,
                          up2dateAuth.getSystemId(),
                          channels,
                          username,
                          passwd)
    except rpclib.Fault, f:
        if f.faultCode == -36:
            raise up2dateErrors.PasswordError(f.faultString)
        else:
            raise up2dateErrors.CommunicationError(f.faultString)

def unsubscribeChannels(channels,username,passwd):
    s = rpcServer.getServer()
    try:
        channels = rpcServer.doCall(s.up2date.unsubscribeChannels,
                          up2dateAuth.getSystemId(),
                          channels,
                          username,
                          passwd)
    except rpclib.Fault, f:
        if f.faultCode == -36:
            raise up2dateErrors.PasswordError(f.faultString)
        else:
            raise up2dateErrors.CommunicationError(f.faultString)

