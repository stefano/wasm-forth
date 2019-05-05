1 QUIET !

: IMMEDIATE 1 LATEST @ 1- C! ;

: ( SOURCE >IN @ /STRING 41 SCAN DROP CHAR+ SOURCE DROP - >IN ! ; IMMEDIATE

: CELLS ( n1 -- n2 )
  0 CELL+ * ;

: NFA>CFA ( c-addr1 -- c-addr2 )
  ( 127 AND to unsmudge the length in case the definition is hidden )
  DUP C@ 127 AND + 1+ ALIGNED ;

: DOES> ( R: ret -- )
  R> LATEST @ NFA>CFA ! ;

: CREATE ( "<spaces>name" -- )
  HEADER lit (dovar) @ , ;

: VARIABLE ( "<spaces>name" -- )
  CREATE 0 CELL+ ALLOT ;

: CONSTANT ( x "<spaces>name" -- )
  HEADER lit (doconst) @ , , ;

: EMBED-STR ( "ccc<quote>" -- )
  SOURCE >IN @ /STRING OVER >R 34 SCAN DROP
  R@ -
  DUP CHAR+ >IN +!
  DUP ,
  R> HERE ROT DUP >R CMOVE
  R> ALIGNED ALLOT ;

: GET-EMBEDDED-STR ( -- a-addr u )
  R> DUP DUP @ + ALIGNED CELL+ >R ( skip the characters when executing )
  DUP CELL+ SWAP @ ;

: S" ( "ccc<quote>" -- )
  lit GET-EMBEDDED-STR , EMBED-STR ; IMMEDIATE

: ." ( "ccc<quote>" -- )
  lit GET-EMBEDDED-STR , EMBED-STR lit WRITE , ; IMMEDIATE

: IF ( compilation: C: -- orig, runtime: x -- )
  lit ?branch , HERE 0 , ( placeholder, filled in by THEN/ELSE )
  ; IMMEDIATE

: PATCH-IF ( orig -- )
  HERE OVER - SWAP !
  ;

: ELSE ( compilation: C: orig1 -- orig2, runtime: -- )
  lit branch , HERE 0 , SWAP PATCH-IF
  ; IMMEDIATE

: THEN ( compilation: C: orig --, runtime: -- )
  PATCH-IF
  ; IMMEDIATE

: ' ( "<spaces>name" -- xt )
  BL WORD FIND 0= IF ." word to compile not found: " COUNT WRITE ABORT THEN
  ;

: ['] ( compilation: "<spaces>name" --, runtime: -- xt )
  lit lit , ' , ; IMMEDIATE

: POSTPONE ( compilation: "<spaces>name" -- )
  BL WORD FIND DUP
  0= IF ." word to postpone not found: " OVER COUNT WRITE ABORT THEN
  SWAP lit lit , ,
  1 = IF ['] EXECUTE , ELSE ['] , , THEN ; IMMEDIATE

: DO ( compilation: C: -- loop-addr, runtime: n1|u1 n2|u2 -- R: -- loop-end-addr limit index )
  ['] (do) , 0 , ( will be patched by LOOP/+LOOP )
  HERE
  ; IMMEDIATE

: PATCH-DO ( do-sys -- )
  HERE SWAP 1 CELLS - ! ( patch the paren-do-paren introduced by DO )
  ;

: LOOP ( compilation: C: do-sys --, runtime: R: loop-sys1 -- | loop-sys2 )
  ['] (loop) , DUP HERE - ,
  PATCH-DO
  ; IMMEDIATE

: +LOOP ( compilation: C: do-sys --, runtime: n -- R: loop-sys1 -- | loop-sys2 )
  ['] (+loop) , DUP HERE - ,
  PATCH-DO
  ; IMMEDIATE

: BEGIN ( compilation: C: -- dest, runtime: -- )
  HERE
  ; IMMEDIATE

: UNTIL ( compilation: C: dest -- , runtime: x -- )
  ['] ?branch , HERE - ,
  ; IMMEDIATE

: WHILE ( compilation: C: dest -- orig dest, runtime: x -- )
  ['] ?branch , HERE SWAP 0 , ( placeholder, patched by REPEAT )
  ; IMMEDIATE

: REPEAT ( compilation: orig dest --, runtime: -- )
  ['] branch , HERE - ,
  HERE OVER - SWAP ! ( patch WHILE ?branch offset )
  ; IMMEDIATE

: AGAIN ( compilation: dest --, runtime: -- )
  ['] branch , HERE - , ; IMMEDIATE

: [ ( -- )
  0 STATE ! ; IMMEDIATE

: ] ( -- )
  1 STATE ! ;

: CHAR ( "<spaces>name" -- char )
  BL WORD 1+ C@ ;

: [CHAR] ( compilation: "<spaces>name" --, runtime: -- c )
  CHAR ['] lit , , ; IMMEDIATE

VARIABLE #SIZE
1024 CONSTANT #MAX-SIZE

: #NEXT-FREE-SPACE ( -- c-addr )
  HERE #MAX-SIZE + #SIZE @ - ;

: <# ( -- )
  0 #SIZE ! ;

: HOLD ( char -- )
  #NEXT-FREE-SPACE C! 1 #SIZE +! ;

: SIGN ( n -- )
  0 < IF [CHAR] - HOLD THEN ;

: # ( ud1 -- ud2 )
  BASE @ UD/MOD DUP 10 < IF 48 ELSE 65 THEN + HOLD ;

: #S ( ud1 -- ud2 )
  BEGIN # 2DUP 0= SWAP 0= AND UNTIL ;

: #> ( xd -- c-addr u )
  2DROP #NEXT-FREE-SPACE 1+ #SIZE @ ;

: */MOD ( n1 n2 n3 -- n4 n5 )
  >R M* R> SM/REM ;

: */ ( n1 n2 n3 -- n4 )
  */MOD SWAP DROP ;

: FM/MOD ( d1 n1 -- n2 n3 )
  ( note: the sign is in the high cell )
  2DUP 0 < SWAP 0 < XOR IF DUP >R SM/REM 1- SWAP R> + SWAP ELSE SM/REM THEN ;

: ABS ( n -- u )
  DUP 0 < IF 0 SWAP - THEN ;

: TYPE ( c-addr u -- )
  WRITE ;

: . ( n -- )
  DUP ABS S>D <# BL HOLD #S ROT SIGN #> TYPE ;

: U. ( u -- )
  0 <# BL HOLD #S #> TYPE ;

: 2! ( x1 x2 a-addr -- )
  SWAP OVER ! CELL+ ! ;

: 2@ ( a-addr -- x1 x2 )
  DUP CELL+ @ SWAP @ ;

: >BODY ( xt -- a-addr )
  CELL+ ;

: (ABORT") ( i*x x1 c-addr u -- | i*x R: j*x -- | j*x )
  ROT IF TYPE ABORT ELSE 2DROP THEN ;

: ABORT" ( compilation: "ccc<quote>" --, runtime: i*x x1 -- | i*x R: j*x -- | j*x )
  ['] GET-EMBEDDED-STR , EMBED-STR ['] (ABORT") , ; IMMEDIATE

: ALIGN ( -- )
  HERE ALIGNED HERE - ALLOT ;

: CHARS ( n1 -- n2 ) ;

: EMIT ( x -- )
  PAD C! PAD 1 TYPE ;

: CR ( -- )
  10 EMIT ;

: S= ( c-addr1 u1 c-addr2 u2 -- flag )
  ROT 2DUP =
    IF
      DROP
      0 DO 2DUP I + C@ SWAP I + C@ = INVERT IF UNLOOP 2DROP 0 EXIT THEN LOOP
      2DROP 0 1-
    ELSE
      2DROP 2DROP 0
    THEN
  ;

: TRUE ( -- true )
  0 1- ;

: ENVIRONMENT? ( c-addr u -- false | i*x true )
  2DUP S" /COUNTED-STRING" S= IF 2DROP 127 TRUE EXIT THEN
  2DUP S" /HOLD" S= IF 2DROP #MAX-SIZE TRUE EXIT THEN
  2DUP S" /PAD" S= IF 2DROP 4096 TRUE EXIT THEN
  2DUP S" ADDRESS-UNIT-BITS" S= IF 2DROP 8 TRUE EXIT THEN
  2DUP S" CORE" S= IF 2DROP TRUE TRUE EXIT THEN
  2DUP S" CORE-EXT" S= IF 2DROP 0 TRUE EXIT THEN
  2DUP S" FLOORED" S= IF 2DROP 0 TRUE EXIT THEN
  2DUP S" MAX-CHAR" S= IF 2DROP TRUE TRUE EXIT THEN
  2DUP S" MAX-D" S= IF 2DROP 0 INVERT DUP 1 RSHIFT TRUE EXIT THEN
  2DUP S" MAX-N" S= IF 2DROP 1 31 LSHIFT 1- TRUE EXIT THEN
  2DUP S" MAX-U" S= IF 2DROP 0 INVERT TRUE EXIT THEN
  2DUP S" MAX-UD" S= IF 2DROP 0 INVERT DUP TRUE EXIT THEN
  2DUP S" RETURN-STACK-CELLS" S= IF 2DROP 1024 TRUE EXIT THEN
  2DUP S" STACK-CELLS" S= IF 2DROP 1024 TRUE EXIT THEN
  2DROP 0
  ;

: EVALUATE ( i*x c-addr u -- j*x )
  SOURCE-ID @ >R
  IN-BUF @ >R
  IN-BUF-EOL @ >R
  IN-BUF-SIZE @ >R
  >IN @ >R

  -1 SOURCE-ID !
  0 >IN !
  IN-BUF-EOL !
  IN-BUF !

  INTERPRET

  R> >IN !
  R> IN-BUF-SIZE !
  R> IN-BUF-EOL !
  R> IN-BUF !
  R> SOURCE-ID ! ;

: KEY ( -- char )
  >IN @ IN-BUF-EOL @ > IF LINE 2DROP 0 >IN ! THEN
  IN-BUF @ >IN @ + C@ 1 >IN +! ;

: LITERAL ( compilation: x --, runtime: -- x )
  ['] lit , , ; IMMEDIATE

: MAX ( n1 n2 -- n3 )
  2DUP < IF SWAP THEN DROP ;

: MIN ( n1 n2 -- n3 )
  2DUP > IF SWAP THEN DROP ;

: MOD ( n1 n2 -- n3 )
  /MOD DROP ;

: MOVE ( addr1 addr2 u -- )
  >R 2DUP < IF R> CMOVE> ELSE R> CMOVE THEN ;

: RECURSE ( compilation: -- )
  LATEST @ NFA>CFA , ; IMMEDIATE

: SPACE ( -- )
  BL EMIT ;

: SPACES ( n -- )
  0 SWAP DO SPACE LOOP ;

: >= ( n1 n2 -- flag )
  < INVERT ;

: ACCEPT ( c-addr +n1 -- +n2 )
  >IN @ IN-BUF-EOL @ >= IF LINE 2DROP 0 >IN ! THEN
  IN-BUF-EOL @ >IN @ - MIN >R ( c-addr R: n2 )
  IN-BUF @ >IN @ + SWAP R@ MOVE
  R@ >IN +!
  R> ;

: ?DUP ( x -- 0 | x x )
  DUP 0= IF DUP THEN ;

: FILL ( c-addr u c -- )
  ROT ROT 0 DO 2DUP I + C! LOOP 2DROP ;

( core extension words )

( NOTE: #TIB, .(, .R, :NONAME, ?DO, C" not implemented )

: 0<> ( x -- flag )
  0= INVERT ;

: 0> ( x -- flag )
  0 > ;

: 2>R ( x1 x2 -- R: -- x1 x2 )
  R> ROT >R SWAP >R >R ;

: 2R> ( -- x1 x2 R: x1 x2 -- )
  R> R> R> SWAP ROT >R ;

: 2R@ ( -- x1 x2 R: x1 x2 -- x1 x2 )
  R> R> R> 2DUP >R >R ROT >R SWAP ;

: <> ( x1 x2 - flag )
  = INVERT ;

( non-standard utilities )

: SP0 ( -- addr ) 10 1024 * CELL+ task-base + ;
: sl ( -- n ) SP@ CELL+ SP0 SWAP - 0 CELL+ /MOD SWAP DROP ;
: .NOSPACE ( n -- ) DUP ABS S>D <# #S ROT SIGN #> TYPE ;
: .sl ( -- ) S" <" TYPE sl .NOSPACE S" > " TYPE ;
: PEEK ( u -- x ) 1+ CELLS SP0 SWAP - @ ;
: .sitem ( u -- ) PEEK . ;
: .s ( -- ) .sl sl 0 > IF sl 0 DO I .sitem LOOP THEN ;

( setup cooperative multi tasking )

11 1024 * CONSTANT task-size
5 1024 * CELL+ CONSTANT task-rs-offset
3 CELLS CONSTANT task-ip-initial-offset
0 CONSTANT ip-mem-offset

VARIABLE task-free-block 0 task-free-block !

: find-free-block ( -- addr flag )
  task-free-block @ DUP 0= IF 0 EXIT THEN
  DUP @ task-free-block ! 1 ;
: create-block ( -- addr ) HERE task-size ALLOT ;
: alloc-block ( -- addr ) find-free-block 0= IF DROP create-block THEN ;
: release-block ( addr -- ) task-free-block @ OVER ! task-free-block ! ;

: end-task ( -- ) task-base release-block BYE ;
: new-task ( xt -- )
  alloc-block task-base!
  >R RESET-SP R>
  task-base task-rs-offset + RP!
  EXECUTE end-task ;
: start-task ( -- ) task-param new-task ;

: ready ( -- ) ." Ready" CR 0 QUIET ! RESET-SP 0 (QUIT) ;
: setup-tasks ( -- )
  ( must be within word definition, or an async FFI call from the interpreter will mess it up )
  task-base task-ip-initial-offset + task-base ip-mem-offset + !
  ( start-task is the new main task )
  ['] start-task task-base task-ip-initial-offset + !
  ( run interpreter in new task )
  ['] ready new-task ;

: (abort-task") ( c-str u -- ) TYPE end-task ;
: abort-task" ( compilation: "<ccc>quote" --, runtime: -- )
  ['] GET-EMBEDDED-STR , EMBED-STR ['] (abort-task") , ; IMMEDIATE

setup-tasks ( must be last, since it calls ABORT which empties the I/O buffers )
