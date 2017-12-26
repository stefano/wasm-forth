"""
Forth interepter, defined in Forth within Python.
"""

from asm_ops import *
from memory_layout import *


def forth_def(label, *code, immediate=False):
    """
    Splits each code string into forth byte-string words, and returns a flat list of words.
    Also allows to define labels using '~<label name>', which are not returned as words,
    and label references using ':~<label-name>', which are replaced by an integer offset
    from the current position to the label definition.
    """

    # first, find labels and their offset from the start of the colon definition
    jump_labels = {}
    code_offset = 0
    for item in code:
        if isinstance(item, int):
            # literals use 2 cells
            code_offset += 2
            continue
        else:
            for word in item.split(' '):
                if word == '':
                    continue

                if word.startswith('~'):
                    # a label definition
                    jump_labels[word] = code_offset
                    continue
                elif word.startswith(':~'):
                    # a label reference, will use 1 cell
                    code_offset += 1
                    continue

                try:
                    int(word)
                    # an int literal
                    code_offset += 2
                except ValueError:
                    # it's a word reference
                    code_offset += 1

    res = []
    for item in code:
        if isinstance(item, int):
            res.append('lit')
            res.append(item)
        else:
            for word in item.split(' '):
                if word == '':
                    continue

                if word.startswith('~'):
                    # don't add labels to ouput
                    continue
                elif word.startswith(':~'):
                    jump_label = word[1:]
                    offset = CELL_SIZE * (jump_labels[jump_label] - len(res))
                    res.append(offset)
                    continue

                try:
                    value = int(word)
                    res.append('lit')
                    res.append(value)
                except ValueError:
                    res.append(word)

    return label, res, immediate


WORD_NOT_FOUND_ERR = b'word not found: '
OK_MSG = b' ok\n'


FORTH_CONSTANTS = [
    ('IN-BUF-MAX', PAD_START - BUFFER_START),
    ('PAD', PAD_START),
]


FORTH_VARIABLES = [
    ('STATE', 0),
    ('SOURCE-ID', 0),
    ('IN-BUF', BUFFER_START),
    ('>IN', 0),
    ('IN-BUF-EOL', -1),  # index of line terminator in input buffer
    ('IN-BUF-SIZE', 0),  # number of chars in input buffer
    ('\'HERE', 0),
    ('LATEST', 0),  # not standard: pointer to start of the last defined word (points to the address of the name length)
    ('BASE', 10),
    ('WORD-NOT-FOUND-ERR', WORD_NOT_FOUND_ERR),
    ('QUIET', 0),  # not standard: tells if the interpreter prints " OK"
    ('OK-MSG', OK_MSG),
]


