#!/usr/bin/python
#
# $Id: up2dateAuth.py 87091 2005-11-15 17:25:11Z alikins $

import rpcServer
import config
import os
import up2dateErrors
import up2dateUtils
import string
import up2dateLog
import clientCaps
import capabilities

from types import DictType

from rhn import rpclib

loginInfo = None

def getSystemId():
    cfg = config.initUp2dateConfig()
    path = cfg["systemIdPath"]
    if not os.access(path, os.R_OK):
        return None
    
    f = open(path, "r")
    ret = f.read()
        
    f.close()
    return ret

# if a user has upgraded to a newer release of Red Hat but still
# has a systemid from their older release, they need to get an updated
# systemid from the RHN servers.  This takes care of that.
def maybeUpdateVersion():
    cfg = config.initUp2dateConfig()
    try:
        idVer = rpclib.xmlrpclib.loads(getSystemId())[0][0]['os_release']
    except:
        # they may not even have a system id yet.
        return 0

    systemVer = up2dateUtils.getVersion()
    
    if idVer != systemVer:
      s = rpcServer.getServer()
    
      try:
          newSystemId = rpcServer.doCall(s.registration.upgrade_version,
                                         getSystemId(), systemVer)
      except rpclib.Fault, f:
          raise up2dateErrors.CommunicationError(f.faultString)

      path = cfg["systemIdPath"]
      dir = path[:string.rfind(path, "/")]
      if not os.access(dir, os.W_OK):
          try:
              os.mkdir(dir)
          except:
              return 0
      if not os.access(dir, os.W_OK):
          return 0

      if os.access(path, os.F_OK):
          # already have systemid file there; let's back it up
          savePath = path + ".save"
          try:
              os.rename(path, savePath)
          except:
              return 0

      f = open(path, "w")
      f.write(newSystemId)
      f.close()
      try:
          os.chmod(path, 0600)
      except:
          pass



# allow to pass in a system id for use in rhnreg
# a bit of a kluge to make caps work correctly
def login(systemId=None):
    server = rpcServer.getServer()
    log = up2dateLog.initLog()

    # send up the capabality info
    headerlist = clientCaps.caps.headerFormat()
    for (headerName, value) in headerlist:
        server.add_header(headerName, value)

    if systemId == None:
        systemId = getSystemId()

    if not systemId:
        return None
        
    maybeUpdateVersion()
    log.log_me("logging into up2date server")

    # the list of caps the client needs
    caps = capabilities.Capabilities()

    global loginInfo
    try:
        li = rpcServer.doCall(server.up2date.login, systemId)
    except rpclib.Fault, f:
        if abs(f.faultCode) == 49:
#            print f.faultString
            raise up2dateErrors.AbuseError(f.faultString)
        else:
            raise f
    # set a static in the LoginInfo class...
    response_headers =  server.get_response_headers()
    caps.populate(response_headers)

    # figure out if were missing any needed caps
    caps.validate()

#    for i in response_headers.keys():
#        print "key: %s foo: %s" % (i, response_headers[i])

    if type(li) == DictType:
        if type(loginInfo) == DictType:
            # must retain the reference.
            loginInfo.update(li)
        else:
            # this had better be the initial login or we lose the reference.
            loginInfo = li
    else:
        loginInfo = None

    if loginInfo:
        log.log_me("successfully retrieved authentication token "
                   "from up2date server")

    log.log_debug("logininfo:", loginInfo)
    return loginInfo

def updateLoginInfo():
    log = up2dateLog.initLog()
    log.log_me("updating login info")
    # NOTE: login() updates the loginInfo object
    login()
    if not loginInfo:
        raise up2dateErrors.AuthenticationError("Unable to authenticate")
    return loginInfo


def getLoginInfo():
    global loginInfo
    try:
        loginInfo = loginInfo
    except NameError:
        loginInfo = None
    if loginInfo:
        return loginInfo
    # NOTE: login() updates the loginInfo object
    login()
    return loginInfo

