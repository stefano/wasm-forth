"""
Utilities to make it easier to write webassembly opcodes.
"""

from _binaryen_c import ffi, lib

from binaryen_module import module, retain_gc
from memory_layout import *


# Control flow


def block(*instrs, label=None):
    if label is None:
        label = ffi.NULL
    else:
        label = label.encode('ascii')

    instrs_array = ffi.new('BinaryenExpressionRef[]', _flatten(instrs))

    return lib.BinaryenBlock(
        module,
        label,
        instrs_array,
        len(instrs_array),
        lib.BinaryenNone(),
    )

    retain_gc.append(instrs_array)


def _flatten(lst, res=None):
    if res is None:
        res = []

    for item in lst:
        if isinstance(item, (list, tuple)):
            _flatten(item, res)
        else:
            res.append(item)

    return res


def loop(label, expr):
    return lib.BinaryenLoop(
        module,
        label.encode('ascii'),
        expr,
    )


def switch(labels, default_label, cond_expr):
    labels_array_elems = [ffi.new('char[]', label.encode('ascii')) for label in labels]
    labels_array = ffi.new('char*[]', labels_array_elems)

    retain_gc(labels_array_elems, labels_array)

    return lib.BinaryenSwitch(module, labels_array, len(labels_array), default_label.encode('ascii'), cond_expr, ffi.NULL)


def jmp(label, cond_expr=ffi.NULL):
    return lib.BinaryenBreak(module, label.encode('ascii'), cond_expr, ffi.NULL)


# Function calls


def call_iin(label, expr1, expr2):
    params = ffi.new('BinaryenExpressionRef[2]', [expr1, expr2])

    retain_gc(params)

    return lib.BinaryenCallImport(module, label.encode('ascii'), params, 2, lib.BinaryenNone())


# Memory access


def get_reg(reg):
    return lib.BinaryenGetLocal(module, reg, CELL_TYPE)


def get_double_reg(reg):
    return lib.BinaryenGetLocal(module, reg, DOUBLE_CELL_TYPE)


def set_reg(reg, expr):
    return lib.BinaryenSetLocal(module, reg, expr)


def load_cell(addr_expr, cells_offset=0):
    return lib.BinaryenLoad(
        module,
        CELL_SIZE,
        0,
        cells_offset * CELL_SIZE,
        0,
        CELL_TYPE,
        addr_expr,
    )


def load_double_cell(addr_expr, cells_offset=0):
    return lib.BinaryenLoad(
        module,
        CELL_SIZE * 2,
        0,
        cells_offset * CELL_SIZE,
        0,
        DOUBLE_CELL_TYPE,
        addr_expr,
    )


def store_cell(addr_expr, value_expr, cells_offset=0):
    return lib.BinaryenStore(
        module,
        CELL_SIZE,
        cells_offset * CELL_SIZE,
        0,
        addr_expr,
        value_expr,
        CELL_TYPE,
    )


def store_double_cell(addr_expr, value_expr, cells_offset=0):
    return lib.BinaryenStore(
        module,
        CELL_SIZE * 2,
        cells_offset * CELL_SIZE,
        0,
        addr_expr,
        value_expr,
        DOUBLE_CELL_TYPE,
    )


def load_byte(addr_expr):
    return lib.BinaryenLoad(
        module,
        1,
        0,
        0,
        0,
        CELL_TYPE,
        addr_expr,
    )


def store_byte(addr_expr, value_expr):
    return lib.BinaryenStore(
        module,
        1,
        0,
        0,
        addr_expr,
        value_expr,
        CELL_TYPE,  # NOTE: there is no 'byte' type in webassembly
    )


# Stack helpers


def invert_double_cell(expr):
    """forth wants low | hi, but wasm is little endian (i.e. the
    reverse). Cells are already stored in little-endian, so we can get
    a proper 64 bit number by rotating by 32 bits.

    """
    return lib.BinaryenBinary(module, lib.BinaryenRotRInt64(), expr, lib.BinaryenConst(module, lib.BinaryenLiteralInt64(32)))


def peek(stack_reg, cells_offset):
    return load_cell(get_reg(stack_reg), cells_offset)


def peek_double(stack_reg, cells_offset):
    return invert_double_cell(load_double_cell(get_reg(stack_reg), cells_offset))


def put(stack_reg, cells_offset, expr):
    return store_cell(get_reg(stack_reg), expr, cells_offset)


def put_double(stack_reg, cells_offset, expr):
    return store_double_cell(get_reg(stack_reg), invert_double_cell(expr), cells_offset)


def inc(reg, n_cells):
    return set_reg(reg, add_cell_size(reg, n_cells))


def drop(reg, n_cells):
    return inc(reg, n_cells)


def push(stack_reg, expr):
    """
    NOTE: the stack size is already incremented by 1 cell when expr is evaluated.
    """

    return [
        inc(stack_reg, -1),
        put(stack_reg, 0, expr),
    ]


