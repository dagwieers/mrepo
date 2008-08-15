#!/usr/bin/python

import os
import sys
import string

import config
import up2dateUtils
from repoBackends import urlUtils

def getMirrors(source, defaultMirrorUrl=None):
    cfg = config.initUp2dateConfig()
    mirrorPath = "/etc/sysconfig/rhn/mirrors/"

    mirrorType = ""
    if cfg.has_key("mirrorLocation"):
        mirrorType = cfg['mirrorLocation']
    
    if mirrorType != "":
        mirrorFile = "%s/%s.%s" % (mirrorPath, source['label'], mirrorType)
    else:
        mirrorFile = "%s/%s" % (mirrorPath, source['label'])

 #   print "source: %s" % source
    mirrors = []
    arch = up2dateUtils.getUnameArch()
 #   print "mf1: %s" % mirrorFile
    if os.access(mirrorFile, os.R_OK):
 #       print "mirrorFile: %s" % mirrorFile
        f = open(mirrorFile, "r")
        for line in f.readlines():
            if line[0] == "#":
                continue
            line = string.strip(line)
            # just in case we want to add more info, like weight, etc
            tmp = []
            tmp = string.split(line, ' ')
            # sub in arch so we can use one mirror list for all arches
            url = string.replace(tmp[0], "$ARCH", arch)

            mirrors.append(url)

    # if there were user defined mirrors, use them
    if mirrors:
#        print "mirrors from /etc: %s" % mirrors
        return mirrors

#    print "gh2"
    #otherwise look for the dymanic ones in /var/spool/up2date
    mirrorPath = cfg['storageDir']
    mirrorFile = "%s/%s" % (mirrorPath, source['label'])
    mirrors = []

# we should cache these and do If-Modified fetches like we
# do for the package list info

##    if os.access(mirrorFile, os.R_OK):
###        print "mirrorFile: %s" % mirrorFile
##        f = open(mirrorFile, "r")
##        for line in f.readlines():
##            line = string.strip(line)
##            # just in case we want to add more info, like weight, etc
##            tmp = []
##            tmp = string.split(line, ' ')

##            mirrors.append(tmp[0])

    # if there were user defined mirrors, use them
    if mirrors:
        return mirrors

#    print "gh3"
    # download and save the latest mirror list

    # use the hardcode url for the moment, till we can
    # expect mirror lists to be in the base of the repo, hopefully
    # soon
    if defaultMirrorUrl == None:
        return []
    
    # we could try something heirarch here, aka, mirrors.us.es first, then mirrors.us, then mirrors
    if mirrorType != "":
        mirrorUrl = "%s.%s" % (defaultMirrorUrl,mirrorType)
    else:
        mirrorUrl = "%s" % (defaultMirrorUrl)

    print mirrorUrl
    try:
    
        readfd = urlUtils.open_resource(mirrorUrl, agent="Up2date/%s" % up2dateUtils.version())
    except IOError:
#        print "gh5"
        return []
#    print "DDDmirrorFile: %s" % mirrorFile
    fd = open(mirrorFile, "w")
    fd.write(readfd.read())
    readfd.close()
    fd.close()

    arch = up2dateUtils.getUnameArch()
    if os.access(mirrorFile, os.R_OK):
#        print "mirrorFile2: %s" % mirrorFile
        f = open(mirrorFile, "r")
        for line in f.readlines():
            line = string.strip(line)
            # blank line
            if len(line) == 0:
                continue
            if line[0] == "#":
                continue
            # just in case we want to add more info, like weight, etc
            tmp = []
            tmp = string.split(line, ' ')

            url = string.replace(tmp[0], "$ARCH", arch)
            mirrors.append(url)
    

#    print "mirrors: %s" % mirrors
    return mirrors

	
