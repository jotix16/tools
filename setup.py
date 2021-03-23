#!/usr/bin/env python3
# checked mikel
import os
from lib.utils import ShellError, sysexecVerbose

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

print("> Change into tools-multistep %s" % "tools-multisetup/")
os.chdir("tools-multisetup/")
sysexecVerbose("git", "submodule", "init")
sysexecVerbose("git", "submodule", "update")
