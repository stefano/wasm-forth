"""
Basic Forth words defined directly in WebAssembly.
"""

from asm_ops import *


def init_registers():
    return [
        set_reg(IP, const_cell(IP_INITIAL)),
        # register W doesn't need to be initialized
        set_reg(SP, const_cell(SP_INITIAL)),
        set_reg(RS, const_cell(RS_INITIAL)),
        block(
            jmp('init_registers', cond_expr=eqz(get_reg(CONT))),
            # Re-entering the interpreter after an FFI call.
            # Reload registers state from memory
            load_registers(),
            # Push into stack the result received (i.e. the
            # continuation result).
            push(SP, get_reg(CONT_RES)),
            label='init_registers',
        ),
    ]


def store_registers():
    """
    Store registers into the memory, so the interpeter can be restarted,
    similar to a context switch.
    """

    # NOTE: it's not necessary to store/reload register W, its value
    # will be refreshed from the IP
    return [
        store_cell(const_cell(IP_MEM_ADDR), get_reg(IP)),
        store_cell(const_cell(SP_MEM_ADDR), get_reg(SP)),
        store_cell(const_cell(RS_MEM_ADDR), get_reg(RS)),
    ]


def load_registers():
    """
    Load registers from the memory, to restart the interpeter,
    similar to a context switch.
    """

    return [
        set_reg(IP, load_cell(const_cell(IP_MEM_ADDR))),
        set_reg(SP, load_cell(const_cell(SP_MEM_ADDR))),
        set_reg(RS, load_cell(const_cell(RS_MEM_ADDR))),
    ]


def _branch():
    """
    Branch to the instruction indicated by the byte offset stored in the next cell
    pointed by IP
    """

    return [
        # relative jump to offset, bytes offset calculated and stored
        # after the current codeword
        set_reg(
            IP,
            add(
                get_reg(IP),
                # note: offset in bytes, user must manually skip the address
                load_cell(get_reg(IP)),
            ),
        ),
        jmp('next'),
    ]


def _call_iin(name):
    return [
        # store in temporary registers, so we can drop
        # from the stack before executing the FFI call
        set_reg(SCRATCH_1, peek(SP, 1)),
        set_reg(SCRATCH_2, peek(SP, 0)),
        drop(SP, 2),
        # store before the FFI call, so it can re-enter the interpeter both synchronously
        # and asynchronously
        store_registers(),
        call_iin(name, get_reg(SCRATCH_1), get_reg(SCRATCH_2)),
        # quit immediately, the FFI call might have re-entered
        # the interpreter multiple times already!
        jmp('entry'),
    ]


