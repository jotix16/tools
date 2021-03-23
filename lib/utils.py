import os, sys, re
import lib.ui as ui
from sys import platform

mac = platform == "darwin"


IsPython2 = sys.version_info[0] <= 2
IsPython3 = sys.version_info[0] >= 3

if IsPython3:
    unicode = str


def betterRepr(o):
    """
    The main difference: this one is deterministic,
    the orig dict.__repr__ has the order undefined.
    Also, the output is minimally formatted.
    Also, this tries to output such that we can import
    with both Python 2+3.
    """
    # Recursive structures.
    if isinstance(o, list):
        return "[" + ", ".join(map(betterRepr, o)) + "]"
    if isinstance(o, tuple):
        return "(" + ", ".join(map(betterRepr, o)) + ")"
    # Sort dict. And format.
    if isinstance(o, dict):
        return "{\n" + "".join([betterRepr(k) + ": " + betterRepr(v) + ",\n" for (k,v) in sorted(o.items())]) + "}"
    # Handle Python2 unicode to not print prefix 'u'.
    if IsPython2 and isinstance(o, unicode):
        s = o.encode("utf8")
        s = repr(s)
        if "\\x" in s: # Simple hacky check: Do we need unicode?
            return "%s.decode('utf8')" % s
        return s
    # fallback
    return repr(o)

class ShellError(Exception):
    """ Costum exception for shell comands that prints the exit code. """
    def __init__(self, res):
        self.exitCode = res
        assert self.exitCode != 0
        super(ShellError, self).__init__("exit code %i" % self.exitCode)


def sysexec(*args, **kwargs):
    """ Executes a shell comand given by *args """
    import subprocess
    res = subprocess.call(args, shell=False, **kwargs)
    if res != 0:
        raise ShellError(res)

def sysexecVerbose(*args, **kwargs):
    """ Prints and then executes a shell comand given by *args """
    print("sysexec: %s" % (args,))
    return sysexec(*args, **kwargs)

def sysexecOut(*args, **kwargs):
    from subprocess import Popen, PIPE
    kwargs.setdefault("shell", False)
    p = Popen(args, stdin=PIPE, stdout=PIPE, **kwargs)
    out, _ = p.communicate()
    if p.returncode != 0:
        raise ShellError(p.returncode)
    out = out.decode("utf-8")
    return out

def custom_exec(source, source_filename, user_ns, user_global_ns):
    if not source.endswith("\n"):
        source += "\n"
    co = compile(source, source_filename, "exec")
    user_global_ns["__package__"] = __package__  # important so that imports work when CRNN itself is loaded as a package
    eval(co, user_global_ns, user_ns)



# This is just like `assert`, except that it will not be optimized away.
def test(value, msg=None):
    """ If value is False or None it asserts and possibly prints msg """
    if not value:
        raise AssertionError(*((msg,) if msg else ()))

def ls(path):
    if mac:
        sysexec("ls", "-G", path)
    else: sysexec("ls", "--color=auto", "-l", path)

def make_symlink(src, dst):
    test(src)
    abssrc = os.path.join(os.path.dirname(dst), src) if src[:1] != "/" else src
    test(os.path.exists(abssrc), "the link destination %s does not exists" % src)
    if os.path.islink(dst):
        curlink = os.readlink(dst)
        test(curlink == src, "existing missmatching symlink: %s -> %s" % (dst, curlink))
    else:
        os.symlink(src, dst)

@ui.ConfirmByUserDeco
def shellcmd(cmd):
    use_shell = False
    if type(cmd) is str:
        use_shell = True
    import subprocess
    res = subprocess.call(cmd, shell=use_shell)
    if res != 0:
        raise ShellError(res)


def parse_time(t):
    """ Parses h:m:s to seconds
    :param str t:
    :rtype: int
    """
    ts = t.split(":")
    if len(ts) == 1:
        return int(t)
    elif len(ts) == 2:
        return int(ts[1]) + 60 * int(ts[0])
    elif len(ts) == 3:
        return int(ts[2]) + 60 * int(ts[1]) + 60 * 60 * int(ts[0])
    assert False, t

def repr_time(t):
    """ From seconds to h:m:s
    :param int|float t: in seconds
    :rtype: str
    """
    hh, mm, ss = t / (60 * 60), (t / 60) % 60, t % 60
    return "%i:%02i:%02i" % (hh, mm, ss)

def repr_time_mins(t):
    """ From seconds to h:m
    :param int|float t: in seconds
    :rtype: str
    """
    if t == float("inf"):
        return "inf"
    t = round(t / 60.0) * 60
    hh, mm, ss = t / (60 * 60), (t / 60) % 60, t % 60
    return "%i:%02ih" % (hh, mm)

def avoid_wiki_link(s):
    """
    :param str s:
    :rtype: str
    """
    if s[0:1].isupper() and s[1:2].islower():
        for c in s[2:]:
            if c.isspace():
                break
            if c.isupper():
                return "!%s" % s
    return s

def human_size(s, postfix="B", limit=0.9, base=1024, str_format=None):
    p = ["", "K", "M", "G", "T"]
    b = 1
    i = 0
    while i < len(p) - 1 and s * limit > b * base:
        b *= base
        i += 1
    if str_format is None:
        if isinstance(s, float) or i > 0:
            str_format = "%.2f"
        else:
            str_format = "%i"
    return str_format % ((s * 1.0) / b) + " %s%s" % (p[i], postfix)


## needed in ui
def get_func_name(func):
    """
    :param function|callable func:
    :rtype: str
    """
    if hasattr(func, "func_name"):
        return func.func_name
    if hasattr(func, "__name__"):
        return func.__name__
    return str(func)

# needed in tools.py
def load_config_py(filename, config_dict=None):
    """   Updates config_dict with entries from the dict build from filename
    :param str filename:
    :param dict[str]|ObjAsDict|None config_dict: if given, will update inplace
    :return: config_dict (same instance)
    :rtype: dict[str]
    """
    content = open(filename).read()
    if config_dict is None:
        config_dict = {}
    if isinstance(config_dict, dict):
        user_ns = config_dict
    else:
        user_ns = dict(config_dict)
    # Always overwrite:
    user_ns.update({"config": config_dict, "__file__": filename, "__name__": "__crnn_config__"})
    custom_exec(content, filename, user_ns, user_ns)
    if user_ns is not config_dict:
        config_dict.update(user_ns)
    return config_dict

class ObjAsDict:
    Blacklist = ("__dict__", "__weakref__")

    def __init__(self, obj):
        self.__obj = obj

    def __getitem__(self, item):
        if not isinstance(item, (str, unicode)):
            raise KeyError("%r must be a str" % (item,))
        try:
            return getattr(self.__obj, item)
        except AttributeError as e:
            raise KeyError(e)

    def __setitem__(self, item, value):
        if hasattr(self.__obj, item) and getattr(self.__obj, item) is value:
            return
        setattr(self.__obj, item, value)

    def update(self, other):
        items = other.items() if isinstance(other, dict) else other
        for k, v in items:
            self[k] = v

    def keys(self):
        return [k for k in vars(self.__obj).keys() if k not in self.Blacklist]

    def items(self):
        return [(k, v) for (k, v) in vars(self.__obj).items() if k not in self.Blacklist]

    def __iter__(self):
        return iter(self.keys())

    def __repr__(self):
        return "<ObjAsDict %r -> %r>" % (self.__obj, dict(self.items()))


def main():
    sysexecVerbose("ls", "-la")
    test(None)

if __name__ == '__main__':
    main()
