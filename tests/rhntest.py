#!/usr/bin/python -u

import sys, os, rpm, string

sys.path.insert(0, "/usr/share/rhn/")
from up2date_client import up2dateAuth
from up2date_client import up2date
from up2date_client import config
from up2date_client import repoDirector
from up2date_client import rpcServer
from up2date_client import wrapperUtils
from up2date_client import rhnChannel

def getSystemId(dist):
    return open('/var/yam/'+dist+'/rhn-systemid').read(131072)

def subscribedChannels():
    ret = []
    debugprint(ret)
    li = up2dateAuth.getLoginInfo()
    if not li: return []
        
    channels = li.get('X-RHN-Auth-Channels')
    if not channels: return []

    for label, version, t, t in channels:
        ret.append(rhnChannel.rhnChannel(label = label, version = version, type = 'up2date', url = cfg['serverURL']))

    return ret

def debugprint(obj):
    if '__name__' in dir(obj):
        print 'DEBUGPRINT object %s' % obj.__name__
        print '  repr', obj
        print '  dir', dir(obj)
    elif '__class__' in dir(obj):
        print 'DEBUGPRINT class %s' % obj.__class__
        print '  repr', obj
        print '  dir', dir(obj)
        try: print '  keys', obj.keys()
        except: print 'FAILED'
        try:
            print '  list', 
            for i in obj: print i,
        except: print 'FAILED'
    elif '__module__' in dir(obj):
        print 'DEBUGPRINT module %s' % obj.__module__
        print '  repr', obj
        print '  dir', dir(obj)
    else:
        print 'DEBUGPRINT unknown ', dir(obj)
        print '  repr', obj
        print '  dir', dir(obj)
    print

registered = getSystemId('rhel3as-i386')
up2dateAuth.updateLoginInfo()
cfg = config.initUp2dateConfig()
repos = repoDirector.initRepoDirector()

### Print channels
debugprint(rhnChannel)
debugprint(rhnChannel.rhnChannelList())
debugprint(rhnChannel.rhnChannelList().list)
debugprint(rhnChannel.getChannels(force=1))
debugprint(rhnChannel.getChannels(force=1).list)
for channel in rhnChannel.rhnChannelList().list: print channel['label'],
print

for channel in rhnChannel.getChannels(force=1).list: print channel['label'],
print

for channel in repos.channels.list: print channel['label'],
print

for channel in subscribedChannels(): print channel['label'],
print
#sys.exit(0)

debugprint(up2dateAuth.getLoginInfo())

for channel in subscribedChannels():
    cfg['storageDir'] = '/var/yam/rhel4as-i386/'+channel['label']
    try: os.makedirs(cfg['storageDir'], 0755)
    except: pass
    print channel['label'], channel['type'], channel['url'], channel['version']
    package_list, type = rpcServer.doCall(repos.listPackages, channel, None, None)
    print channel['label'], 'has', len(package_list), 'packages'
#   for name, version, release, test, arch, test, label in package_list:
#       print name,
#   for pkg in package_list:
#       name, version, release, test, arch, test, label = pkg
#       rpcServer.doCall(repos.getPackage, pkg)
#       rpcServer.doCall(repos.getPackage, pkg, wrapperUtils.printPkg, wrapperUtils.printRetrieveHash)

### Print packages
#printList(rhnPackageInfo.getAvailableAllArchPackageList(), cfg['showChannels'])
#print rhnPackageInfo.getAvailableAllArchPackageList()