def add_cell_size(reg, n_cells):
    if n_cells == 0:
        return get_reg(reg)

    return add(
        get_reg(reg),
        const_cell(n_cells * CELL_SIZE),
    )


def cmp_neg(cmp_op):
    # NOT: cmp_op MUST be the reverse of the desired one!
    return [
        put(
            SP,
            1,
            sub(
                cmp_op(
                    peek(SP, 1),
                    peek(SP, 0),
                ),
                const_cell(1),
            ),
        ),
        drop(SP, 1),
    ]


def cmp_neg_zero(cmp_op):
    # NOT: cmp_op MUST be the reverse of the desired one!
    return [
        put(
            SP,
            0,
            sub(
                cmp_op(
                    peek(SP, 0),
                    const_cell(0),
                ),
                const_cell(1),
            ),
        ),
    ]


def op_on_tos(op, rhs_expr, stack_reg=SP):
    """
    Applies X = op(X, rhs_expr), where X is the top of the stack.
    """

    return put(stack_reg, 0, op(peek(stack_reg, 0), rhs_expr))


def bin_op(op):
    return [
        put(SP, 1, op(peek(SP, 1), peek(SP, 0))),
        drop(SP, 1),
    ]


def bin_op_32_32_64(op):
    return put_double(SP, 0, op(peek(SP, 1), peek(SP, 0)))


def bin_op_64_32_64(op):
    return [
        put_double(SP, 1, op(peek_double(SP, 1), peek(SP, 0))),
        drop(SP, 1),
    ]


# Constants


def const_cell(value):
    return lib.BinaryenConst(module, lib.BinaryenLiteralInt32(value))


def const_double_cell(value):
    return lib.BinaryenConst(module, lib.BinaryenLiteralInt64(value))


# Type conversions


def u_32_to_64(expr):
    return lib.BinaryenUnary(module, lib.BinaryenExtendUInt32(), expr)


def u_64_to_32(expr):
    return lib.BinaryenUnary(module, lib.BinaryenWrapInt64(), expr)


def s_32_to_64(expr):
    return lib.BinaryenUnary(module, lib.BinaryenExtendSInt32(), expr)


def s_64_to_32(expr):
    return lib.BinaryenUnary(module, lib.BinaryenWrapInt64(), expr)


# Comparisons


def eqz(expr):
    return lib.BinaryenUnary(module, lib.BinaryenEqZInt32(), expr)


def eq(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenEqInt32(), expr1, expr2)


def ne(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenNeInt32(), expr1, expr2)


def ge_s(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenGeSInt32(), expr1, expr2)


def ge_u(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenGeUInt32(), expr1, expr2)


def le_s(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenLeSInt32(), expr1, expr2)


def le_u(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenLeUInt32(), expr1, expr2)


def l_s(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenLtSInt32(), expr1, expr2)


# Math/bit-ops


def add(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenAddInt32(), expr1, expr2)


def add_64_32(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenAddInt64(), expr1, u_32_to_64(expr2))


def add_64(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenAddInt64(), expr1, expr2)


def sub(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenSubInt32(), expr1, expr2)


def mul(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenMulInt32(), expr1, expr2)


def mul_32_32_64(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenMulInt64(), s_32_to_64(expr1), s_32_to_64(expr2))


def mul_64(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenMulInt64(), expr1, expr2)


def umul_32_32_64(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenMulInt64(), u_32_to_64(expr1), u_32_to_64(expr2))


def div(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenDivSInt32(), expr1, expr2)


def rem(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenRemSInt32(), expr1, expr2)


def div_64_32_32(expr1, expr2):
    return s_64_to_32(lib.BinaryenBinary(module, lib.BinaryenDivSInt64(), expr1, s_32_to_64(expr2)))


def udiv_64_32_32(expr1, expr2):
    return u_64_to_32(lib.BinaryenBinary(module, lib.BinaryenDivUInt64(), expr1, u_32_to_64(expr2)))


def udiv_64_32_64(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenDivUInt64(), expr1, u_32_to_64(expr2))


def rem_64_32_32(expr1, expr2):
    return s_64_to_32(lib.BinaryenBinary(module, lib.BinaryenRemSInt64(), expr1, s_32_to_64(expr2)))


def urem_64_32_32(expr1, expr2):
    return u_64_to_32(lib.BinaryenBinary(module, lib.BinaryenRemUInt64(), expr1, u_32_to_64(expr2)))


def ls(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenShlInt32(), expr1, expr2)


def a_rs(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenShrSInt32(), expr1, expr2)


def l_rs(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenShrUInt32(), expr1, expr2)


def bit_and(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenAndInt32(), expr1, expr2)


def bit_or(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenOrInt32(), expr1, expr2)


def bit_xor(expr1, expr2):
    return lib.BinaryenBinary(module, lib.BinaryenXorInt32(), expr1, expr2)
