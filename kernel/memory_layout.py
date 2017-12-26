"""
Constants that define the memory layout.
"""

from _binaryen_c import lib


CELL_SIZE = 4
CELL_TYPE = lib.BinaryenInt32()
DOUBLE_CELL_TYPE = lib.BinaryenInt64()

# Interpreter parameters
CONT = 0
CONT_RES = 1

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

# bytes: 0 ... 16: registers
IP_MEM_ADDR = 0
W_MEM_ADDR = IP_MEM_ADDR + CELL_SIZE
SP_MEM_ADDR = W_MEM_ADDR + CELL_SIZE
RS_MEM_ADDR = SP_MEM_ADDR + CELL_SIZE

# bytes: 16 ... 20: address of initial forth word to run when the
# interpreter starts
IP_INITIAL = RS_MEM_ADDR + CELL_SIZE

# bytes: 20 ... 1k: random bytes (to avoid a simple return stack
# overflow to overwrite the registers)

# bytes: 1k ... 5k: return stack
RS_INITIAL = 5 * 1024 + CELL_SIZE  # stack empty, point one cell above start of stack

# bytes: 5k ... 6k: random bytes (to avoid a simple return stack
# underflow to overwrite the registers)

# bytes: 6k ... 10k: I/O buffers
BUFFER_START = 6 * 1024

# bytes: 10k ... 14k: pad (multi-purpose memory area for use by forth code)
PAD_START = 10 * 1024

# bytes: 14k ... 15k: random bytes (to avoid a simple params stack
# overflow to overwrite the registers)

# bytes: 15k ... 19k: params stack
SP_INITIAL = 19 * 1024 + CELL_SIZE  # stack empty, point one cell above start of stack

# bytes: 19k ... 19k+511: random bytes (to avoid a simple params stack
# underflow to overwrite the registers)

# bytes: 19k+512 ... 20k: scratch area used by the interpreter to keep
# parsed words
INTERPRET_WORD = 19 * 1024 + 512

# bytes: 20k ... 64k: dictionary
HERE_INITIAL = 20 * 1024
