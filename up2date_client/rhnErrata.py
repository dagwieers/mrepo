#!/usr/bin/python
            
import rpm
import os   
import sys
sys.path.insert(0, "/usr/share/rhn/")
sys.path.insert(1,"/usr/share/rhn/up2date_client")

from rhpl.translate import _, N_
import up2dateErrors
import up2dateMessages
import rpmUtils
import up2dateAuth
import up2dateLog
import up2dateUtils
import rpcServer
import transaction
import config

from rhn import rpclib



def getAdvisoryInfo(pkg, warningCallback=None):
    log = up2dateLog.initLog()
    cfg = config.initUp2dateConfig()
    # no errata for non rhn use
    if not cfg['useRhn']:
        return None
        
    s = rpcServer.getServer()

    ts = transaction.initReadOnlyTransaction()
    mi = ts.dbMatch('Providename', pkg[0])
    if not mi:
	return None

    # odd,set h to last value in mi. mi has to be iterated
    # to get values from it...
    h = None
    for h in mi:
        break

    info = None

    # in case of package less errata that somehow apply
    if h:
        try:
            pkgName = "%s-%s-%s" % (h['name'],
                                h['version'],
                                h['release'])
            log.log_me("getAdvisoryInfo for %s" % pkgName)
            info = rpcServer.doCall(s.errata.getPackageErratum,
                                    up2dateAuth.getSystemId(),
                                    pkg)
        except rpclib.Fault, f:
            if warningCallback:
                warningCallback(f.faultString)
            return None
    
    if info:
        return info
    
    try:
        log.log_me("getAdvisoryInfo for %s-0-0" % pkg[0])
        info = rpcServer.doCall(s.errata.GetByPackage,
                      "%s-0-0" % pkg[0],
                      up2dateUtils.getVersion())
    except rpclib.Fault, f:
        if warningCallback:
            warningCallback(f.faultString)
        return None
    
    return info
