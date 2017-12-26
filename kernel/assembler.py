from _binaryen_c import ffi, lib

from asm_ops import *
from binaryen_module import module, retain_gc, release_gc
from code_words import init_registers, CODE_WORDS
from forth_interpreter import FORTH_CONSTANTS, FORTH_VARIABLES, FORTH_COL_DEFS
from memory_layout import *


def build_kernel(output_file):
    """
    Builds the basic forth kernel, with just enough primitives to run an interpreter,
    and saves it to a WASM file.
    """

    assemble()
    save_kernel(output_file)
    destroy()


def assemble():
    """
    Assembles the forth kernel into the global binaryen module.
    """

    add_imports()
    add_exports()
    add_initial_memory()
    add_interpreter()


def add_imports():
    """
    Add FFI imports to the module (io.read and io.write).
    """

    ii_params = ffi.new('BinaryenType[2]', [CELL_TYPE] * 2)
    iin = lib.BinaryenAddFunctionType(module, b'iin', lib.BinaryenNone(), ii_params, 2)

    lib.BinaryenAddImport(module, b'read', b'io', b'read', iin)
    lib.BinaryenAddImport(module, b'write', b'io', b'write', iin)

    retain_gc(ii_params)


def add_exports():
    """
    Exports the interpreter entry point.
    """

    lib.BinaryenAddExport(module, b'exec', b'exec')


def add_initial_memory():
    """
    Initializes the memory with compiled forth constants, variables and column definition.
    """

    forth_words_addrs = {}
    dictionary_bytes = []
    last_name_addr = 0
    last_name_addr = add_code_primitives_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr)
    last_name_addr = add_forth_constants_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr)
    last_name_addr = add_forth_variables_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr)
    last_name_addr = add_forth_col_defs_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr)

    # set LATEST to last_name_addr
    replace_forth_variable_value(dictionary_bytes, forth_words_addrs, 'LATEST', last_name_addr)
    # set HERE to HERE_INITIAL + len(dictionary_bytes)
    replace_forth_variable_value(dictionary_bytes, forth_words_addrs, '\'HERE', HERE_INITIAL + len(dictionary_bytes))

    # address of first forth word to run (i.e. initial value of the IP register)
    ip_initial_bytes = []
    append_cell(ip_initial_bytes, forth_words_addrs['ABORT'])

    dictionary_data = ffi.new('char[]', bytes(dictionary_bytes))
    ip_initial_data = ffi.new('char[]', bytes(ip_initial_bytes))

    segment_contents = ffi.new('char*[]', [ip_initial_data, dictionary_data])
    segment_offsets = ffi.new('BinaryenExpressionRef[]', [const_cell(IP_INITIAL), const_cell(HERE_INITIAL)])
    segment_sizes = ffi.new('BinaryenIndex[]', [len(ip_initial_bytes), len(dictionary_bytes)])

    # 2 = 128k
    lib.BinaryenSetMemory(module, 2, 2, b'mem', segment_contents, segment_offsets, segment_sizes, 2)

    retain_gc(dictionary_data, ip_initial_data, segment_contents, segment_offsets, segment_sizes)


def add_interpreter():
    """
    Adds the interpreter function to the global module.
    """

    ii_params = ffi.new('BinaryenType[2]', [CELL_TYPE, CELL_TYPE])
    iin = lib.BinaryenAddFunctionType(module, b't_iin', lib.BinaryenNone(), ii_params, len(ii_params))

    registers = ffi.new('BinaryenType[]', 8)
    registers[IP - 2] = CELL_TYPE
    registers[W - 2] = CELL_TYPE
    registers[SP - 2] = CELL_TYPE
    registers[RS - 2] = CELL_TYPE
    registers[SCRATCH_1 - 2] = CELL_TYPE
    registers[SCRATCH_2 - 2] = CELL_TYPE
    registers[SCRATCH_3 - 2] = CELL_TYPE
    registers[SCRATCH_DOUBLE_1 - 2] = DOUBLE_CELL_TYPE

    exec_body = block(
        init_registers(),
        assemble_interpreter(),
        label='entry',
    )
    lib.BinaryenAddFunction(module, b'exec', iin, registers, len(registers), exec_body)

    retain_gc(ii_params, registers)


def assemble_interpreter():
    # main interpreter switch to execute code words
    interpreter_body = switch(
        [label for label, _ in CODE_WORDS],
        # memory addresses in the dictionary are always greater than
        # primitive indexes (because of how far into the memory the
        # dictionary starts). If a code index is not found, we assume
        # it's a custom initiation code defined using DOES>, so we
        # execute (dodoes) to run it.
        '(dodoes)',
        load_cell(get_reg(W)),
    )

    for label, instrs in CODE_WORDS:
        interpreter_body = block(block(interpreter_body, label=label), instrs)

    interpreter_body = block(
        set_reg(W, load_cell(get_reg(IP))),
        inc(IP, 1),
        loop('interpreter_switch', interpreter_body),
    )

    return loop('next', interpreter_body)


def add_code_primitives_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr):
    for code_addr, (label, _) in enumerate(CODE_WORDS):
        last_name_addr = append_dict_header(dictionary_bytes, forth_words_addrs, last_name_addr, label)

        append_cell(dictionary_bytes, code_addr)

    return last_name_addr


