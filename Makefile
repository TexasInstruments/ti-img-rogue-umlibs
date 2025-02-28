DESTDIR ?= ${DISCIMAGE}
TARGET_PRODUCT ?= j721e_linux
BUILD ?= release
WINDOW_SYSTEM ?= lws-generic
SRCDIR = ./targetfs/${TARGET_PRODUCT}/${WINDOW_SYSTEM}/${BUILD}

etcdir = etc
usrdir = usr
fwdir = lib

all: install

install:
	mkdir -p ${DESTDIR}/${etcdir}
	mkdir -p ${DESTDIR}/${usrdir}
	mkdir -p ${DESTDIR}/${fwdir}
	cp -ar ${SRCDIR}/${etcdir}/* ${DESTDIR}/${etcdir}
	cp -ar ${SRCDIR}/${usrdir}/* ${DESTDIR}/${usrdir}
	cp -ar ${SRCDIR}/${fwdir}/* ${DESTDIR}/${fwdir}
	install -Dm0644 pvrsrvkm.conf "${DESTDIR}/${usrdir}/lib/modprobe.d/pvrsrvkm.conf"

clean:
	@echo Remvoing unnecessary log files
	find targetfs -name '*.log' -delete
	@echo Remvoing files with invalid license
	rg -i 'confidential' targetfs/ --files-with-matches | \
		while IFS='\n' read -r line; do \
			echo "$$line" ; \
			rm "$$line" ; \
		done
	@echo Removing legacy sysvinit scripts
	find targetfs/ -wholename '*etc/init.d/*' -delete
	@echo Remvoing empty directories
	find targetfs/ -type d -empty -delete

.PHONY: all install clean
