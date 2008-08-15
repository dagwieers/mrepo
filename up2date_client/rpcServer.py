#!/usr/bin/python
#
# $Id: rpcServer.py 89799 2006-03-31 15:28:28Z pkilambi $

import os
import sys
import config
import types
import socket
import string
import time
import httplib
import urllib2

import clientCaps
import up2dateLog
import up2dateErrors 
import up2dateAuth 
import up2dateUtils
import repoDirector

#import wrapperUtils
from rhn import rpclib
    
from rhpl.translate import _, N_
            

def stdoutMsgCallback(msg):
    print msg


def hasSSL():
    return hasattr(socket, "ssl")

class RetryServer(rpclib.Server):
    def foobar(self):
        pass

    def addServerList(self, serverList):
        self.serverList = serverList

    def _request1(self, methodname, params):
        self.log = up2dateLog.initLog()
        while 1:
            try:
                ret = self._request(methodname, params)
            except rpclib.InvalidRedirectionError:
#                print "GOT a InvalidRedirectionError"
                raise
            except rpclib.Fault:
		raise 
            except:
                server = self.serverList.next()
                if server == None:
                    # since just because we failed, the server list could
                    # change (aka, firstboot, they get an option to reset the
                    # the server configuration) so reset the serverList
                    self.serverList.resetServerIndex()
                    raise

                msg = "An error occured talking to %s:\n" % self._host
                msg = msg + "%s\n%s\n" % (sys.exc_type, sys.exc_value)
                msg = msg + "Trying the next serverURL: %s\n" % self.serverList.server()
                self.log.log_me(msg)
                # try a different url

                # use the next serverURL
                import urllib
                typ, uri = urllib.splittype(self.serverList.server())
                typ = string.lower(typ)
                if typ not in ("http", "https"):
                    raise InvalidRedirectionError(
                        "Redirected to unsupported protocol %s" % typ)

#                print "gha2"
                self._host, self._handler = urllib.splithost(uri)
                self._orig_handler = self._handler
                self._type = typ
                if not self._handler:
                    self._handler = "/RPC2"
                self._allow_redirect = 1
                continue
            # if we get this far, we succedded
            break
        return ret

    
    def __getattr__(self, name):
        # magic method dispatcher
        return rpclib.xmlrpclib._Method(self._request1, name)
                

# uh, yeah, this could be an iterator, but we need it to work on 1.5 as well
class ServerList:
    def __init__(self, serverlist=[]):
        self.serverList = serverlist
        self.index = 0
        
    def server(self):
        self.serverurl = self.serverList[self.index]
        return self.serverurl


    def next(self):
        self.index = self.index + 1
        if self.index >= len(self.serverList):
            return None
        return self.server()

    def resetServerList(self, serverlist):
        self.serverList = serverlist
        self.index = 0

    def resetServerIndex(self):
        self.index = 0

# singleton for the ServerList
def initServerList(servers):
    global server_list
    try:
        server_list = server_list
    except NameError:
        server_list = None

    if server_list == None:
        server_list = ServerList(servers)

    # if we've changed the config, we need need to
    # update the server_list as well. Not really needed
    # in the app, but makes testing cleaner
    cfg = config.initUp2dateConfig()
    sl = cfg['serverURL']
    if type(sl) == type(""):
        sl  = [sl]
        
    if sl != server_list.serverList:
        server_list = ServerList(servers)

    return server_list

def getServer(refreshCallback=None):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
# Where do we keep the CA certificate for RHNS?
# The servers we're talking to need to have their certs
# signed by one of these CA.
    ca = cfg["sslCACert"]
    if type(ca) == type(""):
    	ca = [ca]

    rhns_ca_certs = ca or ["/usr/share/rhn/RHNS-CA-CERT"]
    if cfg["enableProxy"]:
        proxyHost = up2dateUtils.getProxySetting()
    else:
        proxyHost = None

    if hasSSL():
        serverUrls = cfg["serverURL"]
    else:
        serverUrls = cfg["noSSLServerURL"]

    # the standard is to be a string, so list-a-fy in that case
    if type(serverUrls) == type(""):
        serverUrls = [serverUrls]

    serverList = initServerList(serverUrls)

    proxyUser = None
    proxyPassword = None
    if cfg["enableProxyAuth"]:
        proxyUser = cfg["proxyUser"] or None
        proxyPassword = cfg["proxyPassword"] or None

    lang = None
    for env in 'LANGUAGE', 'LC_ALL', 'LC_MESSAGES', 'LANG':
        if os.environ.has_key(env):
            if not os.environ[env]:
                # sometimes unset
                continue
            lang = string.split(os.environ[env], ':')[0]
            lang = string.split(lang, '.')[0]
            break


    s = RetryServer(serverList.server(),
                    refreshCallback=refreshCallback,
                    proxy=proxyHost,
                    username=proxyUser,
                    password=proxyPassword)
    s.addServerList(serverList)

    s.add_header("X-Up2date-Version", up2dateUtils.version())
    
    if lang:
        s.setlang(lang)

    # require RHNS-CA-CERT file to be able to authenticate the SSL connections
    for rhns_ca_cert in rhns_ca_certs:
        if not os.access(rhns_ca_cert, os.R_OK):
	    msg = "%s: %s" % (_("ERROR: can not find RHNS CA file:"),
				 rhns_ca_cert)
            log.log_me("%s" % msg)
	    print msg
            sys.exit(-1)

        # force the validation of the SSL cert
        s.add_trusted_cert(rhns_ca_cert)

    clientCaps.loadLocalCaps()

    # send up the capabality info
    headerlist = clientCaps.caps.headerFormat()
    for (headerName, value) in headerlist:
        s.add_header(headerName, value)
    return s

