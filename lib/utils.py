import os, sys, re

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

# This is just like `assert`, except that it will not be optimized away.
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












def main():
    sysexecVerbose("ls", "-la")
    test(None)

if __name__ == '__main__':
    main()
