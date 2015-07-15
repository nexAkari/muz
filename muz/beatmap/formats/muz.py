# -*- coding: utf-8 -*-

from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import logging, shutil, os
log = logging.getLogger(__name__)

import muz
import muz.vfs
import muz.beatmap

name = "μz beatmap"
extensions = ["beatmap"]
inferExtensions = extensions
locations = ["beatmaps"]

VERSION = "1"

class ParseError(Exception):
    pass

def read(fobj, filename, bare=False, options=None):
    buf = b""
    bmap = muz.beatmap.Beatmap(None, 1)
    initialized = False
    essentialParsed = False
    maxnotes = 0
    lastnote = None

    while True:
        byte = fobj.read(1)

        if not byte:
            break

        if byte in (b'\r', b'\n'):
            if buf:
                buf = buf.decode('utf-8')

                if buf[0] != '#':
                    s, args = buf.split(' ', 1)

                    if s == "version":
                        if initialized:
                            log.warning("duplicate 'version' statement ignored")
                        else:
                            initialized = True
                            if args != VERSION:
                                log.warning("unsupported version %s", repr(args))
                    elif not initialized:
                        raise ParseError("statement %s encountered before 'version'" % s)
                    elif s == "meta":
                        key, val = args.split(' ', 1)
                        bmap.meta[key] = val
                    elif s == "essential":
                        if essentialParsed:
                            log.warning("duplicate 'essential' statement ignored")
                        elif not bare:
                            args = args.split(' ', 2)

                            maxnotes = int(args[0])
                            bmap.numbands = int(args[1])
                            bmap.music = args[2]

                        essentialParsed = True
                    elif s == "rate":
                        bmap.noterate = float(args)
                    elif s == "note" or s == "hint":
                        if not bare and essentialParsed:
                            args = args.split(' ')
                            lastnote = muz.beatmap.Note(
                                *(int(a) for a in args[:2] + [args[2] if len(args) > 2 else 0]),
                                isHint=(s == "hint")
                            )
                            bmap.append(lastnote)
                    elif s == "var":
                        args = [int(a) for a in args.split(' ')]
                        lastnote.varBands = args
                    elif s == "ref":
                        args = args.split(' ')
                        lastnote.ref = int(args[0])
                        lastnote.refOfs = int(args[1])
                    elif s == "refvar":
                        args = [int(a) for a in args.split(' ')]
                        lastnote.refVarOfs = args
                    else:
                        log.warning("unknown statement %s ignored", repr(s))
            buf = b""
            continue

        buf += byte
    
    if not bare:
        if len(bmap) < maxnotes:
            log.warning("premature EOF: expected %i notes, got %i", maxnotes, len(bmap))

        if not essentialParsed or not maxnotes > 0:
            raise ParseError("empty beatmap")

    bmap.applyMeta()
    return bmap

def write(bmap, fobj, options=None):
    bmap.fix()
    mus = bmap.music.encode('utf-8')

    out = lambda s: fobj.write(s.encode('utf-8'))
    lst = lambda s: reduce(lambda x, y: x + y, (" %i" % i for i in s), "")

    out("# generated by %s-%s\nversion 1\nessential %i %i %s\nrate %f\n" %
       (muz.NAME, muz.VERSION, len(bmap), bmap.numbands, mus, bmap.noterate)
    )

    for key, val in sorted(bmap.meta.items(), key=lambda p: p[0]):
        out("meta %s %s\n" % (key, val))

    for note in bmap:
        out("%s %i %i%s\n" % (
            "hint" if note.isHint else "note", note.band, note.hitTime,
            (" " + str(note.holdTime)) if note.holdTime else ""
        ))

        if note.varBands is not None:
            out("var%s\n" % lst(note.varBands))

        if note.ref >= 0:
            out("ref %i %i\n" % (note.ref, note.refOfs))

        if note.refVarOfs is not None:
            out("refvar%s\n" % lst(note.refVarOfs))

    return bmap.name, "%s/%s.%s" % (locations[0], bmap.name, extensions[0]), "%s/%s" % (locations[0], os.path.splitext(mus)[0])