# inherinet the retry/failover from RetryServer here
class RetryGETServer(rpclib.GETServer, RetryServer):
    pass


# FIXME: doCall should probabaly be a method
# of a higher level server object
def doCall(method, *args, **kwargs):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
    ret = None

    attempt_count = 1
    attempts = cfg["networkRetries"] or 5

    while 1:
        failure = 0
        ret = None        
        try:
            ret = apply(method, args, kwargs)
        except KeyboardInterrupt:
            raise up2dateErrors.CommunicationError(_(
                "Connection aborted by the user"))
        # if we get a socket error, keep tryingx2
        except (socket.error, socket.sslerror), e:
            log.log_me("A socket error occurred: %s, attempt #%s" % (
                e, attempt_count))
            if attempt_count >= attempts:
                if len(e.args) > 1:
                    raise up2dateErrors.CommunicationError(e.args[1])
                else:
                    raise up2dateErrors.CommunicationError(e.args[0])
            else:
                failure = 1
        except httplib.IncompleteRead:
            print "httplib.IncompleteRead" 
            raise up2dateErrors.CommunicationError("httplib.IncompleteRead")

        except urllib2.HTTPError, e:
            msg = "\nAn HTTP error occurred:\n"
            msg = msg + "URL: %s\n" % e.filename
            msg = msg + "Status Code: %s\n" % e.code
            msg = msg + "Error Message: %s\n" % e.msg
            log.log_me(msg)
            raise up2dateErrors.CommunicationError(msg)
        
        except rpclib.ProtocolError, e:
            
            log.log_me("A protocol error occurred: %s , attempt #%s," % (
                e.errmsg, attempt_count))
            (errCode, errMsg) = rpclib.reportError(e.headers)
            reset = 0
            if abs(errCode) == 34:
                log.log_me("Auth token timeout occurred\n errmsg: %s" % errMsg)
                # this calls login, which in tern calls doCall (ie,
                # this function) but login should never get a 34, so
                # should be safe from recursion

                rd = repoDirector.initRepoDirector()
                rd.updateAuthInfo()
                reset = 1

            # the servers are being throttle to pay users only, catch the
            # exceptions and display a nice error message
            if abs(errCode) == 51:
                log.log_me(_("Server has refused connection due to high load"))
                raise up2dateErrors.CommunicationError(e.errmsg)
            # if we get a 404 from our server, thats pretty
            # fatal... no point in retrying over and over. Note that
            # errCode == 17 is specific to our servers, if the
            # serverURL is just pointing somewhere random they will
            # get a 0 for errcode and will raise a CommunicationError
            if abs(errCode) == 17:
		#in this case, the args are the package string, so lets try to
		# build a useful error message
                if type(args[0]) == type([]):
                    pkg = args[0]
                else:
                    pkg=args[1]
                    
                if type(pkg) == type([]):
                    pkgName = "%s-%s-%s.%s" % (pkg[0], pkg[1], pkg[2], pkg[4])
                else:
                    pkgName = pkg
		msg = "File Not Found: %s\n%s" % (pkgName, errMsg)
		log.log_me(msg)
                raise up2dateErrors.FileNotFoundError(msg)
                
            if not reset:
                if attempt_count >= attempts:
                    raise up2dateErrors.CommunicationError(e.errmsg)
                else:
                    failure = 1
            
        except rpclib.ResponseError:
            raise up2dateErrors.CommunicationError(
                "Broken response from the server.")

        if ret != None:
            break
        else:
            failure = 1


        if failure:
            # rest for five seconds before trying again
            time.sleep(5)
            attempt_count = attempt_count + 1
        
        if attempt_count > attempts:
            print "busted2"
            print method
            raise up2dateErrors.CommunicationError("The data returned from the server was incomplete")

    return ret
    