FORTH_COL_DEFS = [
    forth_def(
        'HERE',  # ( -- a-addr )
        '\'HERE @',
    ),
    forth_def(
        'ALLOT',  # ( n -- )
        '\'HERE +!',
    ),
    forth_def(
        'CELL+',  # ( a-addr1 -- a-addr2 )
        CELL_SIZE, '+',
    ),
    forth_def(
        'SOURCE',  # ( -- c-addr u )
        'IN-BUF @',
        'IN-BUF-EOL @',
    ),
    forth_def(
        'SCAN-NEWLINE',  # ( -- newline-addr u )
        'IN-BUF @ IN-BUF-SIZE @', ord('\n'), 'SCAN',
    ),
    forth_def(
        'ADDR>IN-BUF-EOL!',  # ( newline-addr -- )
        'IN-BUF @ - IN-BUF-EOL !',
    ),
    forth_def(
        'LINE',  # ( -- c-addr u )
        'IN-BUF @', # ( in )
        'IN-BUF-EOL @ 1+', # ( in index-after-newline )
        'OVER +', # ( in new-line-addr+1 )
        'SWAP IN-BUF-SIZE @ 1- IN-BUF-EOL @ - DUP >R', # ( new-line-addr+1 in n-remaining R: n-remaining )
        'CMOVE', # ( R: n-remaining )
        'R> IN-BUF-SIZE !', # ( )
        'SCAN-NEWLINE', # ( newline-addr u )
        '0 > ?branch :~REFILL', # ( newline-addr )
        'ADDR>IN-BUF-EOL! branch :~FINISH',
        '~REFILL',
        'IN-BUF-MAX IN-BUF-SIZE @ - READ IN-BUF-SIZE +!', # ( )
        # even if we don't find a newline now, consider it a newline
        'SCAN-NEWLINE DROP ADDR>IN-BUF-EOL!',
        '~FINISH SOURCE',
    ),
    forth_def(
        'BL',  # ( -- c )
        ord(b' '),
    ),
    forth_def(
        '2DUP',  # ( x -- x x )
        'OVER OVER'
    ),
    forth_def(
        'CHAR+',  # ( a-addr1 -- a-addr2 )
        '1+'
    ),
    forth_def(
        '>COUNTED',  # ( a-addr-src n a-addr-dst -- )
        '2DUP C! CHAR+ SWAP CMOVE'
    ),
    forth_def(
        '/STRING',  # ( a-addr u n -- a-addr+n u-n )
        'DUP >R -',  # ( a-addr u-n R: n )
        'SWAP R> +',  # ( u-n a-addr+n R: )
        'SWAP',
    ),
    forth_def(
        '_WORD',  # ( dest-addr c -- c-addr )
        '>R SOURCE >IN @ /STRING R@ SKIP',  # ( dest-addr c-addr-start u-start R: c )
        'SWAP DUP ROT', # ( dest-addr c-addr-start c-addr-start u-start R: c )
        'R> SCAN', # ( dest-addr c-addr-start c-addr-end u-end R: )
        '>R OVER -', # ( dest-addr c-addr-start (c-addr-end-c - addr-start) R: u-end )
        'ROT DUP >R >COUNTED R>', # ( dest-addr R: u-end )
        'SOURCE R@ - + R>', # ( dest-addr c-addr-end u-end )
        '1 /STRING', # ( dest-addr c-addr-end-skipped u-end-skipped )
        'SOURCE ROT -', # ( dest-addr c-addr-end-skipped c-addr (u - u-end-skipped) )
        '>IN ! DROP DROP', # ( dest-addr )
    ),
    forth_def(
        'WORD',  # ( c -- c-addr )
        'HERE SWAP _WORD',
    ),
    forth_def(
        'ALIGNED',  # ( u1 -- u2 )
        CELL_SIZE, 'OVER', CELL_SIZE - 1, 'AND -', CELL_SIZE - 1, 'AND +',
    ),
    forth_def(
        'COUNT',  # ( c-addr1 -- c-addr2 u )
        'DUP C@ SWAP 1+ SWAP',
    ),
    forth_def(
        'FIND',  # ( c-addr -- c-addr 0  |  xt 1  |  xt -1 )
        '>R', # ( R: c-addr )
        'LATEST @', # ( a-addr R: c-addr )
        '~LOOP DUP 0=', # ( a-addr flag R: c-addr )
        '?branch :~NOT-ZERO', # ( a-addr R: c-addr )
        'DROP R> 0 EXIT', # ( c-addr 0 )
        '~NOT-ZERO DUP R@', # ( a-addr a-addr c-addr R: c-addr )
        'EQ-COUNTED', # ( a-addr flag R: c-addr )
        '?branch :~NOT-EQ', # ( a-addr R: c-addr )
        'DUP DUP C@ 127 AND 1+ + ALIGNED', # ( a-addr a-addr' R: c-addr ) 127 AND to remove the smudge bit
        'SWAP 1-', # ( a-addr' (a-addr - 1) R: c-addr )
        'C@ 1 =', # ( a-addr' is-imm-flag R: c-addr )
        'R> DROP', # ( a-addr' is-imm-flag )
        '0= 1 OR EXIT', # ( a-addr' -1/1 )
        '~NOT-EQ', CELL_SIZE, '- 1-', # ( (a-addr - 5) )
        '@ branch :~LOOP'
    ),
    forth_def(
        'DIGIT',  # ( char -- u flag )
        'DUP 48 < OVER 57 > OR ?branch :~parse-dec', # jump when 48 <= c <= 57 (i.e. '0'..'9')
        'DUP 65 < OVER 90 > OR ?branch :~parse-alpha-upper', # jump when 65 <= c <= 90 (i.e. 'A'..'Z')
        'DUP 97 < OVER 122 > OR ?branch :~parse-alpha-lower', # jump when 97 <= c <= 122 (i.e. 'a'..'z')
        '0 EXIT', # else not found
        '~parse-dec 48 - branch :~done',
        '~parse-alpha-upper 65 - 10 + branch :~done',
        '~parse-alpha-lower 97 - 10 + branch :~done',
        '~done DUP BASE @ < ?branch :~out-of-base',
        '-1 EXIT',
        '~out-of-base 0',
    ),
    forth_def(
        'SKIP-SIGN',  # ( c-addr1 u1 -- c-addr2 u2 )
        'DUP ?branch :~DONE', # end if empty
        'OVER C@ 45 = ?branch :~DONE', # end if doesn't start with '-'
        '1 /STRING',
        '~DONE',
    ),
    forth_def(
        'NEGATIVE',  # ( char -- flag )
        ord('-'), '=',
    ),
    forth_def(
        'BASE*',  # ( ud1 -- ud2 )
        'BASE @ S>D D*',
    ),
    forth_def(
        '>NUMBER',  # ( ud1 c-addr1 u1 -- ud2 c-addr2 u2 )
        '~LOOP',
        'DUP ?branch :~END', # if empty, go to end
        'OVER C@ DIGIT ?branch :~PARTIAL', # if can't parse digit, error
        'SWAP >R SWAP >R >R BASE* R> S>D D+ R> R> 1 /STRING branch :~LOOP',
        '~PARTIAL DROP', # drop unparsed digit
        '~END',
    ),
    forth_def(
        'COUNTED>NUMBER',  # ( c-addr -- d 1 | n 2 | 0 )
        '0 0 ROT', # ( 0 0 c-addr )
        'COUNT OVER C@ NEGATIVE >R',  # ( 0 0 c-addr1 u R: negative-flag )
        'SKIP-SIGN >NUMBER',  # ( ud2 c-addr2 u2 R: negative-flag )
        'R> ?branch :~FINISH', # ( ud2 c-addr2 u2 )
        # negative
        '>R >R DNEGATE R> R>',
        '~FINISH', # ( ud2 c-addr2 u2 )
        'DUP ?branch :~SINGLE', # jump if no char left unconverted
        '1 = ?branch :~ERROR', # jump if more than 1 char unconverted ( ud2 c-addr2 )
        'DUP C@ 46 = ?branch :~ERROR', # jump if doesn't end in '.'
        'DROP 1 EXIT', # double number
        '~SINGLE DROP DROP D>S 2 EXIT', # single number
        '~ERROR DROP DROP DROP 0', # error
    ),
    forth_def(
        ',',  # ( x -- )
        'HERE ! 0 CELL+ ALLOT',
    ),
    forth_def(
        'C,',  # ( c -- )
        'HERE C! 1 ALLOT',
    ),
    forth_def(
        '(LITERAL)',  # ( x -- )
        'lit lit , ,', # yep, literal of itself
    ),
    forth_def(
        'INTERPRET',  # ( x*j -- y*i flag )
        '~I-LOOP',
        INTERPRET_WORD, 'BL _WORD',
        'DUP C@ ?branch :~EMPTY-WORD',  # skip empty words
        'FIND',
        'DUP ?branch :~NOT-FOUND',
        # found
        '-1 = ?branch :~IMM', # immediate word
        'STATE @ ?branch :~IMM', # interpretation state
        # compile
        ', branch :~DONE',
        # execute
        '~IMM EXECUTE branch :~DONE',
        # parse number
        '~NOT-FOUND DROP DUP >R COUNTED>NUMBER',
        'DUP ?branch :~NOT-NUMBER',
        'R> DROP',
        'STATE @ ?branch :~DONE-NUMBER', # am I interpreting?
        'DUP 1 = ?branch :~SINGLE-NUMBER',
        # compiling double number
        'DROP SWAP (LITERAL) (LITERAL) branch :~DONE',
        # compiling single number
        '~SINGLE-NUMBER DROP (LITERAL) branch :~DONE',
        '(LITERAL) branch :~DONE',
        '~EMPTY-WORD DROP branch :~DONE',
        '~DONE-NUMBER DROP',
        '~DONE',
        # continue interpreting if there are more words in the parse
        # area
        'SOURCE SWAP DROP >IN @ SWAP < INVERT ?branch :~I-LOOP',
        '-1 EXIT',
        '~NOT-NUMBER WORD-NOT-FOUND-ERR', len(WORD_NOT_FOUND_ERR), 'WRITE DROP R> COUNT WRITE DROP',
    ),
    forth_def(
        'OK',  # ( -- )
        'QUIET @ ?branch :~VERBOSE EXIT ~VERBOSE OK-MSG', len(OK_MSG), 'WRITE DROP',
    ),
    forth_def(
        'RESET-SP',  # ( -- )
        SP_INITIAL, 'SP!',
    ),
    forth_def(
        'QUIT', # (  x*j -- y*i )
        '~START',
        RS_INITIAL, 'RP!',
        '0 SOURCE-ID !',
        BUFFER_START, 'IN-BUF !',
        -1, 'IN-BUF-EOL !',
        0, 'IN-BUF-SIZE !',
        '0 STATE !',
        '~LOOP 0 >IN ! LINE DROP DROP INTERPRET',
        '0= ?branch :~OK',
        'RESET-SP branch :~START', # simulate abort without recursive calls
        '~OK STATE @ 0= ?branch :~LOOP OK', # show prompt only if in interpretation state
        'branch :~LOOP', # infinite loop
    ),
    forth_def(
        'ABORT', # (  x*j -- y*i )
        'RESET-SP QUIT',
    ),
    forth_def(
        'HEADER',  # ( -- )
        'LATEST @ , 0 C, HERE LATEST ! BL WORD HERE OVER C@ 1+ DUP >R CMOVE R> 1+ ALIGNED 1- ALLOT',
    ),
    forth_def(
        ':',  # ( -- word-addr )
        # 128 OR applies the smudge bit to keep this definition hidden
        'HEADER LATEST @ DUP C@ 128 OR OVER C! lit (docol) @ , 1 STATE !',
    ),
    forth_def(
        ';',  # ( word-addr -- )
        # 127 AND un-smudges the length
        '0 STATE ! lit EXIT , DUP C@ 127 AND SWAP C!',
        immediate=True,
    ),
]
