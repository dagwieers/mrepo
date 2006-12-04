isodir=/mnt/iso
xnldir=/var/www/xnl
tftpdir=/tftpboot/xnl
pxelinux=/usr/lib/syslinux/pxelinux.0

RHNUSER=dag@wieers.com
LOGNAME=$(shell logname)

all: mount-all update-all build-all pxe-all

umount: umount-all
mount: mount-all
update: update-all
pxe: pxe-all
build: build-all

mount-all: umount-all m-fc1-i386 m-fc1-AMD64 m-tao1-i386 m-rhas3-i386 m-rhes3-i386 m-rhws3-i386 m-rhas3-AMD64 m-rhas21 m-rh73
#mount-all: umount-all m-fc1-i386 m-rhas3-i386 m-rh73
### Disable unsupported distributions (rh62, rh73)
#update-all: u-fc1-i386 u-fc1-AMD64
update-all: u-fc1-i386 u-tao1-i386 u-rh73
build-all: b-fc1-i386 b-fc1-AMD64 b-tao1-i386 b-rhas3-i386 b-rhes3-i386 b-rhws3-i386 b-rhas3-AMD64 b-rhas21
#build-all: b-fc1-i386 b-tao3-i386 b-rhas3-i386 b-rh73

pxe-all: x-fc1-i386 x-fc1-AMD64 x-tao1-i386 x-rhas3-i386 x-rhes3-i386 x-rhws3-i386 x-rhas3-AMD64 x-rhas21 x-rh73

