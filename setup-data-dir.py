#!/usr/bin/env python3

import os, sys, re
import argparse
from lib.utils import test, make_symlink, ls

# ------------------------       Helpers        ------------------------
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

def test(value, msg=None):
    """ If value is False or None it asserts and possibly prints msg """
    if not value:
        raise AssertionError(*((msg,) if msg else ()))

def ls(path):
    sysexec("ls", "--color=auto", "-l", path)

def make_symlink(src, dst):
    test(src)
    abssrc = os.path.join(os.path.dirname(dst), src) if src[:1] != "/" else src
    test(os.path.exists(abssrc), "the link destination %s does not exists" % src)
    if os.path.islink(dst):
        curlink = os.readlink(dst)
        test(curlink == src, "existing missmatching symlink: %s -> %s" % (dst, curlink))
    else:
        os.symlink(src, dst)
# ------------------------------------------------------------------------

class ShellError(Exception):
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


def custom_exec(source, source_filename, user_ns, user_global_ns):
    if not source.endswith("\n"):
        source += "\n"
    co = compile(source, source_filename, "exec")
    user_global_ns["__package__"] = __package__  # important so that imports work when CRNN itself is loaded as a package
    eval(co, user_global_ns, user_ns)


def load_config_py(filename, config_dict=None):
    """
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


# --------------------------------






datadirlink = "setup-data-dir-symlink"

class Settings:
    workdir_base = "/work/asr3/zeyer"


def find_info_file(base_dir, cur_dir):
    assert base_dir
    assert cur_dir == base_dir or cur_dir.startswith(base_dir + "/")
    if os.path.exists(cur_dir + "/setup-data-dir-info.py"):
        return cur_dir + "/setup-data-dir-info.py"
    if cur_dir == base_dir:
        return None
    return find_info_file(base_dir, os.path.dirname(cur_dir))  # check parent dir


def setup_data_dir(newdir=None):
    curdir = os.getcwd()
    print("Current dir: %s" % curdir)
    setup_dir_prefix = os.path.realpath(os.path.expanduser("~/setups")) + "/"
    test(curdir.startswith(setup_dir_prefix), "Error: Must be in %s" % setup_dir_prefix)

    info_file = find_info_file(setup_dir_prefix[:-1], curdir)
    if info_file:
        load_config_py(info_file, ObjAsDict(Settings))

    user = os.environ["USER"].strip()
    assert user
    workdir = "%s/%s/setups-data/%s" % (Settings.workdir_base, user, curdir[len(setup_dir_prefix):])
    print("Work dir: %s" % workdir)

    if not os.path.isdir(workdir):
        print("Work dir does not exist, create...")
        os.makedirs(workdir)

    if not os.path.islink(workdir + "/setup-dir-symlink"):
        print("Workdir/setup-dir-symlink does not exist, create...")
        os.symlink(curdir, workdir + "/setup-dir-symlink")
    #else:
    #	assert os.readlink(workdir + "/setup-dir-symlink") == curdir

    if os.path.islink(datadirlink) and os.readlink(datadirlink) != workdir:
        print("existing missmatching symlink:")
        ls(datadirlink)
        print("Deleting %s..." % datadirlink)
        os.remove(datadirlink)
    if not os.path.islink(datadirlink):
        print("%s does not exist, create..." % datadirlink)
        os.symlink(workdir, datadirlink)
        ls(datadirlink)

    if newdir is None: return # stop here
    test(newdir)
    test("/" not in newdir, "Error: %r must not contain slashes" % newdir)

    if not os.path.isdir(os.path.join(datadirlink, newdir)):
        print("Workdir/%r does not exist, create..." % newdir)
        os.mkdir(os.path.join(datadirlink, newdir))

    print("Create symlink %r..." % newdir)
    make_symlink(os.path.join(datadirlink, newdir), newdir)
    ls(newdir)

    print("Finished.")


def auto_update_dirs():
    curdir = os.getcwd()
    print("Automatically update dirs. Current dir: %s" % curdir)

    for d in os.listdir(curdir):
        fulldir = os.path.join(curdir, d)
        if not os.path.islink(fulldir): continue
        link = os.readlink(fulldir)
        if not link.startswith(datadirlink + "/"): continue
        print(">>> Dir: %s" % d)
        setup_data_dir(d)


if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('dirs',
        nargs='*',
        help='which dir symlinks we should check/update')
    args = parser.parse_args()

    if len(args.dirs) == 0:
        setup_data_dir()
        auto_update_dirs()

    else:
        for d in args.dirs:
            print(">>> Dir: %s" % d)
            setup_data_dir(d)

