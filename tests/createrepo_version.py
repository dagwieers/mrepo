#! /usr/bin/python

import sys

def vercmp(a, b):
    al = a.split('.')
    bl = b.split('.')
    length = min(len(al), len(bl))
    for i in range(1, length):
        if cmp(al[i], bl[i]) < 0:
            return -1
        elif cmp(al[i], bl[i]) > 0:
            return 1
    return cmp(len(al), len(bl))

sys.path.append("/usr/share/createrepo")
import genpkgmetadata
print genpkgmetadata.__version__
sys.path.remove("/usr/share/createrepo")
del genpkgmetadata

print vercmp('0.4.4', '0.4.6')
print vercmp('0.4.8', '0.4.6')
print vercmp('0.4.6', '0.4.6')
print vercmp('0.4.6.0', '0.4.6')
print vercmp('0.4.6.1', '0.4.6')
