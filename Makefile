DESTDIR ?= ${DISCIMAGE}
TARGET_PRODUCT ?= j721e_linux
BUILD ?= release
WINDOW_SYSTEM ?= lws-generic
SRCDIR = ./targetfs/${TARGET_PRODUCT}/${WINDOW_SYSTEM}/${BUILD}

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
