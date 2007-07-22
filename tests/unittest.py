#!/usr/bin/python

import os
import sys

import os.path
testdir = os.path.abspath(os.path.dirname(__file__))
parentdir = os.path.dirname(testdir)
sys.path.insert(1, parentdir)

import unittest
import mrepo
from mrepo import mySet

class TestmySet(unittest.TestCase):

    def setUp(self):
        self.s = mySet([1, 2, 3, 4])
        
    def test_initempty(self):
        s = mySet()
        self.assert_(isinstance(s, mrepo.mySet))

    def test_init(self):
        s = mySet([ 1, 2, 3, 4 ])
        self.assert_(isinstance(s, mrepo.mySet))
        self.assert_(repr(s) == 'mySet([1, 2, 3, 4])')

    def test_add(self):
        s = self.s
        self.assert_(9 not in s)
        s.add(9)
        self.assert_(9 in s)

    def test_eq(self):
        s1 = mySet([1, 2, 3])
        s2 = mySet([1, 2, 3])
        self.assertEqual(s1, s2)

    def test_difference(self):
        s1 = mySet([ 1, 2, 3, 4 ])
        s2 = mySet([ 1, 3 ])
        s = s1.difference(s2)
        self.assertEqual(s, mySet([2, 4]))

    def test_iter(self):
        s = mySet([1, 2, 3])
        l = []
        for i in s:
            l.append(i)
        self.assertEqual(l, [1, 2, 3])


class TestSync(unittest.TestCase):
    def setUp(self):
        pass
    def test_synciter1(self):
        left = (
            1, 2, 4, 5
            )
        right = (
            2, 3, 5, 6, 7
            )

        onlyright = []
        onlyleft = []
        keyequal = []
        for a, b in mrepo.synciter(left, right):
            # print "%s, %s, %s" % ( a, b, k )
            if a is None:
                onlyright.append(b)
            elif b is None:
                onlyleft.append(a)
            else:
                keyequal.append(a)

        self.assertEqual(onlyright, [3, 6, 7])
        self.assertEqual(onlyleft, [1, 4])
        self.assertEqual(keyequal, [2, 5])

    def test_synciter2(self):
        left = (
            (1, 'l1'), (2, 'l2'), (4, 'l4'), (5, 'l5')
            )
        right = (
            (2, 'r2'), (3, 'r3'), (5, 'r5'), (6, 'r6'), (7, 'r7')
            )

        onlyright = []
        onlyleft = []
        keyequal = []
        # key is the first element
        for a, b in mrepo.synciter(left, right, key = lambda x: x[0]):
            if a is None:
                onlyright.append(b)
            elif b is None:
                onlyleft.append(a)
            else:
                keyequal.append((a, b))

        self.assertEqual(onlyright, [(3, 'r3'), (6, 'r6'), (7, 'r7')])
        self.assertEqual(onlyleft, [(1, 'l1'), (4, 'l4')])
        self.assertEqual(keyequal, [((2, 'l2'), (2, 'r2')),
                                    ((5, 'l5'), (5, 'r5'))])

