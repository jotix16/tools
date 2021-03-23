#!/usr/bin/env python3

import os, sys, re
import argparse
from lib.utils import test, make_symlink, ls, ObjAsDict, load_config_py, sysexecOut

# from .utils import test


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

    user = os.environ["USER"].strip() if "USER" in os.environ else sysexecOut("whoami").strip() # logname for mac with zsh
    print(user)
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