CODE_WORDS = [
    # Initiation codes (non-standard words)
    ('(docol)', [  # ( R: -- c-addr )
        push(RS, get_reg(IP)),
        set_reg(IP, add_cell_size(W, 1)),
        jmp('next'),
    ]),
    ('(doconst)', [  # ( -- x )
        push(SP, load_cell(get_reg(W), 1)),
        jmp('next'),
    ]),
    ('(dovar)', [  # ( -- a-addr )
        push(SP, add_cell_size(W, 1)),
        jmp('next'),
    ]),
    ('(dodoes)', [ # ( -- a-addr )
        push(RS, get_reg(IP)),
        push(SP, add_cell_size(W, 1)),
        # see the switch in assemble_interpreter, the cell pointed by
        # W contains the address to execute compiled in by (DOES>)
        set_reg(IP, load_cell(get_reg(W))),
        jmp('next'),
    ]),
    # FFI (non-standard words)
    # these quit the interpreter. The called foreign function must then re-enter it.
    ('READ', [  # ( c-addr u1 -- u2 )
        _call_iin('read'),
    ]),
    ('WRITE', [  # ( c-addr u1 -- u2 )
        _call_iin('write'),
    ]),
    # Non-standard extensions, useful to implement the interpreter
    ('lit', [ # ( -- x )
        # load literal value kept in next cell, which is now pointed by IP
        push(SP, load_cell(get_reg(IP))),
        inc(IP, 1),
        jmp('next'),
    ]),
    ('RP!', [ # ( a-addr -- )
        set_reg(RS, peek(SP, 0)),
        drop(SP, 1),
        jmp('next'),
    ]),
    ('RP@', [ # ( -- a-addr )
        inc(SP, -1),
        put(SP, 0, get_reg(RS)),
        jmp('next'),
    ]),
    ('SP!', [ # ( a-addr -- )
        set_reg(SP, peek(SP, 0)),
        jmp('next'),
    ]),
    ('SP@', [ # ( -- a-addr )
        # returns address of stack top on top of the stack,
        # counting the newly added address
        inc(SP, -1),
        put(SP, 0, get_reg(SP)),
        jmp('next'),
    ]),
    ('SKIP', [  # ( c-addr1 u1 c -- c-addr2 u2 )
        set_reg(SCRATCH_1, peek(SP, 0)),  # c
        set_reg(SCRATCH_2, peek(SP, 1)),  # u1
        set_reg(SCRATCH_3, peek(SP, 2)),  # c-addr1
        drop(SP, 1),
        loop(
            'SKIP-loop',
            block(
                jmp(
                    'SKIP-loop-done',
                    cond_expr=le_s(get_reg(SCRATCH_2), const_cell(0)),
                ),
                jmp(
                    'SKIP-loop-done',
                    cond_expr=ne(load_byte(get_reg(SCRATCH_3)), get_reg(SCRATCH_1)),
                ),
                set_reg(SCRATCH_2, sub(get_reg(SCRATCH_2), const_cell(1))),
                set_reg(SCRATCH_3, add(get_reg(SCRATCH_3), const_cell(1))),
                jmp('SKIP-loop'),
                label='SKIP-loop-done',
            ),
        ),
        put(SP, 0, get_reg(SCRATCH_2)),
        put(SP, 1, get_reg(SCRATCH_3)),
        jmp('next'),
    ]),
    ('SCAN', [  # ( c-addr1 u1 c -- c-addr2 u2 )
        set_reg(SCRATCH_1, peek(SP, 0)),  # c
        set_reg(SCRATCH_2, peek(SP, 1)),  # u1
        set_reg(SCRATCH_3, peek(SP, 2)),  # c-addr1
        drop(SP, 1),
        loop(
            'SCAN-loop',
            block(
                jmp(
                    'SCAN-loop-done',
                    cond_expr=le_s(get_reg(SCRATCH_2), const_cell(0)),
                ),
                jmp(
                    'SCAN-loop-done',
                    cond_expr=eq(load_byte(get_reg(SCRATCH_3)), get_reg(SCRATCH_1)),
                ),
                set_reg(SCRATCH_2, sub(get_reg(SCRATCH_2), const_cell(1))),
                set_reg(SCRATCH_3, add(get_reg(SCRATCH_3), const_cell(1))),
                jmp('SCAN-loop'),
                label='SCAN-loop-done',
            ),
        ),
        put(SP, 0, get_reg(SCRATCH_2)),
        put(SP, 1, get_reg(SCRATCH_3)),
        jmp('next'),
    ]),
    ('EQ-COUNTED', [  # ( c-addr1 c-addr2 -- flag )
        set_reg(SCRATCH_1, load_byte(peek(SP, 0))),  # n1
        set_reg(SCRATCH_2, load_byte(peek(SP, 1))),  # n2
        block(
            jmp('eq-counted-if', cond_expr=eq(get_reg(SCRATCH_1), get_reg(SCRATCH_2))),
            put(SP, 1, const_cell(0)),
            drop(SP, 1),
            jmp('next'),
            label='eq-counted-if',
        ),
        loop(
            'eq-counted-loop',
            block(
                block(
                    jmp(
                        'eq-counted-ok',
                        cond_expr=le_s(get_reg(SCRATCH_1), const_cell(0)),
                    ),
                    jmp(
                        'eq-counted-loop-fail',
                        cond_expr=ne(
                            load_byte(add(peek(SP, 0), get_reg(SCRATCH_1))),
                            load_byte(add(peek(SP, 1), get_reg(SCRATCH_1))),
                        ),
                    ),
                    set_reg(SCRATCH_1, sub(get_reg(SCRATCH_1), const_cell(1))),
                    jmp('eq-counted-loop'),
                    label='eq-counted-loop-fail',
                ),
                put(SP, 1, const_cell(0)),
                drop(SP, 1),
                jmp('next'),
                label='eq-counted-ok',
            ),
        ),
        put(SP, 1, const_cell(-1)),
        drop(SP, 1),
        jmp('next'),
    ]),
    # Branching/looping (non-standard words)
    ('branch', [  # ( -- )
        _branch(),
    ]),
    ('?branch', [  # ( x -- )
        block(
            jmp('?branch-if', cond_expr=ne(peek(SP, 0), const_cell(0))),
            drop(SP, 1),
            _branch(),
            label='?branch-if',
        ),
        drop(SP, 1),
        inc(IP, 1),  # if false, skip the address
        jmp('next'),
    ]),
    ('(do)', [  # ( limit index -- R: -- loop-end-addr limit index )
        inc(RS, -3),
        # copy limit and index in one go
        store_double_cell(get_reg(RS), load_double_cell(get_reg(SP))),
        put(RS, 2, load_cell(get_reg(IP))), # the loop end address, stored in the next cell
        inc(IP, 1), # skip the loop-end-addr
        drop(SP, 2),
        jmp('next'),
    ]),
    ('(loop)', [  # ( R: loop-end-addr limit index1 -- | loop-end-addr limit index2 )
        op_on_tos(add, const_cell(1), stack_reg=RS),
        block(
            jmp('(loop)-if', l_s(peek(RS, 0), peek(RS, 1))),
            drop(RS, 3),
            inc(IP, 1),  # skip the address
            jmp('next'),
            label='(loop)-if',
        ),
        _branch(),
    ]),
    ('(+loop)', [  # ( n -- R: loop-end-addr limit index1 -- | loop-end-addr limit index2 )
        op_on_tos(add, peek(SP, 0), stack_reg=RS),
        drop(SP, 1),
        block(
            jmp('(+loop)-if', l_s(peek(RS, 0), peek(RS, 1))),
            drop(RS, 3),
            inc(IP, 1),  # skip the address
            jmp('next'),
            label='(+loop)-if',
        ),
        _branch(),
    ]),

    # Core words

    # Stack manipulation
    ('>R', [  # ( x -- R: -- x )
        push(RS, peek(SP, 0)),
        drop(SP, 1),
        jmp('next'),
    ]),
    ('R>', [  # ( -- x R: x -- )
        push(SP, peek(RS, 0)),
        drop(RS, 1),
        jmp('next'),
    ]),
    ('R@', [  # ( -- x R: x -- x )
        push(SP, peek(RS, 0)),
        jmp('next'),
    ]),
    ('DROP', [  # ( x -- )
        drop(SP, 1),
        jmp('next'),
    ]),
    ('DUP', [  # ( x -- x x )
        push(SP, peek(SP, 1)),
        jmp('next'),
    ]),
    ('SWAP', [  # ( x1 x2 -- x2 x1 )
        set_reg(SCRATCH_1, peek(SP, 0)),
        put(SP, 0, peek(SP, 1)),
        put(SP, 1, get_reg(SCRATCH_1)),
        jmp('next'),
    ]),
    ('OVER', [  # ( x1 x2 -- x1 x2 x1 )
        push(SP, peek(SP, 2)),
        jmp('next'),
    ]),
    ('ROT', [  # ( x1 x2 x3 -- x2 x3 x1 )
        set_reg(SCRATCH_1, peek(SP, 2)),
        put(SP, 2, peek(SP, 1)),
        put(SP, 1, peek(SP, 0)),
        put(SP, 0, get_reg(SCRATCH_1)),
        jmp('next'),
    ]),
    ('NIP', [  # ( x1 x2 -- x2 )
        put(SP, 1, peek(SP, 0)),
        drop(SP, 1),
        jmp('next'),
    ]),
    ('TUCK', [  # ( x1 x2 -- x2 x1 x2 )
        inc(SP, -1),
        put(SP, 0, peek(SP, 1)),
        put(SP, 1, peek(SP, 2)),
        put(SP, 2, peek(SP, 0)),
        jmp('next'),
    ]),
    ('2DROP', [  # ( x x -- )
        drop(SP, 2),
        jmp('next'),
    ]),
    ('2OVER', [  # ( x1 x2 x3 x4 -- x1 x2 x3 x4 x1 x2 )
        inc(SP, -2),
        store_double_cell(get_reg(SP), load_double_cell(get_reg(SP), 4)),
        jmp('next'),
    ]),
    ('2SWAP', [  # ( x1 x2 x3 x4 -- x3 x4 x1 x2 )
        set_reg(SCRATCH_DOUBLE_1, load_double_cell(get_reg(SP))),
        store_double_cell(get_reg(SP), load_double_cell(get_reg(SP), 2)),
        store_double_cell(get_reg(SP), get_double_reg(SCRATCH_DOUBLE_1), 2),
        jmp('next'),
    ]),
    # Memory access
    ('@', [  # ( a-addr -- x )
        put(SP, 0, load_cell(peek(SP, 0))),
        jmp('next'),
    ]),
    ('!', [  # ( x a-addr -- )
        store_cell(peek(SP, 0), peek(SP, 1)),
        drop(SP, 2),
        jmp('next'),
    ]),
    ('+!', [ # ( n1|u1 a-addr -- )
        store_cell(
            peek(SP, 0),
            add(
                load_cell(peek(SP, 0)),
                peek(SP, 1),
            ),
        ),
        drop(SP, 2),
        jmp('next'),
    ]),
    ('C@', [  # ( a-addr -- x )
        put(SP, 0, load_byte(peek(SP, 0))),
        jmp('next'),
    ]),
    ('C!', [  # ( c c-addr -- )
        store_byte(peek(SP, 0), peek(SP, 1)),
        drop(SP, 2),
        jmp('next'),
    ]),
    ('CMOVE', [  # ( c-addr1 c-addr2 u -- )
        set_reg(SCRATCH_1, peek(SP, 2)),  # c-addr-1
        set_reg(SCRATCH_2, add(get_reg(SCRATCH_1), peek(SP, 0))),  # c-addr-1 + u
        set_reg(SCRATCH_3, peek(SP, 1)),  # c-addr-2
        loop(
            'cmove-loop',
            block(
                jmp(
                    'cmove-loop-done',
                    cond_expr=le_s(get_reg(SCRATCH_2), get_reg(SCRATCH_1)),
                ),
                store_byte(get_reg(SCRATCH_3), load_byte(get_reg(SCRATCH_1))),
                set_reg(SCRATCH_1, add(get_reg(SCRATCH_1), const_cell(1))),
                set_reg(SCRATCH_3, add(get_reg(SCRATCH_3), const_cell(1))),
                jmp('cmove-loop'),
                label='cmove-loop-done',
            ),
        ),
        drop(SP, 3),
        jmp('next'),
    ]),
    ('CMOVE>', [  # ( c-addr1 c-addr2 u -- )
        set_reg(SCRATCH_2, peek(SP, 0)),  # u
        set_reg(SCRATCH_1, peek(SP, 2)),  # c-addr-1
        set_reg(SCRATCH_3, sub(add(get_reg(SCRATCH_2), peek(SP, 1)), const_cell(1))),  # c-addr-2 + u - 1
        set_reg(SCRATCH_2, sub(add(get_reg(SCRATCH_2), get_reg(SCRATCH_1)), const_cell(1))),  # c-addr-1 + u - 1
        loop(
            'cmove>-loop',
            block(
                jmp(
                    'cmove>-loop-done',
                    cond_expr=l_s(get_reg(SCRATCH_2), get_reg(SCRATCH_1)),
                ),
                store_byte(get_reg(SCRATCH_3), load_byte(get_reg(SCRATCH_2))),
                set_reg(SCRATCH_2, sub(get_reg(SCRATCH_2), const_cell(1))),
                set_reg(SCRATCH_3, sub(get_reg(SCRATCH_3), const_cell(1))),
                jmp('cmove>-loop'),
                label='cmove>-loop-done',
            ),
        ),
        drop(SP, 3),
        jmp('next'),
    ]),
    # Loops
    ('I', [ # ( -- n|u R: loop-sys1 -- loop-sys1 )
        push(SP, peek(RS, 0)),
        jmp('next'),
    ]),
    ('J', [ # ( -- n|u R: loop-sys1 loop-sys2 -- loop-sys1 loop-sys2 )
        push(SP, peek(RS, 3)),  # a do-loop has 3 control parameters
        jmp('next'),
    ]),
    ('UNLOOP', [ # ( R: loop-end-addr sys1 sys2 -- )
        drop(RS, 3),
        jmp('next'),
    ]),
    ('LEAVE', [  # ( loop-end-addr limit index -- )
        set_reg(IP, peek(RS, 2)),
        drop(RS, 3),
        jmp('next'),
    ]),
    # Control
    ('EXECUTE', [  # ( i*x xt -- j*x )
        set_reg(W, peek(SP, 0)),
        drop(SP, 1),
        jmp('interpreter_switch'),
    ]),
    ('EXIT', [
        set_reg(IP, load_cell(get_reg(RS))),
        drop(RS, 1),
        jmp('next'),
    ]),
    ('BYE', [
        jmp('entry'),
    ]),
    # Type conversions
    ('S>D', [ # ( n -- d )
        inc(SP, -1),
        put_double(SP, 0, s_32_to_64(peek(SP, 1))),
        jmp('next'),
    ]),
    ('D>S', [ # ( d -- n )
        put(SP, 1, s_64_to_32(peek_double(SP, 0))),
        drop(SP, 1),
        jmp('next'),
    ]),
    # Comparisons
    ('=', [ # ( x1 x2 -- flag )
        cmp_neg(ne),
        jmp('next'),
    ]),
    ('<>', [  # ( x1 x2 -- x3 )
        cmp_neg(eq),
        jmp('next'),
    ]),
    ('<', [ # ( n1 n2 -- flag )
        cmp_neg(ge_s),
        jmp('next'),
    ]),
    ('>', [ # ( n1 n2 -- flag )
        cmp_neg(le_s),
        jmp('next'),
    ]),
    ('U<', [  # ( u1 u2 -- flag )
        cmp_neg(ge_u),
        jmp('next'),
    ]),
    ('U>', [  # ( u1 u2 -- flag )
        cmp_neg(le_u),
        jmp('next'),
    ]),
    ('0<', [ # ( n -- flag )
        cmp_neg_zero(ge_s),
        jmp('next'),
    ]),
    ('0=', [ # ( n -- flag )
        cmp_neg_zero(ne),
        jmp('next'),
    ]),
    # Bitwise operations
    ('INVERT', [  # ( x1 -- x2 )
        op_on_tos(bit_xor, const_cell(-1)),
        jmp('next'),
    ]),
    ('AND', [ # ( x1 x2 -- x3 )
        bin_op(bit_and),
        jmp('next'),
    ]),
    ('OR', [  # ( x1 x2 -- x3 )
        bin_op(bit_or),
        jmp('next'),
    ]),
    ('XOR', [  # ( x1 x2 -- x3 )
        bin_op(bit_xor),
        jmp('next'),
    ]),
    ('LSHIFT', [  # ( x1 u -- x2 )
        bin_op(ls),
        jmp('next'),
    ]),
    ('RSHIFT', [  # ( x1 u -- x2 )
        bin_op(l_rs),
        jmp('next'),
    ]),
    # Single-cell math
    ('NEGATE', [  # ( x1 -- x2 )
        op_on_tos(mul, const_cell(-1)),
        jmp('next'),
    ]),
    ('+', [ # ( n1|u1 n2|u2 -- n3|u3 )
        bin_op(add),
        jmp('next'),
    ]),
    ('-', [ # ( n1|u1 n2|u2 -- n3|u3 )
        bin_op(sub),
        jmp('next'),
    ]),
    ('*', [ # ( n1 n2 -- n3 )
        bin_op(mul),
        jmp('next'),
    ]),
    ('/MOD', [ # ( n1 n2 -- n_rem n_quot )
        set_reg(SCRATCH_1, div(peek(SP, 1), peek(SP, 0))),
        put(SP, 1, rem(peek(SP, 1), peek(SP, 0))),
        put(SP, 0, get_reg(SCRATCH_1)),
        jmp('next'),
    ]),
    ('1+', [ # ( n1|u1 -- n2|u2 )
        op_on_tos(add, const_cell(1)),
        jmp('next'),
    ]),
    ('1-', [ # ( n1|u1 -- n2|u2 )
        op_on_tos(add, const_cell(-1)),
        jmp('next'),
    ]),
    ('2*', [ # ( x1 -- x2 )
        op_on_tos(ls, const_cell(1)),
        jmp('next'),
    ]),
    ('2/', [ # ( x1 -- x2 )
        op_on_tos(a_rs, const_cell(1)),
        jmp('next'),
    ]),
    # Mixed math
    ('M*', [ # ( n1 n2 -- d )
        bin_op_32_32_64(mul_32_32_64),
        jmp('next'),
    ]),
    ('UM*', [ # ( u1 u2 -- ud )
        bin_op_32_32_64(umul_32_32_64),
        jmp('next'),
    ]),
    ('SM/REM', [ # ( d1 n1 -- n_rem n_quot )
        set_reg(SCRATCH_1, div_64_32_32(peek_double(SP, 1), peek(SP, 0))),
        put(SP, 2, rem_64_32_32(peek_double(SP, 1), peek(SP, 0))),
        put(SP, 1, get_reg(SCRATCH_1)),
        drop(SP, 1),
        jmp('next'),
    ]),
    ('UM/MOD', [ # ( ud u1 -- u_rem u_quot )
        set_reg(SCRATCH_1, udiv_64_32_32(peek_double(SP, 1), peek(SP, 0))),
        put(SP, 1, urem_64_32_32(peek_double(SP, 1), peek(SP, 0))),
        put(SP, 2, get_reg(SCRATCH_1)),
        drop(SP, 1),
        jmp('next'),
    ]),
    ('UD/MOD', [ # ( ud1 u1 -- ud_quot u_rem )
        set_reg(SCRATCH_DOUBLE_1, udiv_64_32_64(peek_double(SP, 1), peek(SP, 0))),
        put(SP, 0, urem_64_32_32(peek_double(SP, 1), peek(SP, 0))),
        put_double(SP, 1, get_double_reg(SCRATCH_DOUBLE_1)),
        jmp('next'),
    ]),
    # Double-cell math
    ('DNEGATE', [  # ( d1 -- d2 )
        put_double(SP, 0, mul_64(peek_double(SP, 0), const_double_cell(-1))),
        jmp('next'),
    ]),
    ('D+', [  # ( d1|ud1 d2|ud2 -- d3|ud3 )
        put_double(SP, 2, add_64(peek_double(SP, 2), peek_double(SP, 0))),
        drop(SP, 2),
        jmp('next'),
    ]),
    ('D*', [ # ( d1|ud1 d2|ud2 -- d3|ud3 )
        put_double(SP, 2, mul_64(peek_double(SP, 2), peek_double(SP, 0))),
        drop(SP, 2),
        jmp('next'),
    ]),
]
