"""
Constants that define the memory layout.
"""

from _binaryen_c import lib


CELL_SIZE = 4
CELL_TYPE = lib.BinaryenInt32()
DOUBLE_CELL_TYPE = lib.BinaryenInt64()

# Interpreter parameters
TASK_BASE_PARAM = 0
TASK_PARAM = 1

# registers, stored as local variables in the evaluation function
IP = 2  # instruction pointer
W = 3  # address of the codeword of the word being executed
SP = 4  # stack pointer, points to the top of the stack (grow downwards)
RS = 5  # return stack pointer, points to the top of the stack  (grow downwards)
SCRATCH_1 = 6 # whatever
SCRATCH_2 = 7 # whatever
SCRATCH_3 = 8 # whatever
SCRATCH_DOUBLE_1 = 9 # whatever

# Memory layout:

# bytes: 0 .. 11k: main task memory area
MAIN_TASK_BASE_VALUE = 0

# bytes: 0 .. 12: main task saved registers
# register offsets, registers are saved/loaded from get_reg(TASK_BASE_PARAM) + OFFSET
IP_MEM_OFFSET = 0
SP_MEM_OFFSET = IP_MEM_OFFSET + CELL_SIZE
RS_MEM_OFFSET = SP_MEM_OFFSET + CELL_SIZE

# bytes: 12 .. 16: offset to the address of the initial forth word to run when the interpreter starts
IP_INITIAL_OFFSET = RS_MEM_OFFSET + CELL_SIZE

# bytes: 16 ... 1k: random bytes (to avoid a simple return stack
# overflow to overwrite the registers)

# bytes: 1k ... 5k: return stack
RS_INITIAL_OFFSET = 5 * 1024 + CELL_SIZE  # stack empty, point one cell above start of stack

# bytes: 5k ... 6k: random bytes (to avoid a simple return stack
# underflow to overwrite the params stack)

# bytes: 6k ... 10k: params stack
SP_INITIAL_OFFSET = 10 * 1024 + CELL_SIZE  # stack empty, point one cell above start of stack

# bytes: 10k ... 11k: random bytes (to avoid a simple params stack
# underflow to overwrite the buffers)

# main task memory area ends here

# bytes: 11k ... 15k: I/O buffers
BUFFER_START = 11 * 1024

# bytes: 15k ... 19k: pad (multi-purpose memory area for use by forth code)
PAD_START = 15 * 1024

# bytes: 19k ... 20k: scratch area used by the interpreter to keep
# parsed words
INTERPRET_WORD = 19 * 1024

# bytes: 20k ... : dictionary
HERE_INITIAL = 20 * 1024
