from os import path

from cffi import FFI


ffibuilder = FFI()

base_path = path.abspath(path.dirname(__file__))
header_path = path.join(base_path, 'vendor/binaryen-c.h')

with open(header_path, 'r') as header_file:
    source = header_file.read()
    ffibuilder.set_source(
        '_binaryen_c',
        r"""
        #include <stddef.h>
        #include <stdint.h>
        {}""".format(source),
        libraries=['binaryen'],
        library_dirs=['vendor'],
    )
    ffibuilder.cdef(source)


if __name__ == '__main__':
    ffibuilder.compile(verbose=True)
