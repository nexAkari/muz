
import logging, os
log = logging.getLogger(__name__)

from . import Note, Beatmap

import muz.vfs as vfs

class Builder(object):
    def __init__(self, mapname, numbands, msrclist, meta=None):
        if isinstance(msrclist, str) or isinstance(msrclist, unicode):
            msrclist = [msrclist]

        musfile = None
        for musicsource in msrclist:
            try:
                musfile = vfs.locate(musicsource).open()
            except Exception:
                log.warning("couldn't load music source %s", repr(musicsource))
        assert musfile is not None

        self.beatmap = Beatmap(mapname, numbands, music=os.path.split(musfile.name)[-1], musicFile=musfile, meta=meta)
        self.pos = 0
        self.tactLength = 1000.0
        self.bands = []

    @property
    def bpm(self):
        return 60000.0 / (self.tactLength / 4.0)

    @bpm.setter
    def bpm(self, v):
        self.tactLength = (60000.0 / v) * 4.0

    @property
    def meta(self):
        return self.beatmap.meta

    @meta.setter
    def meta(self, v):
        self.beatmap.meta = v

    def __call__(self, *bands):
        s = set(bands)

        if len(s) < len(bands):
            log.warning("duplicate values in band selector %r ignored", bands)

        self.bands = s
        return self

    def beat(self, delayfract=0.0):
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            self.beatmap.append(Note(band, self.pos, 0))

        self.rawpause(delayfract)
        return self

    def hold(self, holdfract, delayfract=0.0):
        holdfract = self.getDelay(holdfract)
        delayfract = self.getDelay(delayfract)

        for band in self.bands:
            self.beatmap.append(Note(band, self.pos, holdfract))
        
        self.rawpause(delayfract)
        return self

    def getDelay(self, delayfract):
        try:
            return sum(self.getDelay(d) for d in delayfract)
        except Exception:
            if delayfract:
                return self.tactLength / float(delayfract)
            return 0

    def pause(self, delayfract):
        self.rawpause(self.getDelay(delayfract))

    def rawpause(self, delay):
        self.pos += delay
