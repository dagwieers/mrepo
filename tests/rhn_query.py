#! /usr/bin/python

import xmlrpclib
from optparse import OptionParser


host = 'xmlrpc.rhn.redhat.com'
username='rhnname'
password = 'rhnpass'
protocol = 'https'
url = "%s://%s/rpc/api" %(protocol,host)

server = xmlrpclib.ServerProxy(url)
session = server.auth.login(username, password)

systems = server.system.list_user_systems(session)
if len(systems) == 0:
    print "No systems are subscribed to RHN."
else:
    print "These machines are subscribed to RHN\n\n"
    print "Name: \t\tcheckin: \t\t\tsid: "
        for vals in systems:
        print "%s\t\t%s\t\t%s" % (vals['name'],vals['last_checkin'],vals['id'])

methods = server.system.listMethods()
print methods

for method in methods:
    print server.system.methodHelp(method)
