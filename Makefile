DESTDIR ?= ${DISCIMAGE}
TARGET_PRODUCT ?= dra822_linux
BUILD ?= release
SRCDIR = ./targetfs/${TARGET_PRODUCT}/${BUILD}

etcdir = etc
usrdir = usr
fwdir = lib

all:

install:
	mkdir -p ${DESTDIR}/${etcdir}
	mkdir -p ${DESTDIR}/${usrdir}
	mkdir -p ${DESTDIR}/${fwdir}
	cp -ar ${SRCDIR}/${etcdir}/* ${DESTDIR}/${etcdir}
	cp -ar ${SRCDIR}/${usrdir}/* ${DESTDIR}/${usrdir}
	cp -ar ${SRCDIR}/${fwdir}/* ${DESTDIR}/${fwdir}
