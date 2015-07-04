prefix = /usr
sysconfdir = /etc
bindir = $(prefix)/bin
sbindir = $(prefix)/sbin
libdir = $(prefix)/lib
datadir = $(prefix)/share
mandir = $(datadir)/man
localstatedir = /var

httpddir = $(sysconfdir)/httpd/conf.d
initrddir = $(sysconfdir)/rc.d/init.d

cachedir = $(localstatedir)/cache/mrepo
htmldir = $(datadir)/mrepo/html
srcdir = $(localstatedir)/mrepo
wwwdir = $(localstatedir)/www/mrepo

all: *.adoc

.adoc:
	asciidoc $@
