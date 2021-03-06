
from __future__ import absolute_import
from __future__ import print_function
from __future__ import division
from __future__ import unicode_literals

import importlib, pkgutil

from .misc import QuitRequest, Command
from .abstract import Sound, Music, Clock, Frontend

def get(name, frontendArgs=None, frontendArgsNamespace=None):
    return importlib.import_module(__name__ + "." + name).Frontend(args=frontendArgs, namespace=frontendArgsNamespace)

def iter():
    prefix = __name__ + "."
    for importer, modname, ispkg in pkgutil.iter_modules(__path__, prefix):
        if ispkg:
            modname = modname[len(prefix):]
            if "." not in modname:
                yield modname
