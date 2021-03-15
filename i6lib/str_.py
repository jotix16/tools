

import sys
if sys.version_info[0] >= 3:
    unicode = str


def get_str(s):
    """
    :param str|unicode|bytes s:
    :rtype: str|unicode
    """
    if isinstance(s, (str, unicode)):
        return s
    if isinstance(s, bytes):
        return s.decode("utf8")
    raise Exception("Type not supported: %r" % s)