class Testlinksync(unittest.TestCase):
    def setUp(self):
        mkdir = os.mkdir
        pj= os.path.join
        self.tmpdir = tmpdir = pj(testdir, 'tmp')

        os.mkdir(tmpdir)

        # global "op" is needed by mrepo.Config, horrible for testing!
        
        class TestConfig:
            pass
        
        self.cf = cf = TestConfig()

        cf.srcdir = pj(tmpdir, 'src')
        cf.wwwdir = pj(tmpdir, 'dst')
       
        self.dist = mrepo.Dist('testdist', 'i386', cf)
        self.repo = repo = mrepo.Repo('testrepo', '', self.dist, cf)
        srcdir = repo.srcdir


        # tmp/src/testdist-i386/testrepo
        os.makedirs(srcdir)

        # tmp/dst/testdist-i386/RPMS.testrepo
        os.makedirs(repo.wwwdir)

        for f in xrange(4):
            __touch(pj(srcdir, str(f) + '.rpm'))
        __touch(pj(srcdir, 'dontsync.txt'))
                
        os.mkdir(pj(srcdir, 'a'))
        __touch(pj(srcdir, 'a', '2.rpm'))
        __touch(pj(srcdir, 'a', 'a.rpm'))

        self.localdir = localdir = pj(cf.srcdir, 'testdist-i386', 'local')
        os.makedirs(localdir)
        for f in ('local.rpm', 'dont_sync2.txt'):
            __touch(pj(localdir, f))

        # this should be the result when linksync'ing srcdir
        self.linkbase = linkbase = '../../../src/testdist-i386/testrepo'
        self.links = [
            ('0.rpm', pj(linkbase, '0.rpm')),
            ('1.rpm', pj(linkbase, '1.rpm')),
            ('2.rpm', pj(linkbase, '2.rpm')),
            ('3.rpm', pj(linkbase, '3.rpm')),
            ('a.rpm', pj(linkbase, 'a', 'a.rpm'))
            ]
        self.links.sort()

        
    def tearDown(self):
        isdir = os.path.isdir
        walk = os.path.walk
        pathjoin= os.path.join
        tmpdir = self.tmpdir
        # for safety-reasons:
        if tmpdir.count('/') < 3:
            raise "Will not remove tmpdir %s" % ( tmpdir, )

        def rmfile(arg, path, files):
            for file in files:
                # print "%s" % ( file, )
                f = pathjoin(path, file)
                if isdir(f):
                    walk(f, rmfile, None)
                    #print "rmdir %s" % ( f, )
                    os.rmdir(f)
                else:
                    #print "unlink %s" % ( f, )
                    os.unlink(f)

        os.path.walk(tmpdir, rmfile, None)
        os.rmdir(tmpdir)

    def readlinks(self, dir):
        """return a list of (linkname, linktarget) tuples for all files in a directory"""
        pj = os.path.join
        readlink = os.readlink
        return [ (l, readlink(pj(dir, l))) for l in os.listdir(dir) ]

    def genlinks(self, links, dir=''):
        if not dir:
            dir = self.repo.wwwdir
        pj = os.path.join
        symlink = os.symlink
        for name, target in links:
            symlink(target, pj(dir, name))

    def test_listrpms(self):
        srcdir = self.repo.srcdir
        actual = mrepo.listrpms(srcdir)
        pj= os.path.join
        target = [
            ('0.rpm', srcdir),
            ('1.rpm', srcdir),
            ('2.rpm', srcdir),
            ('2.rpm', pj(srcdir, 'a')),
            ('3.rpm', srcdir),
            ('a.rpm', pj(srcdir, 'a')),
            ]
        self.assertEqual(actual, target)

    def test_listrpms_rel(self):
        srcdir = self.repo.srcdir
        linkbase = self.linkbase
        actual = mrepo.listrpms(srcdir, relative = self.repo.wwwdir)
        pj= os.path.join
        target = [
            ('0.rpm', linkbase),
            ('1.rpm', linkbase),
            ('2.rpm', linkbase),
            ('2.rpm', pj(linkbase, 'a')),
            ('3.rpm', linkbase),
            ('a.rpm', pj(linkbase, 'a')),
            ]
        self.assertEqual(actual, target)

    def test_linksync_new(self):
        repo = self.repo
        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        target = self.links
        self.assertEqual(actual, target)

    def test_linksync_missing(self):
        repo = self.repo
        links = self.links[:]

        # remove some links
        del links[0]
        del links[2]
        del links[-1:]
        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        target = self.links
        actual.sort()
        self.assertEqual(actual, target)

    def test_linksync_additional(self):
        repo = self.repo
        links = self.links[:]

        pj = os.path.join
        # add some links
        links.insert(0, ('new1.rpm', pj(self.linkbase, 'new1.rpm')))
        links.insert(2, ('new2.rpm', pj(self.linkbase, 'new2.rpm')))
        links.append(('new3.rpm', pj(self.linkbase, 'new3.rpm')))
        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        actual.sort()
        target = self.links
        self.assertEqual(actual, target)

    def test_linksync_targetchange(self):
        repo = self.repo
        links = self.links[:]

        pj = os.path.join
        # add some links
        
        # basename != target basename
        links[1] = (links[1][0], pj(self.linkbase, 'illegal.rpm'))
        # different dir
        links[2] = (links[2][0], pj(self.linkbase, 'illegaldir', links[2][0]))
        # correct, but absolute link
        links[3] = (links[3][0], pj(repo.srcdir, links[3][0]))

        self.genlinks(links)

        self.dist.linksync(repo)

        actual = self.readlinks(repo.wwwdir)
        actual.sort()
        target = self.links
        self.assertEqual(actual, target)


    def test_linksync_mod(self):
        self.dist.linksync(self.repo)

def _Testlinksync__touch(filename):
    open(filename, 'a')


if __name__ == '__main__':
    # mrepo.op = mrepo.Options(('-vvvvv', '-c/dev/null'))
    mrepo.op = mrepo.Options(('-c/dev/null')) # should really get rid of this!
    unittest.main()
