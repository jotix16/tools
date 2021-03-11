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



def main():
    sysexecVerbose("ls", "-la")
    test(None)

if __name__ == '__main__':
    main()
