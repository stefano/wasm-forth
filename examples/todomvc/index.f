1 QUIET !

VARIABLE first-render TRUE first-render !

( each todo has: 4 byte length [excluding flags], 1 byte completed flag, 1 byte editing flag, 1 byte show remove button 1 byte focus editing, string content )
1 MB buffer todos

1025 buffer todo-temp 0 todo-temp !
1025 buffer item-temp 0 item-temp !

: completed ( addr -- flag ) CELL+ C@ ;
: set-completed ( flag addr -- ) CELL+ C! ;

: editing ( addr -- flag ) CELL+ 1+ C@ ;
: set-editing ( flag addr -- ) CELL+ 1+ C! ;

: show-remove ( addr -- flag ) CELL+ 2 + C@ ;
: set-show-remove ( flag addr -- ) CELL+ 2 + C! ;

: focus ( addr -- flag ) CELL+ 3 + C@ ;
: set-focus ( flag addr -- ) CELL+ 3 + C! ;

: text-addr ( addr -- addr1 ) 2 CELLS + ;
: todo-text ( addr -- addr1 u ) text-addr & @ ;
: todo-text-len @ ;

: bytes-to-end ( addr -- n ) todos buf-next @ SWAP - ;
: eof-todo ( addr -- addr1 ) todo-text + ;
: no-space-to-replace? ( u addr -- flag )
  DUP eof-todo bytes-to-end + + 2 CELLS + todos buf-end > ;
: set-todo-text ( c-addr u addr -- )
  2DUP no-space-to-replace? IF abort-task" no space left to set todo text" THEN
  2DUP + 2 CELLS + >R
  DUP eof-todo DUP bytes-to-end R> 2DUP + >R SWAP MOVE ( make space )
  R> todos buf-next !
  2DUP ! ( set text length )
  2 CELLS + SWAP MOVE ; ( copy text )
: add-empty-todo ( -- addr ) todos buf-next @ 0 todos ,buf 0 todos ,buf ;
: remove-todo ( addr -- )
  DUP eof-todo SWAP OVER bytes-to-end 2DUP + >R MOVE
  R> todos buf-next ! ;
: next-todo-offset ( addr1 -- u ) @ 2 CELLS + ;
: next-todo ( addr -- addr1 ) DUP next-todo-offset + ;
: remove-completed ( -- )
  todos BEGIN DUP todos buf-next @ < WHILE DUP completed IF DUP remove-todo ELSE next-todo THEN REPEAT DROP ;
: each-todo ( xt -- )
  todos buf-next @ todos = IF DROP EXIT THEN
  todos buf-next @ todos DO I SWAP DUP >R EXECUTE R> I next-todo-offset +LOOP DROP ;
