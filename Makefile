name = depo
version = $(shell awk '/^Version: / {print $$2}' $(name).spec)

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

all:
	@echo "There is nothing to be build. Try install !"

install:
	install -Dp -m0755 gensystemid $(DESTDIR)$(bindir)/gensystemid
	install -Dp -m0755 rhnget $(DESTDIR)$(bindir)/rhnget
	install -Dp -m0755 depo $(DESTDIR)$(bindir)/depo
	[ ! -f $(DESTDIR)$(sysconfdir)/depo.conf ] && install -D -m0600 config/depo.conf $(DESTDIR)$(sysconfdir)/depo.conf || :
	install -d -m0755 $(DESTDIR)$(sysconfdir)/depo.conf.d/
	install -Dp -m0644 config/httpd/depo.conf $(DESTDIR)$(httpddir)/depo.conf
	install -Dp -m0755 config/depo $(DESTDIR)$(initrddir)/depo

	install -d -m0755 $(DESTDIR)$(htmldir)
	install -p -m0644 html/* $(DESTDIR)$(htmldir)

	install -d -m0755 $(DESTDIR)$(srcdir)/all/
	install -d -m0755 $(DESTDIR)$(wwwdir)
	install -d -m0755 $(DESTDIR)$(cachedir)

	[ "$(DESTDIR)" -o ! -f "$(DESTDIR)$(sysconfdir)/cron.d/depo" ] && install -Dp -m0644 config/depo.cron $(DESTDIR)$(sysconfdir)/cron.d/depo || :
	
	install -Dp -m0644 config/depo.logrotate $(DESTDIR)$(sysconfdir)/logrotate.d/depo

	@if [ -z "$(DESTDIR)" -a -x "/sbin/chkconfig" ]; then \
		/sbin/chkconfig --add depo; \
	elif [ -z "$(DESTDIR)" -a -x "$(sbindir)/chkconfig" ]; then \
		$(sbindir)/chkconfig --add depo; \
	fi

docs:
	make -C docs

dist:
	find . ! -path '*/.svn*' | pax -d -w -x ustar -s ',^.,$(name)-$(version),' | bzip2 >../$(name)-$(version).tar.bz2

rpm: dist
	rpmbuild -tb --clean --rmsource --rmspec --define "_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm" --define "_rpmdir ../" ../$(name)-$(version).tar.bz2

srpm: dist
	rpmbuild -ts --clean --rmsource --rmspec --define "_rpmfilename %%{NAME}-%%{VERSION}-%%{RELEASE}.%%{ARCH}.rpm" --define "_srcrpmdir ../" ../$(name)-$(version).tar.bz2

clean:
	rm -f README*.html
