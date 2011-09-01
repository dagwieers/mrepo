#!/usr/bin/python
#
# This file is a portion of the Red Hat Update Agent
# Copyright (c) 1999 - 2005 Red Hat, Inc.  Distributed under GPL
#
# Authors:
#       Cristian Gafton <gafton@redhat.com>
#       Adrian Likins   <alikins@redhat.com>
#
# $Id: sourcesConfig.py 113619 2007-03-21 19:20:39Z pkilambi $

import os
import sys
import string
import re

import config
import up2dateUtils
import up2dateLog
import wrapperUtils

# The format for sources v1 is stupid. each entry can only be one line
# each different source type has different info (aieee!) # comment stuff out (duh)


SOURCESFILE="/etc/sysconfig/rhn/sources"

def showError(line):
    print "Error parsing %s" % SOURCESFILE
    print "at line: %s" % line

class SourcesConfigFile:
    "class for parsing out the up2date/apt/yum src repo info"
    def __init__(self, filename = None):
        self.repos = []
        self.fileName = filename
        self.log = up2dateLog.initLog()
        self.cfg = config.initUp2dateConfig()
        #just so we dont import repomd info more than onc
        self.setupRepomd = None
        if self.fileName:
            self.load()
            

    def load(self, filename = None):
        if filename:
            self.fileName = filename
        if not self.fileName:
            return

        if not os.access(self.fileName, os.R_OK):
            print "warning: can't access %s" % self.fileName
            return

        f = open(self.fileName, "r")

        
	for line in f.readlines():
            # strip comments
            if '#' in line:
                line = line[:string.find(line, '#')]

            line = string.strip(line)
            if not line:
                continue

            data = string.split(line)
            repoType = data[0]
            if data[0] == "up2date":
                self.parseUp2date(line)
            if data[0] == "yum":
                self.parseYum(line)
            if data[0] == "apt":
                self.parseApt(line)
            if data[0] == "dir":
                self.parseDir(line)
            if data[0] == "bt":
                self.parseBt(line)
            if data[0] == "yum-mirror":
                self.parseYumMirror(line)
            if data[0] == "apt-mirror":
                self.parseAptMirror(line)
            if data[0] == "rpmmd":
                self.parseRpmmd(line)
            if data[0] == "repomd" and not self.setupRepomd:
                self.parseRepomd(line)
                self.setupRepomd = True

        f.close()

    # in some cases, we want to readd the line that points at RHN
    def writeUp2date(self):
        # parse the config file into something editable
        f = open(self.fileName, "r")
        lines = f.readlines()
        index = 0
        for line in lines:
            if '#' in line:
                line = line[:string.find(line, '#')]
                
            line = string.rstrip(line)
            if not line:
                index = index + 1
                continue
            
            firstUsedLine = index
            break
        
        f.close()
        
        f = open(self.fileName, "w")

        lines.insert(firstUsedLine-1, "up2date default\n")
        buf = string.join(lines, '')
        f.write(buf)
        f.close()
        
        
    def parseUp2date(self,line):
        try:
            (tmp, url) = string.split(line)
        except:
            showError(line)
            return
            
        if url == "default":
            self.repos.append({'type':'up2date', 'url':self.cfg['serverURL']})
        else:
            self.repos.append({'type':'up2date', 'url':url})

    def parseDir(self, line):
        try:
            (tmp, name, path) = string.split(line)
        except:
            showError(line)
            return
        
        self.repos.append({'type':'dir','path':path, 'label':name})

    def parseYum(self, line):

        try:
            (tmp, name, url) = string.split(line)
        except:
            showError(line)
            return
        try:
            (tmp, name, url) = string.split(line)
        except:
            showError(line)
            return



        url,name = self.subArchAndVersion(url, name)
        self.repos.append({'type':'yum', 'url':url, 'label':name})

    def subArchAndVersion(self, url,name):
        arch = up2dateUtils.getUnameArch()

        # bz:229847 parsing to get correct release 
        # version instead of hardcoding it, for ex:
        # 3Desktop, 4AS, 3AS
        releasever = re.split('[^0-9]', up2dateUtils.getVersion())[0]
        
        url = string.replace(url, "$ARCH", arch)
        name = string.replace(name, "$ARCH", arch)
        url = string.replace(url, "$RELEASE", releasever)
        name = string.replace(name, "$RELEASE", releasever)

        # support the yum format as well
        url = string.replace(url, "$basearch", arch)
        name = string.replace(name, "$basearch", arch)
        url = string.replace(url, "$releasever", releasever)
        name = string.replace(name, "$releasever", releasever)

        return (url, name)

    def parseYumMirror(self, line):
        try:
            tmp = []
            tmp = string.split(line)
        except:
            showError(line)
            return

        
        url = tmp[2]
        name = tmp[1]

        (url,name) = self.subArchAndVersion(url, name)
        
        self.repos.append({'type':'yum-mirror', 'url':url, 'label':name})
        
    def parseAptMirror(self, line):
        try:
            tmp = []
            tmp = string.split(line)
            server = tmp[2]
            path = tmp[3]
            label = tmp[1]
            dists = tmp[4:]
        except:
            showError(line)
            return

        
        (url,name) = self.subArchAndVersion(url, name)
        for dist in dists:
            self.repos.append({'type':'apt-mirror', 'url':"%s/%s" (server, path),
                               'label':name, 'dist': dist})


    def parseRepomd(self, line):
        try:
            parts = string.split(line)
        except:
            showError(line)
            return

        try:
            from repoBackends import yumBaseRepo
        except ImportError:
            self.log.log_me("Unable to import repomd so repomd support will not be available")
            return
        
        yb = yumBaseRepo.initYumRepo()
        channelName = parts[1]

        # use the built in yum config 
        from yum import repos
 
        for reponame in yb.repos.repos.keys():
            repo = yb.repos.repos[reponame]
            if repo.enabled:
                repo.baseurlSetup()
                # at some point this name got changed in yum
                if hasattr(repo, "baseurls"):
                    (url,name) = self.subArchAndVersion(repo.baseurls[0], repo.id)
                else:
                    (url,name) = self.subArchAndVersion(repo.baseurl[0], repo.id)
                self.repos.append({'type':'repomd', 'url':url, 'label':name})

    def parseApt(self, line):
        # of course, the debian one had to be weird
        # atm, we only support http one's
        try:
            data = string.split(line)
            name = data[1]
            server = data[2]
            path = data[3]
            dists = data[4:]
        except:
            print "Error parsing /etc/sysconfig/rhn/up2date"
            print "at line: %s" % line
            return
        # if multiple dists are appended, make them seperate
        # channels
        for dist in dists:
            self.repos.append({'type':'apt',
                          'url':'%s/%s' % (server, path),
                          'label': "%s-%s" % (name,dist),
                          'dist': dist})


def getSources():
    global sources
    try:
        sources = sources
    except NameError:
        sources = None

    if sources == None:
        scfg = SourcesConfigFile(filename="/etc/sysconfig/rhn/sources")
        sources = scfg.repos
        
    return sources
    
def configHasRepomd(sources):
    for source in sources:
        if source['type'] == "repomd":
            return 1
    return 0                    
