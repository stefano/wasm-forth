from _binaryen_c import lib

_no_gc = []
module = lib.BinaryenModuleCreate()


def retain_gc(*items):
    _no_gc.extend(items)


def release_gc():
    global _no_gc
    _no_gc = []