def add_forth_constants_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr):
    doconst_addr = find_code_primitive_addr('(doconst)')

    for label, initial_value in FORTH_CONSTANTS:
        last_name_addr = append_dict_header(dictionary_bytes, forth_words_addrs, last_name_addr, label)

        append_cell(dictionary_bytes, doconst_addr)
        append_cell(dictionary_bytes, initial_value)

    return last_name_addr


def add_forth_variables_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr):
    dovar_addr = find_code_primitive_addr('(dovar)')

    for label, initial_value in FORTH_VARIABLES:
        last_name_addr = append_dict_header(dictionary_bytes, forth_words_addrs, last_name_addr, label)

        append_cell(dictionary_bytes, dovar_addr)
        # variable values can be a byte-string or a single-cell integer
        if isinstance(initial_value, bytes):
            append_aligned_bytes(dictionary_bytes, initial_value)
        else:
            append_cell(dictionary_bytes, initial_value)

    return last_name_addr


def replace_forth_variable_value(dictionary_bytes, forth_words_addrs, label, new_value):
    replace_cell(dictionary_bytes, forth_words_addrs[label] + CELL_SIZE - HERE_INITIAL, new_value)


def add_forth_col_defs_dict_entries(dictionary_bytes, forth_words_addrs, last_name_addr):
    docol_addr = find_code_primitive_addr('(docol)')

    for label, words, immediate in FORTH_COL_DEFS:
        last_name_addr = append_dict_header(dictionary_bytes, forth_words_addrs, last_name_addr, label, immediate)

        append_cell(dictionary_bytes, docol_addr)

        # compile the body
        for word in words:
            if isinstance(word, int):
                append_cell(dictionary_bytes, word)
            else:
                assert word in forth_words_addrs, 'word {} not defined'.format(word)
                append_cell(dictionary_bytes, forth_words_addrs[word])

        append_cell(dictionary_bytes, forth_words_addrs['EXIT'])

    return last_name_addr


def find_code_primitive_addr(primitive_label):
    for code_addr, (label, _) in enumerate(CODE_WORDS):
        if label == primitive_label:
            return code_addr
    else:
        raise Exception('The {} code primitive must be defined'.format(primitive_label))


def append_dict_header(dictionary_bytes, forth_words_addrs, last_name_addr, label, immediate=False):
    """
    Appends the header for a definition entry in the forth dictionary.
    Adds the address of the code word to forth_words_addrs, and returns the
    address where the (length, name) pair starts.

    Header structure:
    - 4 bytes pointer to previous entry
    - 1 byte of flags (1 = immediate word, 0 = non-immediate word)
    - 1 byte of label length
    - 4-byte aligned label bytes (max 30)
    """

    assert len(label) < 31

    append_cell(dictionary_bytes, last_name_addr)  # pointer to previous entry

    dictionary_bytes.append(int(immediate))  # 1 byte of flags: 1 = IMMEDIATE, 0 = normal

    last_name_addr = HERE_INITIAL + len(dictionary_bytes)

    dictionary_bytes.append(len(label))  # 1 byte of label length (high-bit can be set to 1 to hide the word)
    append_aligned_bytes(dictionary_bytes, label.encode('ascii'))

    forth_words_addrs[label] = HERE_INITIAL + len(dictionary_bytes)

    return last_name_addr


def append_aligned_bytes(dictionary_bytes, value):
    dictionary_bytes.extend(value)
    append_padding(dictionary_bytes)


def append_padding(dictionary_bytes):
    """pad to CELL_SIZE boundary"""

    size = len(dictionary_bytes)
    padded_size = ((CELL_SIZE - (size & (CELL_SIZE - 1))) & (CELL_SIZE - 1)) + size
    dictionary_bytes.extend([0] * (padded_size - size))


def append_cell(dictionary_bytes, value):
    # webassembly uses little endian
    dictionary_bytes.append(value & 0xFF)
    dictionary_bytes.append((value >> 8) & 0xFF)
    dictionary_bytes.append((value >> 16) & 0xFF)
    dictionary_bytes.append((value >> 24) & 0xFF)


def replace_cell(dictionary_bytes, offset, value):
    # webassembly uses little endian
    dictionary_bytes[offset] = value & 0xFF
    dictionary_bytes[offset + 1] = (value >> 8) & 0xFF
    dictionary_bytes[offset + 2] = (value >> 16) & 0xFF
    dictionary_bytes[offset + 3] = (value >> 24) & 0xFF


def print_debug():
    lib.BinaryenModulePrint(module)


def save_kernel(output_file):
    """
    Saves the global module to a file.
    """

    assert lib.BinaryenModuleValidate(module) == 1

    size = 1024
    while True:
        buf = ffi.new('char[]', size)
        written_size = lib.BinaryenModuleWrite(module, buf, size)
        if written_size < size:
            with open(output_file, 'w+b') as out:
                out.write(ffi.buffer(buf, written_size))
            break
        size *= 2


def destroy():
    """
    Frees memory allocated to build to the global module.
    """

    lib.BinaryenModuleDispose(module)
    release_gc()
