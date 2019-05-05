WASM Forth
==========

A Forth implementation compiling to WebAssembly.

It includes an ANS Forth standard environment containing all the CORE words.
The system has a fixed amount of memory available, currently 128 MB.

Interaction with Javascript at the moment is limited to textual input (using `WasmForth.source`)
and output (through the `write` configuration parameter passed to `WasmForth.boot`).

Using the included (optional) virtual DOM library it's possible to
write interactive web apps. See the code in `examples/todomvc/` for an
example TODO list web app fully implemented in Forth.

Installation
============

    $ npm install wasm-forth

Usage
=====

The following code instantiates the interpreter and runs a program that prints "Hello, World!" to the console:

    import * as WasmForth from 'wasm-forth';
    import wasmURL from 'wasm-forth/dist/kernel.wasm';
    import coreURL from 'wasm-forth/dist/core.f';
    import vdomURL from 'wasm-forth/dist/vdom.f';

    WasmForth.boot({
        wasmURL,
        sources: [coreURL, vdomURL],
        write: (text) => {
            console.log(text);
        }
    }).then(() => {
        WasmForth.source(': HELLO S" Hello, World!" TYPE ; HELLO');
    });

`WasmForth.boot({ ... })` initializes the system and returns a Promise. Once resolved, it's possible to
interpret forth code by passing it to `WasmForth.source(string)`. Note that the string passed must end with a newline.

`WasmForth.boot` accepts a configuration object with 3 required parameters:

- `wasmURL`: URL where to fetch the "kernel.wasm" included in the NPM package.
- `sources`: a list of URLs where to fetch the forth "core.f" included in the NPM package.
- `write`: a function that will be called when the forth code needs to output text.

If you're using webpack, you can use the file-loader (https://github.com/webpack-contrib/file-loader)
plugin to distribute `kernel.wasm`, `core.f` and `vdom.f`.

You can also use this library without a module bundler by loading it in a <script> tag.

See https://github.com/stefano/wasm-forth/tree/master/examples/webpack for an example usage with webpack,
and https://github.com/stefano/wasm-forth/tree/master/examples/script for an example usage as a <script> tag.

See https://github.com/stefano/wasm-forth/tree/master/examples/todomvc for an example of a full web app that interacts with the DOM.

Building from source
====================

To build the forth kernel distribution and the interactive environment (see below), you will
first need to install binaryen (https://github.com/WebAssembly/binaryen)
and ensure that `libbinaryen.so` is in the library path (LD_LIBRARY_PATH).

Then build the kernel (Python 3.6 is required):

    $ python3.6 -m venv env
    $ source env/bin/activate
    $ python setup.py build_ext -L path/to/binaryen/lib/
    $ python setup.py develop
    $ python kernel
    $ npm install
    $ npm run build # or 'npm run watch'

Interactive Environment
=======================

This repository also contains a REPL static page (see the `repl` directory).
To serve it locally, follow the instructions above and then run the following command:

    $ python kernel --demo-repl

The REPL will be served at http://localhost:8080/