: inc-count ( n addr -- n2 ) DROP 1+ ;
: count-todos ( -- u )
  0 ['] inc-count each-todo ;
: inc-completed ( n addr -- n2 ) completed IF 1+ THEN ;
: count-completed ( -- u ) 0 ['] inc-completed each-todo ;
: inc-not-completed ( n addr -- n2 ) completed 0= IF 1+ THEN ;
: count-left ( -- u ) 0 ['] inc-not-completed each-todo ;

: .todo ( addr -- ) todo-text TYPE ;
: .todos ( -- ) ['] .todo each-todo ;

: is-checked ( flag1 addr -- flag2 ) completed AND ;
: toggle-all-state ( -- flag )
  TRUE ['] is-checked each-todo ;

: checked ( -- flag ) S" target.checked" 0 0 EVT-ATTR ;
: key-code ( -- x ) S" keyCode" 0 0 EVT-ATTR ;

: clear-completed ( -- ) remove-completed repaint ;

: temp-str ( addr -- c-addr u ) CELL+ & @ ;

: save-todo-temp ( -- ) S" target.value" todo-temp CELL+ 1024 EVT-ATTR todo-temp ! ;
: reset-todo-temp ( -- ) 0 todo-temp ! ;
: todo-tmp-str ( -- c-addr u ) todo-temp temp-str ;

: set-item-temp ( addr -- ) todo-text TUCK item-temp CELL+ SWAP CMOVE item-temp ! ;
: item-tmp-str ( -- c-addr u ) item-temp temp-str ;

: on-todo-input ( -- ) save-todo-temp ;
: on-todo-action ( -- )
  key-code 13 = IF todo-tmp-str trim DUP 0= IF 2DROP EXIT THEN add-empty-todo set-todo-text reset-todo-temp THEN repaint ;
: set-completed' ( flag addr -- flag ) OVER /top set-completed ;
: on-toggle-all ( -- )
  checked ['] set-completed' each-todo DROP
  repaint ;
: on-item-checked ( data -- ) checked SWAP set-completed repaint ;
: on-todo-item-enter ( addr -- ) TRUE SWAP set-show-remove repaint ;
: on-todo-item-leave ( addr -- ) 0 SWAP set-show-remove repaint ;
: on-item-start-editing ( addr -- )
  DUP set-item-temp
  TRUE OVER set-editing
  TRUE OVER set-focus
  repaint
  0 SWAP set-focus
  repaint ;
: on-remove-todo ( addr -- ) remove-todo repaint ;
: trim-item ( addr -- )
  DUP todo-text trim ROT set-todo-text ;
: on-item-blur ( addr -- )
  DUP trim-item DUP todo-text-len 0= IF remove-todo ELSE 0 SWAP set-editing THEN repaint ;

: on-item-input ( addr -- )
  HERE S" target.value" HERE 1024 EVT-ATTR ROT set-todo-text repaint ;
: on-item-action ( addr -- )
  key-code 13 = IF on-item-blur EXIT THEN
  key-code 27 = IF item-tmp-str ROT set-todo-text repaint EXIT THEN ( reset from temp )
  DROP ;

: todo-header ( -- )
  <header> S" header" =class
   <h1> S" todos" text </h1>
   <input>
     S" new-todo" =class
     S" What needs to be done?" =placeholder
     first-render @ IF empty-attr =focus THEN
     ['] on-todo-input =oninput
     ['] on-todo-action =onkeydown
     todo-tmp-str to-rbuf =input-value
   </input>
  </header> ;

: todo-item ( addr -- )
  >R
  <li>
       R@ bind on-todo-item-enter =onmouseenter
       R@ bind on-todo-item-leave =onmouseleave
       R@ editing IF R@ completed IF S" completed editing" ELSE S" editing" THEN
                  ELSE R@ completed IF S" completed" ELSE S" " THEN
                  THEN =class
    <div> S" view" =class
      <input>
        S" toggle" =class
        S" checkbox" =type
        R@ completed IF empty-attr =checked THEN
        R@ bind on-item-checked =onchange
      </input>
      <label> R@ bind on-item-start-editing =ondblclick
        R@ todo-text to-rbuf text
      </label>
      R@ show-remove IF <button> S" destroy" =class R@ bind on-remove-todo =onclick </button> THEN
    </div>
    <input>
      S" edit" =class
      R@ todo-text to-rbuf =input-value
      R@ focus IF empty-attr =focus THEN
      R@ bind on-item-blur =onblur
      R@ bind on-item-start-editing =onfocus
      R@ bind on-item-input =oninput
      R@ bind on-item-action =onkeydown
    </input>
  </li>
  R> DROP ;

: render-todos ( -- )
  count-todos 0= IF EXIT THEN
  <section> S" main" =class
    <input>
      S" toggle-all" =id
      S" toggle-all" =class
      S" checkbox" =type
      toggle-all-state IF S" checked" =checked THEN
      ['] on-toggle-all =onchange
    </input>
    <label> S" toggle-all" =for S" Mark all as complete" text </label>
    <ul> S" todo-list" =class
        ['] todo-item each-todo
    </ul>
  </section> ;

: items-left ( n-left -- )
  >R
  <span>
    <strong> R@ fmt-int text </strong> S"  " text
    R> 1 = IF S" item left" ELSE S" items left" THEN text
  </span> ;
: clear-completed-btn ( -- )
  <button> S" clear-completed" =class ['] clear-completed =onclick
    S" Clear completed" text
  </button> ;
: todo-footer ( n-completed n-left -- )
  count-todos 0= IF 2DROP EXIT THEN
  2>R
  <footer> S" footer" =class
    R> items-left
    R> 0 > IF clear-completed-btn THEN
  </footer> ;

: todo-app ( -- )
  <section> S" todoapp" =class
    todo-header
    render-todos
    count-completed count-left todo-footer
  </section> ;

: footer-info ( -- )
  <footer> S" info" =class
    <p> S" Double click to edit a todo" text </p>
    <p> S" Part of " text <a> S" https://github.com/stefano/wasm-forth" =href S" wasm-forth" text </a> </p>
  </footer> ;

: app <div> todo-app footer-info </div> 0 first-render ! ;

repaint-with app
repaint

0 QUIET !
