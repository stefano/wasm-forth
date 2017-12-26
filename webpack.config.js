let path = require('path');

let wasmForth = {
    entry: {
        main: './src/index.js'
    },
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'wasm-forth.js',
        library: 'WasmForth',
        libraryTarget: 'umd'
    }
};

let repl = {
    entry: {
        main: './repl/repl.js'
    },
    output: {
        path: path.resolve(__dirname, 'repl/dist'),
        filename: 'repl.js'
    }
};

module.exports = [wasmForth, repl];
