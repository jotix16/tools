# -*- coding: utf-8 -*-

from __future__ import print_function
import sys

try:
    import readline
except ImportError:
    # noinspection SpellCheckingInspection
    readline = None
if readline:
    readline.parse_and_bind("tab: complete")
    readline.parse_and_bind("set show-all-if-ambiguous on")


# Python 3 workaround
try:
    # noinspection PyUnresolvedReferences,PyUnboundLocalVariable
    raw_input
except NameError:
    raw_input = input


AllConfirmed = False

def confirm(question):
    if AllConfirmed:
        return
    while True:
        s = raw_input("%s Press enter to confirm or Ctrl+C otherwise." % question)
        if s == "":
            return
        print("Error: Don't type anything, just press enter.")

def seriousConfirm(question):
    if AllConfirmed:
        return
    while True:
        s = raw_input("%s Type 'yes' to confirm." % question)
        if s == "yes":
            return
        if not s:
            continue
        print("Invalid answer %r. Aborting." % s)
        sys.exit(1)

def userRepr(arg):
    import inspect
    from .utils import get_func_name
    if inspect.isroutine(arg):
        return get_func_name(arg)
    return repr(arg)

class ConfirmByUserDeco(object):
    def __init__(self, func):
        self.func = func

    def __call__(self, *args, **kwargs):
        from .utils import get_func_name
        if not AllConfirmed:
            confirm("%s(%s)?" % (
                get_func_name(self.func),
                ", ".join(list(map(userRepr, args)) + ["%s=%r" % item for item in kwargs.items()])
            ))
        return self.func(*args, **kwargs)
