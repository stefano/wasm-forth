1 QUIET !

( utils )

: MB 1024 * 1024 * ;

: 2exec ( x w1 w2 -- x1 x2 ) 2>R DUP R> EXECUTE SWAP R> EXECUTE SWAP ;
: 2exec1 ( x1 x2 w -- x3 x4 ) DUP >R EXECUTE SWAP R> EXECUTE SWAP ;
: exec-under ( x1 x2 w -- x3 x2 ) SWAP >R EXECUTE R> ;

: compile-push-word ( "<spaces>name" -- ) lit lit , ' , ;
: /top compile-push-word ['] exec-under , ; IMMEDIATE
: 2& compile-push-word ['] 2exec1 , ; IMMEDIATE
: pop-here ( -- x ) HERE -1 CELLS + @ -1 CELLS 'HERE +! ;
: & pop-here lit lit , , compile-push-word ['] 2exec , ; IMMEDIATE

: emit" 34 EMIT ;

: buffer ( "<space>name" size -- ) CELLS CREATE DUP HERE + 2 CELLS + , HERE CELL+ , ALLOT DOES> 2 CELLS + ;
: buf-next ( buf -- addr ) -1 CELLS + ;
: buf-cell-rel ( n buf -- addr ) buf-next @ SWAP CELLS + @ ;
: buf-end ( buf -- u ) -2 CELLS + @ ;
: buf-reset ( buf -- ) DUP buf-next ! ;
: buf-assert-space ( n-bytes buf -- ) buf-end & buf-next @ ROT + < IF abort-task" buffer out of space" THEN ;
: ,buf ( x buf -- ) 1 CELLS OVER buf-assert-space TUCK buf-next @ ! buf-next 1 CELLS SWAP +! ;
: buf-empty? ( buf -- flag ) DUP buf-next @ = ;
: .buffer ( buf -- )
  DUP buf-empty? IF DROP ." empty" EXIT THEN
  DUP buf-next @ SWAP DO I @ . 1 CELLS +LOOP ;

: -ROT ( x1 x2 x3 -- x3 x1 x2 ) ROT ROT ;
: 2@ ( addr1 addr2 -- x1 x2 ) @ SWAP @ SWAP ;
: idiv /MOD SWAP DROP ;
: swap-vars ( a1 a2 -- ) 2DUP 2@ >R SWAP ! R> SWAP ! ;

: word-cstr ( "<spaces>name" --, E: -- c-addr ) CREATE LATEST @ , DOES> @ ;

: last-char ( addr u -- c ) + 1- C@ ;
: trim ( addr u -- addr1 u1 ) BL SKIP BEGIN 2DUP last-char BL = OVER 0 > AND WHILE 1- REPEAT ;

( merge sort )

VARIABLE sort-cell-size

: sort-cells ( n1 -- n2 ) sort-cell-size @ * ;
: sort-cell+ ( n1 -- n2 ) sort-cell-size @ + ;
: sort-cell-cp ( addr1 addr2 -- ) sort-cell-size @ CMOVE ;
: sort-cell-aligned ( u1 -- u2 )
  sort-cell-size @ /MOD SWAP 0 > IF 1+ THEN sort-cell-size @ * ;

1 31 LSHIFT 1- CONSTANT max-int
: /2-aligned 1 RSHIFT sort-cell-aligned ;

: cp ( to end start -- to-end )
  DO I @ OVER ! CELL+ 1 CELLS +LOOP max-int OVER ! 1 CELLS sort-cell-aligned + ;
: prepare ( end mid mid start -- buf-mid buf-start )
  HERE -ROT cp DUP >R -ROT cp DROP R> HERE ;
: split ( end start -- end mid mid start )
  2DUP SWAP OVER - /2-aligned + DUP ROT ;
: merge ( end start -- )
  2DUP split prepare
  2SWAP DO 2DUP 2@ < IF SWAP THEN DUP I sort-cell-cp sort-cell+ sort-cell-size @ +LOOP 2DROP ;
: merge-sort ( end start -- )
  2DUP - 2 sort-cells < IF 2DROP EXIT THEN
  2DUP split RECURSE RECURSE merge ;
: sort ( addr n -- ) sort-cells OVER + SWAP merge-sort ;

( DOM VM )

word-cstr text-node-type
word-cstr text-attr-type

1 MB buffer ops

: push-op ( arg op -- ) ops ,buf ops ,buf ;
: prev-op ( -- op ) ops buf-empty? IF 0 ELSE -2 ops buf-cell-rel @ THEN ;
: rm-attr ( type -- ) 1 push-op ;
: set-attr ( addr -- ) DUP @ text-attr-type = IF 10 push-op ELSE 2 push-op THEN ;
: mk-node ( type -- ) DUP text-node-type = IF 9 push-op ELSE 3 push-op THEN ; ( note: this won't advance the position )
: skip-node ( -- ) prev-op 4 = IF 1 -1 ops buf-cell-rel +! ELSE 1 4 push-op THEN ;
: rm-node ( -- ) 0 5 push-op ;
: enter-node ( -- ) 0 6 push-op ;
: leave-node ( -- ) prev-op 6 = IF -2 CELLS ops buf-next +! ELSE 0 7 push-op THEN ;
: stop ( -- ) 0 8 push-op ;

( node & attr structures )

( buffers for use by client code, to keep any non-static strings/event handlers/etc referenced by the vdom )
1 MB buffer render-buf-1
1 MB buffer render-buf-2
VARIABLE render-buf-n render-buf-1 render-buf-n !
VARIABLE render-buf-c render-buf-2 render-buf-c !

: render-buf ( -- buf ) render-buf-n @ ;
: ,rbuf ( x -- ) render-buf ,buf ;
: to-rbuf ( addr1 u -- addr2 u )
  DUP render-buf buf-assert-space
  render-buf buf-next @ >R TUCK R@ SWAP CMOVE DUP render-buf buf-next +! R> SWAP ;

1 MB buffer dom-buf-1
1 MB buffer dom-buf-2
VARIABLE dom-n dom-buf-1 dom-n !
VARIABLE dom-c dom-buf-2 dom-c !

: reset-ndom-bufs ( -- ) dom-n @ buf-reset render-buf buf-reset ;
: swap-diff-buffers ( -- )
  dom-n dom-c swap-vars
  render-buf-n render-buf-c swap-vars ;
: ndom-here ( -- addr ) dom-n @ buf-next ;
: cdom-here ( -- addr ) dom-c @ buf-next ;
: ,ndom ( n -- ) dom-n @ ,buf ;

3 CELLS CONSTANT attr-size
: attr-end-sentinel ( -- ) max-int ,ndom 0 ,ndom 0 ,ndom ;

3 CELLS CONSTANT node-header-size
: node-start ( type -- node ) ndom-here @ SWAP ,ndom attr-size ,ndom 0 ,ndom attr-end-sentinel ;

: empty-node ( -- node ) 0 node-start ;

: node-type ( node -- x ) @ ;
: node-attr-size-cell ( node -- addr ) 1 CELLS + ;
: node-attr-size ( node -- n ) node-attr-size-cell @ ;
: node-children-size-cell ( node -- addr ) 2 CELLS + ;
: node-children-size ( node -- n ) node-children-size-cell @ ;

: cur-node-size ( node -- node n ) ndom-here @ OVER - ;
: node-end ( node -- )
  empty-node DROP
  cur-node-size node-header-size - OVER node-attr-size - SWAP node-children-size-cell ! ;

: first-child ( node-addr -- addr ) DUP node-attr-size + node-header-size + ;
: next-child ( node-addr -- addr2 )
  DUP DUP node-attr-size SWAP node-children-size node-header-size + + + ;
: node-n-attrs ( node-addr -- n ) node-attr-size attr-size idiv 1- ; ( don't count sentinel )
: attr-start ( node-addr -- attr-addr ) node-header-size + ;
: attr-len-cell ( addr1 -- addr2 ) CELL+ ;
: attr-str-cell ( addr1 -- addr2 ) 2 CELLS + ;
: attr-type ( addr1 -- x ) @ ;
: attr-len ( addr1 -- x ) attr-len-cell @ ;
: attr-str ( addr1 -- x ) attr-str-cell @ ;
: inc-attr-size ( node -- node ) attr-size OVER node-attr-size-cell +! ;
: !attr ( node attr-type value-addr value-len -- node )
  attr-size NEGATE ndom-here +! ( remove previous sentinel )
  ROT ,ndom ,ndom ,ndom attr-end-sentinel inc-attr-size ;

: text ( addr n -- )
  text-node-type node-start text-attr-type 2SWAP !attr node-end ;

: reset-ndom ( -- ) reset-ndom-bufs empty-node DROP reset-ndom-bufs ;

( diffing )

: sort-attrs ( node-addr -- )
  attr-size sort-cell-size !
  attr-start & node-n-attrs sort ; ( don't sort sentinel )
: rem-cur-attr ( cur-attr1 next-attr1 -- cur-attr1 next-attr1 ) OVER rm-attr ;
: add-next-attr ( cur-attr1 next-attr1 -- cur-attr1 next-attr1 ) DUP set-attr ;
: attrs-more? ( addr -- flag ) @ max-int <> ;
: is-attr-xt? ( addr -- flag ) attr-len max-int = ;
: attr-value-diff ( cur-attr1 next-attr1 -- cur-attr1 next-attr1 )
  2DUP 2DUP 2& attr-len = -ROT 2& attr-str = AND IF EXIT THEN
  add-next-attr ;
: inc-attr ( addr1 -- addr2 ) DUP attrs-more? IF attr-size + THEN ;
: attr-diff-1 ( cur-attr1 next-attr1 -- cur-attr2 next-attr2 )
  2DUP 2& attr-type = IF attr-value-diff 2& inc-attr ELSE
  2DUP 2& attr-type < IF rem-cur-attr /top inc-attr ELSE ( note: sentinel is max-int )
                         add-next-attr inc-attr
  THEN THEN ;
: attr-diff ( cur-node next-node -- )
  2DUP sort-attrs sort-attrs
  2& attr-start BEGIN 2DUP 2& attrs-more? OR WHILE attr-diff-1 REPEAT 2DROP ;

: first-children ( cur-node next-node -- cur-node1 next-node1 ) 2& first-child ;
: next-children ( cur-node next-node -- cur-node1 next-node1 ) 2& next-child ;
: next-child-next next-child ;
: next-child-cur /top next-child ;

: is-child? ( parent-node node -- flag ) SWAP next-child < ;
: end-node? ( node -- flag ) @ 0= ;
: create-attrs ( node -- )
  attr-start BEGIN DUP attrs-more? WHILE DUP set-attr attr-size + REPEAT DROP ;
: create-tree ( node -- )
  DUP node-type mk-node
  DUP create-attrs
  first-child enter-node BEGIN DUP end-node? INVERT WHILE DUP RECURSE next-child REPEAT leave-node skip-node
  DROP ;
: node-diff ( cur-node1 next-node1 -- cur-node2 next-node2 )
  2DUP 2& end-node? AND IF leave-node skip-node next-children ELSE
  2DUP 2& node-type = IF 2DUP attr-diff enter-node first-children ELSE
  DUP end-node? IF rm-node next-child-cur ELSE
  DUP create-tree next-child-next THEN THEN THEN ;
: more-nodes? ( cur-node next-node -- flag )
  ndom-here @ < SWAP cdom-here @ < OR ;
: nodes-diff ( cur-node next-node -- )
  BEGIN 2DUP more-nodes? WHILE node-diff REPEAT 2DROP ;
: diff ( -- )
  ops buf-reset dom-c @ dom-n @ nodes-diff stop swap-diff-buffers ;

: render ( xt -- )
  reset-ndom EXECUTE diff ops 0 PATCH-BODY ;

: def-tag CREATE LATEST @ , DOES> @ node-start ;
: closed-by CREATE DOES> DROP node-end ;

: def-attr CREATE LATEST @ , DOES> @ -ROT !attr ;

: def-event CREATE LATEST @ , DOES> @ SWAP -1 !attr ;

: (bind) ( data xt1 -- xt2 )
  render-buf buf-next @ >R SWAP
  lit (docol) @ ,rbuf lit lit ,rbuf ,rbuf ,rbuf lit EXIT ,rbuf R> ;
: bind ( "<spaces>name" -- ) compile-push-word ['] (bind) , ; IMMEDIATE

: empty-attr ( -- c-addr u ) S" " ;
: fmt-int ( n -- addr u ) S>D <# #S #> to-rbuf ;

VARIABLE render-xt
: repaint ( -- ) render-xt @ render ;
: repaint-with ( "<spaces>name" -- ) ' render-xt ! ;

( define a few common tags/attrs/events )

def-tag <footer> closed-by </footer>
def-tag <section> closed-by </section>
def-tag <button> closed-by </button>
def-tag <ul> closed-by </ul>
def-tag <li> closed-by </li>
def-tag <a> closed-by </a>
def-tag <span> closed-by </span>
def-tag <p> closed-by </p>
def-tag <div> closed-by </div>
def-tag <label> closed-by </label>
def-tag <input> closed-by </input>
def-tag <header> closed-by </header>
def-tag <h1> closed-by </h1>
def-tag <strong> closed-by </strong>

def-attr =class
def-attr =id
def-attr =for
def-attr =placeholder
def-attr =type
def-attr =checked
def-attr =value
def-attr =href

( virtual attrs )
def-attr =input-value
def-attr =focus

def-event =onclick
def-event =oninput
def-event =onchange
def-event =onkeydown
def-event =onmouseenter
def-event =onmouseleave
def-event =ondblclick
def-event =onblur
def-event =onfocus

0 QUIET !
