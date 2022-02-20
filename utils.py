import os
import json
from functools import reduce
import operator
import lm_dataformat as lmd


class ExitCodeError(Exception):
    pass


def sh(x):
    if os.system(x):
        raise ExitCodeError()


def ls(x):
    return [x + "/" + fn for fn in os.listdir(x)]


def lsr(x):
    if os.path.isdir(x):
        return reduce(operator.add, map(lsr, ls(x)), [])
    else:
        return [x]


def fwrite(fname, content):
    with open(fname, "w") as fh:
        fh.write(content)


def fread(fname):
    with open(fname) as fh:
        return fh.read()


class filt:
    def __init__(self, f):
        self.f = f

    def __rrshift__(self, other):
        return list(filter(self.f, other))


class apply:
    def __init__(self, f):
        self.f = f

    def __rrshift__(self, other):
        return self.f(other)


class one:
    def __rrshift__(self, other):
        try:
            if isinstance(other, list):
                assert len(other) == 1
                return other[0]
            return next(other)
        except:
            return None


class join:
    def __init__(self, sep):
        self.sep = sep

    def __rrshift__(self, other):
        if other is None:
            return
        try:
            return self.sep.join(other)
        except:
            return None
