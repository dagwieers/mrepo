# $Id: mrepo.spec 2103 2004-08-26 10:38:07Z dag $
# Authority: dag
# Upstream: Dag Wieers <dag$wieers,com>

Summary: Set up repositories from various sources (ISO, RHN, YOU, rsync, http, ftp, ...)
Name: mrepo
Version: 0.8.8
Release: 1
License: GPL
Group: System Environment/Base
URL: http://dag.wieers.com/home-made/mrepo/

Packager: Dag Wieers <dag@wieers.com>
Vendor: Dag Apt Repository, http://dag.wieers.com/apt/

Source: http://dag.wieers.com/home-made/mrepo/mrepo-%{version}.tar.bz2
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-root

BuildArch: noarch
BuildRequires: /usr/bin/python2
Requires: createrepo
Requires: python >= 2.0
Requires: pyOpenSSL
Obsoletes: yam <= %{version}

%description
mrepo builds a local Apt/Yum RPM repository from local ISO files,
downloaded updates and extra packages from RHN and 3rd party
repositories.

It can download all updates and extras automatically, creates
the repository structure and meta-data, enables HTTP access to 
the repository and creates a directory-structure for remote
network installations using PXE/TFTP.

mrepo supports ftp, http, sftp, rsync, Red Hat Network and YaST
Online Update and other download methods.

With mrepo, you can enable your laptop or a local server to provide
updates for the whole network and provide the proper files to
allow installations via the network.

%prep
%setup

%{__perl} -pi.orig -e 's|^(VERSION)\s*=\s*.+$|$1 = "%{version}"|' mrepo

%{__cat} <<EOF >config/mrepo.cron
### Enable this if you want mrepo to daily synchronize
### your distributions and repositories at 2:30am.
#30 2 * * * root /usr/bin/mrepo -q -ug
EOF

%{__cat} <<EOF >config/mrepo.conf
### Configuration file for mrepo

### The [main] section allows to override mrepo's default settings
### The mrepo-example.conf gives an overview of all the possible settings
[main]
srcdir = /var/mrepo
wwwdir = /var/www/mrepo
confdir = /etc/mrepo.conf.d
arch = i386

mailto = root@localhost
smtp-server = localhost

#rhnlogin = username:password

### Any other section is considered a definition for a distribution
### You can put distribution sections in /etc/mrepo.conf.d/
### Examples can be found in the documentation at:
###     %{_docdir}/%{name}-%{version}/dists/.
EOF

%build

%install
%{__rm} -rf %{buildroot}
%{__make} install DESTDIR="%{buildroot}"

%preun
if [ $1 -eq 0 ]; then
    /service mrepo stop &>/dev/null || :
    /sbin/chkconfig --del mrepo
fi

%post
/sbin/chkconfig --add mrepo

#%postun
#/sbin/service mrepo condrestart &>/dev/null || :

%clean
%{__rm} -rf %{buildroot}

%files
%defattr(-, root, root, 0755)
%doc AUTHORS ChangeLog COPYING README THANKS TODO config/* docs/
%config(noreplace) %{_sysconfdir}/cron.d/mrepo
%config(noreplace) %{_sysconfdir}/httpd/conf.d/mrepo.conf
%config(noreplace) %{_sysconfdir}/logrotate.d/mrepo
%config(noreplace) %{_sysconfdir}/mrepo.conf
%config(noreplace) %{_sysconfdir}/mrepo.conf.d/
%config %{_initrddir}/mrepo
%{_bindir}/gensystemid
%{_bindir}/mrepo
%{_bindir}/rhnget
%{_bindir}/youget
%{_datadir}/mrepo/
%{_localstatedir}/cache/mrepo/
%{_localstatedir}/mrepo/
%{_localstatedir}/www/mrepo/

%changelog
* Mon Sep 19 2011 Dag Wieers <dag@wieers.com> - 0.8.8-1
- Updated to release 0.8.8.

* Sat Feb 06 2010 Dag Wieers <dag@wieers.com> - 0.8.7-1
- Updated to release 0.8.7.

* Mon Oct 06 2008 Dag Wieers <dag@wieers.com> - 0.8.6-1
- Updated to release 0.8.6.

* Fri Aug 15 2008 Dag Wieers <dag@wieers.com> - 0.8.5-1
- Updated to release 0.8.5.

* Wed Dec 13 2006 Dag Wieers <dag@wieers.com> - 0.8.4-1
- Updated to release 0.8.4.
- Package renamed from yam to mrepo.

* Sun Oct 15 2006 Dag Wieers <dag@wieers.com> - 0.8.3-1
- Updated to release 0.8.3.

* Tue Sep 19 2006 Dag Wieers <dag@wieers.com> - 0.8.2-1
- Updated to release 0.8.2.

* Tue Aug 22 2006 Dag Wieers <dag@wieers.com> - 0.8.1-1
- Updated to release 0.8.1.

* Thu Mar 09 2006 Dag Wieers <dag@wieers.com> - 0.8.0-1
- Updated to release 0.8.0.

* Fri Mar 25 2005 Dag Wieers <dag@wieers.com> - 0.7.3-1
- Updated to release 0.7.3.

* Fri Jan 07 2005 Dag Wieers <dag@wieers.com> - 0.7.2-2
- Add %%post and %%postun scripts. (Bert de Bruijn)

* Sun Nov 28 2004 Dag Wieers <dag@wieers.com> - 0.7.2-1
- Updated to release 0.7.2.

* Sun Nov 07 2004 Dag Wieers <dag@wieers.com> - 0.7.1-1
- Updated to release 0.7.1.

* Sat Sep 11 2004 Dag Wieers <dag@wieers.com> - 0.7.0-1
- Updated to release 0.7.0.

* Thu Aug 26 2004 Dag Wieers <dag@wieers.com> - 0.6.1-1
- Updated to release 0.6.1.

* Wed Aug 25 2004 Dag Wieers <dag@wieers.com> - 0.6-2
- Updated to release 0.6.
- Fix a version problem.

* Thu Aug 19 2004 Dag Wieers <dag@wieers.com> - 0.5-1
- Updated to release 0.5.

* Wed May 19 2004 Dag Wieers <dag@wieers.com> - 0.3-1
- Updated to release 0.3.

* Fri May 14 2004 Dag Wieers <dag@wieers.com> - 0.2-1
- Initial package. (using DAR)
