"""Replace only GI during import, preserving the application's module identity."""

from contextlib import contextmanager
import sys
import types


@contextmanager
def glib_stub(glib):
    names = ('gi', 'gi.repository')
    previous = {name: sys.modules.get(name) for name in names}
    sys.modules['gi'] = types.ModuleType('gi')
    sys.modules['gi.repository'] = types.SimpleNamespace(GLib=glib)
    try:
        yield
    finally:
        for name, module in previous.items():
            if module is None:
                sys.modules.pop(name, None)
            else:
                sys.modules[name] = module
