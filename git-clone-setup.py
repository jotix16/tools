#!/usr/bin/env python3
# checked mikel
import os, sys, re
import argparse
from libs.utils import ShellError, sysexec, test, sysexecVerbose
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

parser = argparse.ArgumentParser()
parser.add_argument('source')
parser.add_argument('dest')
args = parser.parse_args()

test(not os.path.exists(args.dest))
sysexecVerbose("git", "clone", args.source, args.dest)
test(os.path.isdir(args.dest))

print("> Change into new dir %s" % args.dest)
os.chdir(args.dest)

if os.path.exists("setup-data-dir-symlink"):
	sysexecVerbose("setup-data-dir.py")
	sysexecVerbose("git", "commit", "setup-data-dir-symlink", "-m", "setup-data-dir-symlink")

if os.path.exists("newbob.data"):
	os.remove("newbob.data")

sysexecVerbose("git", "submodule", "init")
try:
	sysexecVerbose("git", "submodule", "update")
except ShellError as e:
	print("%s. Try to continue though, maybe still works." % e)
sysexecVerbose("git", "submodule", "foreach", "git", "config", "credential.helper", "store")
sysexecVerbose("git", "submodule", "foreach", "git", "checkout", "-B", "master", "origin/master")
