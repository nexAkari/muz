
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import os
import collections
import logging
import string
import pygame

import muz
import muz.config
import muz.console

from . import Sound, Music, gamerenderer
from .. import QuitRequest
from . import __name__ as __parentname__

log = logging.getLogger(__name__)

class Clock(muz.frontend.Clock):
    def __init__(self, targetFps=0):
        self._clock = pygame.time.Clock()
        self.targetFps = targetFps

    def tick(self):
        self._clock.tick(self.targetFps)

    @property
    def deltaTime(self):
        return self._clock.get_time()

    @property
    def fps(self):
        return self._clock.get_fps()

class Frontend(muz.frontend.Frontend):
    supportedGlyphs = "".join((string.ascii_letters, string.digits, string.punctuation, string.whitespace))
    fallbackFont = "unifont-8.0.01"

    def __init__(self, args, namespace):
        self._music = Music()
        self.config = self.makeDefaultConfig()
        self.videoFlags = pygame.DOUBLEBUF | pygame.HWSURFACE
        self.activity = None
        self.screen = None
        self.gameRendererClass = gamerenderer.GameRenderer
        self.console = None
        self.consoleScope = {}
        self.fonts = {}
        self.fallbackFontsBySize = {}
        self.fallbackFonts = {}

    @property
    def supportedMusicFormats(self):
        return "ogg", "mp3", "wav"

    @property
    def supportedSoundFormats(self):
        return "ogg", "wav"

    def makeDefaultConfigAudio(self):
        return {
            "frequency"             : 44100,
            "buffer"                : 1024,
            "size"                  : -16,
            "channels"              : 2,
            "driver"                : "default",
            "sound-effect-volume"   : 0.7,
            "music-volume"          : 0.5,
        }

    def makeDefaultConfigVideo(self):
        return {
            "window-width"          : 1280,
            "window-height"         : 720,
            "fullscreen"            : False,
            "target-fps"            : 0,
            "render-text"           : True,
            "antialias-text"        : True,
        }

    def makeDefaultConfigKeymaps(self):
        return {
            "global": {
                "`"         :       "toggle-autoplay",
                "pause"     :       "toggle-pause",
                "escape"    :       "toggle-pause",
                "f10"       :       "quit",
    
                "1"         :       "band:0",
                "2"         :       "band:1",
                "3"         :       "band:2",
                "4"         :       "band:3",
                "5"         :       "band:4",
                "6"         :       "band:5",
                "7"         :       "band:6",
                "8"         :       "band:7",
                "9"         :       "band:8",
                "0"         :       "band:9",
    
                "a"         :       "band:-1",
                "s"         :       "band:-1",
                "d"         :       "band:-1",
                "f"         :       "band:-1",
                "space"     :       "band:-1",
                "j"         :       "band:-1",
                "k"         :       "band:-1",
                "l"         :       "band:-1",
                ";"         :       "band:-1",

                "left"      :       "seek:-1000",
                "right"     :       "seek:1000",
                "down"      :       "seek:-5000",
                "up"        :       "seek:5000",
            },
    
            "bandnum=1": {
                "space"     :       "band:0",
            },
    
            "bandnum=2": {
                "f"         :       "band:0",
                "j"         :       "band:1",
            },
    
            "bandnum=3": {
                "f"         :       "band:0",
                "space"     :       "band:1",
                "j"         :       "band:2",
            },
    
            "bandnum=4": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "j"         :       "band:2",
                "k"         :       "band:3",
            },
    
            "bandnum=5": {
                "d"         :       "band:0",
                "f"         :       "band:1",
                "space"     :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
            },
    
            "bandnum=6": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "j"         :       "band:3",
                "k"         :       "band:4",
                "l"         :       "band:5",
            },
    
            "bandnum=7": {
                "s"         :       "band:0",
                "d"         :       "band:1",
                "f"         :       "band:2",
                "space"     :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
            },
    
            "bandnum=8": {
                "a"         :       "band:0",
                "s"         :       "band:1",
                "d"         :       "band:2",
                "f"         :       "band:3",
                "j"         :       "band:4",
                "k"         :       "band:5",
                "l"         :       "band:6",
                ";"         :       "band:7",
            },
    
            "bandnum=9": {
                "a"         :       "band:0",
                "s"         :       "band:1",
                "d"         :       "band:2",
                "f"         :       "band:3",
                "space"     :       "band:4",
                "j"         :       "band:5",
                "k"         :       "band:6",
                "l"         :       "band:7",
                ";"         :       "band:8",
            },
        }

    def makeDefaultConfigRoot(self):
        return {
            "console" : True,
            "audio"   : self.makeDefaultConfigAudio(),
            "video"   : self.makeDefaultConfigVideo(),
            "keymaps" : self.makeDefaultConfigKeymaps(),
            "gamerenderer" : gamerenderer.makeDefaultConfig()
        }

    def makeDefaultConfig(self):
        return muz.config.get(__parentname__, self.makeDefaultConfigRoot())

    def postInit(self):
        a = self.config["audio"]
        v = self.config["video"]

        if a["driver"] != "default":
            os.environ["SDL_AUDIODRIVER"] = a["driver"]

        pygame.mixer.pre_init(
            frequency=a["frequency"],
            size=a["size"],
            channels=a["channels"],
            buffer=a["buffer"]
        )

        pygame.init()

        flags = self.videoFlags
        if v["fullscreen"]:
            flags |= pygame.FULLSCREEN

        self.screen = pygame.display.set_mode((v["window-width"], v["window-height"]), flags)
        self.title = None

        self.antialias = self.config["video"]["antialias-text"]

        if not self.config["video"]["render-text"]:
            self.renderText = self.renderTextDummy

        self.useConsole = self.config["console"]
        self.dummySurf = None
        self.initKeymap()

    def initKeymap(self, submap=None):
        # pygame wtf, why is this not provided by default?
        keyLookupTable = {pygame.key.name(v).lower(): v for k, v in pygame.constants.__dict__.items() if k.startswith("K_")}

        lower = lambda d: {k.lower(): v.lower() for k, v in d.items()}

        self.keymap = collections.defaultdict(lambda: nullfunc)
        keymap = lower(self.config["keymaps"]["global"])

        if submap is not None:
            try:
                keymap.update(lower(self.config["keymaps"][submap]))
            except KeyError:
                log.warning("subkeymap %s doesn't exist", submap)

        for key, action in keymap.items():
            try:
                sdlkey = keyLookupTable[key]
            except KeyError:
                log.warning("unknown key %s in keymap", repr(key))
                continue

            self.keymap[sdlkey] = action

    def shutdown(self):
        log.info("shutting down")
        pygame.quit()

    def loadSound(self, node):
        s = Sound(node)
        s.volume = self.config["audio"]["sound-effect-volume"]
        return s

    def loadMusic(self, node):
        self._music._paused = False
        pygame.mixer.music.load(node.realPath)
        pygame.mixer.music.set_volume(self.config["audio"]["music-volume"])
        return self._music

    def command(self, cmd, isRelease=False):
        log.debug("command: %s (%s)", cmd, "release" if isRelease else "press")

        if cmd == "quit":
            raise QuitRequest

        if self.activity is not None:
            self.activity.command(cmd, isRelease)

    def handleEvent(self, event):
        if event.type == pygame.QUIT:
            raise QuitRequest

        if self.activity is None:
            return

        if event.type == pygame.KEYDOWN:
            if event.key in self.keymap:
                self.command(self.keymap[event.key], False)

        if event.type == pygame.KEYUP:
            if event.key in self.keymap:
                self.command(self.keymap[event.key], True)

    def initConsole(self, conlocals):
        if not self.useConsole:
            return

        self.consoleScope = conlocals

        con = self.console = muz.console.Console()

        @con.handlers.append
        def handler(buf):
            pref = buf[0:1]
            if pref in ("!", "~"):
                self.command(buf[1:], isRelease=(pref == "~"))
                return muz.console.CMD_HANDLED

            return muz.console.CMD_UNHANDLED

        con.handlers.append(muz.console.PythonHandler(scope=conlocals))
        muz.console.AsyncInput.initReadline(scope=conlocals)
        muz.console.AsyncInput(con).start()

    def handleConsole(self):
        if not self.useConsole:
            return

        f = self.consoleScope.get("__frame__")
        if f is not None:
            f()

        self.console.process()

    def gameLoop(self, activity):
        renderer = self.gameRendererClass(activity, self.config["gamerenderer"])
        self.activity = activity
        activity.renderer = renderer
        clock = Clock(self.config["video"]["target-fps"])
        activity.clock = clock
        screen = self.screen

        self.initConsole({
            "__name__"  : "__console__",
            "__frame__" : None,
            "muz"       : muz,
            "vfs"       : muz.vfs,
            "game"      : activity,
            "clock"     : clock,
            "screen"    : screen,
            "frontend"  : self,
            "pygame"    : pygame,
            "cmd"       : self.command,
        })

        try:
            while True:
                self.handleConsole()

                for event in pygame.event.get():
                    self.handleEvent(event)

                activity.update()
                renderer.draw(screen)

                pygame.display.flip()
                clock.tick()
        except QuitRequest:
            return
        finally:
            self._music.playing = False

    def getTitle(self):
        return pygame.display.get_caption()

    def setTitle(self, title):
        if title:
            pygame.display.set_caption(("%s - %s" % (muz.NAME, title)).encode('utf-8'))
        else:
            pygame.display.set_caption(muz.NAME.encode('utf-8'))

    title = property(getTitle, setTitle)

    def _loadFont(self, name, size, isSysFont=False):
        if isSysFont:
            return pygame.font.SysFont(name, size)

        path = None
        for ext in ("otf", "ttf"):
            fname = "fonts/%s.%s" % (name, ext)
            try:
                path = muz.vfs.locate(fname).realPath
            except Exception:
                log.debug("loading font %r failed", exc_info=True)
            else:
                break

        assert path is not None, "font %r couldn't be found" % name
        return pygame.font.Font(path, size)

    def loadFont(self, name, size, isSysFont=False):
        if (name, size) in self.fonts:
            return self.fonts[(name, size)]

        fnt = self._loadFont(name, size, isSysFont)
        self.fonts[(name, size)] = fnt

        if name == self.fallbackFont:
            self.fallbackFonts[fnt] = fnt
            fnt.set_bold(True)
            return fnt

        if size not in self.fallbackFontsBySize:
            self.fallbackFontsBySize[size] = self.loadFont(self.fallbackFont, size)

        self.fallbackFonts[fnt] = self.fallbackFontsBySize[size]
        return fnt

    def renderTextDummy(self, text, font, color, direct=False, useFallback=False):
        if not self.dummySurf:
            self.dummySurf = pygame.Surface((1, 1)).convert()
            ckey = (0, 0, 0)
            self.dummySurf.fill(ckey)
            self.dummySurf.set_colorkey(ckey)
        return self.dummySurf

    def splitTextForRendering(self, text, font):
        buf = ""
        state = True

        for c in text:
            newstate = c in self.supportedGlyphs
            if state != newstate:
                if buf:
                    yield font if state else self.fallbackFonts[font], buf
                    buf = ""

                state = newstate
            buf += c

        if buf:
            yield font if state else self.fallbackFonts[font], buf

    def renderText(self, text, font, color, direct=False, useFallback=False):
        if useFallback:
            surfs = tuple(
                self.renderText(txt, fnt, color, useFallback=False)
                    for fnt, txt in self.splitTextForRendering(text, font)
            )

            w = sum(s.get_rect().width  for s in surfs)
            h = max(s.get_rect().height for s in surfs)

            txt = pygame.Surface((w, h)).convert_alpha()
            txt.fill((0, 0, 0, 0))

            x = 0
            for s in surfs:
                txt.blit(s, (x, int((h - s.get_rect().height) * 0.5)))
                x += s.get_rect().width
        else:
            txt = font.render(text, self.antialias, color)

        if direct:
            return txt

        s = pygame.Surface(txt.get_size()).convert()
        ckey = (0, 0, 0)
        s.fill(ckey)
        s.blit(txt, (0, 0, 0, 0))
        s.set_colorkey(ckey)
        return s
