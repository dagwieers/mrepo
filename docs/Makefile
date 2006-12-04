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

cachedir = $(localstatedir)/cache/depo
htmldir = $(datadir)/depo/html
srcdir = $(localstatedir)/depo
wwwdir = $(localstatedir)/www/depo


all: .txt

.txt:
	asciidoc $@
