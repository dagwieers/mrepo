#! /usr/bin/python

import xmlrpclib
from optparse import OptionParser

def GetOptions():
    parser=OptionParser()

    parser.add_option("-d", "--delete",
        action="store_true", dest="delete", default=False,
        help = "Deletes system, group, or channel")

    parser.add_option("-s", "--system",
        action="store_true", dest="system", default=False,
        help="Used when performing operations to machines subscribe to RHN.")

        parser.add_option("-q", "--query",
        action="store_true", dest="query", default=False,
        help="Used in conjuction with -s to show subscribed systems.")


    parser.add_option("-n", "--name",dest="hostname",
        help="hostname of machine to perform operation on.", metavar=" hostname")

    global options
    (options,args) = parser.parse_args()

    return options.delete, options.system, options.hostname

def getSystemIds():
    systems = server.system.list_user_systems(session)
    return systems

def deleteSystem(sid):
    try:
        print "attempting to remove SID %s... with hostname of %s" % (sid,options.hostname)
            delete = server.system.delete_systems(session,sid)
        print "Deletion of %s successfull." % (options.hostname)
    except:
        print "Deletion of %s unsuccessfull." % (options.hostname)

host = 'xmlrpc.rhn.redhat.com'
username='IBM_RHN'
password = 'think'
protocol = 'https'
url = "%s://%s/rpc/api" %(protocol,host)

server = xmlrpclib.ServerProxy(url)
session = server.auth.login(username,password)

GetOptions()

if options.system:
    systems = getSystemIds()
    if options.query:
        if len(systems) == 0:
            print "No systems are subscribed to RHN."
        else:
            print "These machines are subscribed to RHN\n\n"
            print "Name: \t\tcheckin: \t\t\tsid: "
                for vals in systems:
                print "%s\t\t%s\t\t%s" % (vals['name'],vals['last_checkin'],vals['id'])

    if options.delete:
        for vals in systems:
            if vals['name'] == options.hostname:
                deleteSystem(vals['id'])