umount-all:
	-umount $(xnldir)/*/disc?/ &>/dev/null
	-@for i in $(shell seq 1 256); do losetup -d /dev/loop$$i; done &>/dev/null

### Red Hat Fedora Core 1 (i386)
m-fc1-i386: dist=$(subst m-,,$@)
m-fc1-i386:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3}
	mount -o loop $(isodir)/yarrow-i386-disc1.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/yarrow-i386-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/yarrow-i386-disc3.iso $(xnldir)/$(dist)/disc3/

u-fc1-i386: dist=$(subst u-,,$@)
u-fc1-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r http://ayo.freshrpms.net/fedora/linux/1/i386/RPMS.updates/ $(xnldir)/$(dist)/RPMS.updates'

b-fc1-i386: dist=$(subst b-,,$@)
b-fc1-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3}/Fedora/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-fc1-i386: dist=$(subst x-,,$@)
x-fc1-i386:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### TaoLinux 1 (i386)
m-tao1-i386: dist=$(subst m-,,$@)
m-tao1-i386:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3}
	mount -o loop $(isodir)/mooch-i386-disc1.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/mooch-i386-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/mooch-i386-disc3.iso $(xnldir)/$(dist)/disc3/

u-tao1-i386: dist=$(subst u-,,$@)
u-tao1-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r http://dist.taolinux.org/tao-1.0/updates/ $(xnldir)/$(dist)/RPMS.updates'

b-tao1-i386: dist=$(subst b-,,$@)
b-tao1-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3}/Tao/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-tao1-i386: dist=$(subst x-,,$@)
x-tao1-i386:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Fedora Core 1 (x86_64)
m-fc1-AMD64: dist=$(subst m-,,$@)
m-fc1-AMD64:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3}
	mount -o loop $(isodir)/yarrow-x86_64-disc1.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/yarrow-x86_64-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/yarrow-x86_64-disc3.iso $(xnldir)/$(dist)/disc3/

u-fc1-AMD64: dist=$(subst u-,,$@)
u-fc1-AMD64:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r http://ayo.freshrpms.net/fedora/linux/1/x86_64/RPMS.updates/ $(xnldir)/$(dist)/RPMS.updates'

b-fc1-AMD64: dist=$(subst b-,,$@)
b-fc1-AMD64:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3}/Fedora/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-fc1-AMD64: dist=$(subst x-,,$@)
x-fc1-AMD64:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Enterprise Linux 3 (i386)
m-rhel3-i386: dist=$(subst m-,,$@)
m-rhel3-i386:
	mkdir -p $(xnldir)/$(dist)/disc{2,3,4}/
	mount -o loop $(isodir)/rhel-3-i386-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/rhel-3-i386-disc3.iso $(xnldir)/$(dist)/disc3/
	mount -o loop $(isodir)/rhel-3-i386-disc4.iso $(xnldir)/$(dist)/disc4/

	mkdir -p $(xnldir)/$(dist)/RPMS.extras/


### Red Hat Advanced Server 3 (i386)
m-rhas3-i386: dist=$(subst m-,,$@)
m-rhas3-i386: m-rhel3-i386
	mkdir -p $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/rhel-3-U1-i386-as-disc1.iso $(xnldir)/$(dist)/disc1/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/ $(xnldir)/$(dist)/

b-rhas3-i386: dist=$(subst b-,,$@)
b-rhas3-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.os,.updates}/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/rhel3-i386/RPMS.extras/ $(xnldir)/$(dist)/

	ln -sf $(xnldir)/$(dist)/disc1/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/disc1/RedHat/Updates/*.rpm $(xnldir)/$(dist)/RPMS.updates/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rhas3-i386: dist=$(subst x-,,$@)
x-rhas3-i386:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Enterprise Server 3 (i386)
m-rhes3-i386: dist=$(subst m-,,$@)
m-rhes3-i386: m-rhel3-i386
	mkdir -p $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/rhel-3-U1-i386-es-disc1.iso $(xnldir)/$(dist)/disc1/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/ $(xnldir)/$(dist)/

b-rhes3-i386: dist=$(subst b-,,$@)
b-rhes3-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/rhel3-i386/RPMS.extras/ $(xnldir)/$(dist)/

	ln -sf $(xnldir)/$(dist)/disc1/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/disc1/RedHat/Updates/*.rpm $(xnldir)/$(dist)/RPMS.updates/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rhes3-i386: dist=$(subst x-,,$@)
x-rhes3-i386:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Work Station 3 (i386)
m-rhws3-i386: dist=$(subst m-,,$@)
m-rhws3-i386: m-rhel3-i386
	mkdir -p $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/rhel-3-U1-i386-ws-disc1.iso $(xnldir)/$(dist)/disc1/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/ $(xnldir)/$(dist)/

b-rhws3-i386: dist=$(subst b-,,$@)
b-rhws3-i386:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/rhel3-i386/disc{2,3,4}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/rhel3-i386/RPMS.extras/ $(xnldir)/$(dist)/

	ln -sf $(xnldir)/$(dist)/disc1/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/disc1/RedHat/Updates/*.rpm $(xnldir)/$(dist)/RPMS.updates/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rhws3-i386: dist=$(subst x-,,$@)
x-rhws3-i386:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Advanced Server 3 (AMD64)
m-rhas3-AMD64: dist=$(subst m-,,$@)
m-rhas3-AMD64:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3,4}/
	mount -o loop $(isodir)/rhel-3-U1-AMD64-as-disc1.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/rhel-3-AMD64-as-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/rhel-3-AMD64-as-disc3.iso $(xnldir)/$(dist)/disc3/
	mount -o loop $(isodir)/rhel-3-AMD64-as-disc4.iso $(xnldir)/$(dist)/disc4/

u-rhas3-AMD64:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r https://$(RHNUSER)@rhn.redhat.com/ $(xnldir)/rh73/RPMS.updates'

b-rhas3-AMD64: dist=$(subst b-,,$@)
b-rhas3-AMD64:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3,4}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/disc1/RedHat/Updates/*.rpm $(xnldir)/$(dist)/RPMS.updates/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rhas3-AMD64: dist=$(subst x-,,$@)
x-rhas3-AMD64:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/{initrd.img,vmlinuz} $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat 7.3
m-rh73: dist=$(subst m-,,$@)
m-rh73:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3}
	mount -o loop $(isodir)/valhalla-i386-disc1.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/valhalla-i386-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/valhalla-i386-disc3.iso $(xnldir)/$(dist)/disc3/

u-rh73: dist=$(subst u-,,$@)
u-rh73:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r http://ayo.freshrpms.net/redhat/7.3/i386/RPMS.updates/ $(xnldir)/$(dist)/RPMS.updates'

b-rh73: dist=$(subst b-,,$@)
b-rh73:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rh73: dist=$(subst x-,,$@)
x-rh73:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/initrd-everything.img $(tftpdir)/$(dist)/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/vmlinuz $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat Advanced Server 2.1
m-rhas21: dist=$(subst m-,,$@)
m-rhas21:
	mkdir -p $(xnldir)/$(dist)/disc{1,2,3}/
	mount -o loop $(isodir)/RHEL2.1AS-U3-re1215.RC1.0-i386-disc1-update.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/RHEL2.1AS-U3-re1215.RC1.0-i386-disc2.iso $(xnldir)/$(dist)/disc2/
	mount -o loop $(isodir)/RHEL2.1AS-U3-re1215.RC1.0-i386-disc3.iso $(xnldir)/$(dist)/disc3/

b-rhas21: dist=$(subst b-,,$@)
b-rhas21:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2,3}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras

x-rhas21: dist=$(subst x-,,$@)
x-rhas21:
	mkdir -p $(tftpdir)/$(dist)/pxelinux.cfg/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/initrd-everything.img $(tftpdir)/$(dist)/
	cp -a $(xnldir)/$(dist)/disc1/images/pxeboot/vmlinuz $(tftpdir)/$(dist)/
	cp -a $(pxelinux) $(tftpdir)/$(dist)/


### Red Hat 6.2
m-rh62: dist=$(subst m-,,$@)
m-rh62:
	mkdir -p $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/redhat-6.2-i386.iso $(xnldir)/$(dist)/disc1/
	mount -o loop $(isodir)/Powertools-6.2-i386.iso $(xnldir)/$(dist)/disc2/

u-rh62: dist=$(subst u-,,$@)
u-rh62:
	mkdir -p $(xnldir)/$(dist)/RPMS.updates/
	lftp -c 'mirror -r ftp://ftp.redhat.com/pub/redhat/linux/updates/6.2/en/os/*/ $(xnldir)/$(dist)/RPMS.updates'
	lftp -c 'mirror -r ftp://ftp.redhat.com/pub/redhat/linux/updates/6.2/en/powertools/*/ $(xnldir)/$(dist)/RPMS.updates'

b-rh62: dist=$(subst b-,,$@)
b-rh62:
	mkdir -p $(xnldir)/$(dist)/RPMS{,.extras,.os,.updates}/
	ln -sf $(xnldir)/$(dist)/disc{1,2}/RedHat/RPMS/*.rpm $(xnldir)/$(dist)/RPMS.os/
	ln -sf $(xnldir)/$(dist)/RPMS.{os,updates,extras}/*.rpm $(xnldir)/$(dist)/RPMS/

	genbasedir --progress --flat --bloat --bz2only $(xnldir)/$(dist) os updates extras


delta:
	rsync -avHl --progress --delete-after -e "/usr/bin/ssh -oCompression=no" $(xnldir)/* $(LOGNAME)@delta.be.ibm.com:$(xnldir)

cars:
	nc -i 1 esni.be.ibm.com 259

esni:
	rsync -avHL --progress --delete-after -e "/usr/bin/ssh -oCompression=no" $(xnldir)/* be03774@aix.be.ibm.com:/var/ftp/pub/linux
