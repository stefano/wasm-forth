let path = require('path');

let wasmForth = {
    entry: {
        main: './src/index.js'
    },
    output: {
        path: path.resolve(__dirname, 'npm_dist'),
        filename: 'wasm-forth.js',
        library: 'WasmForth'
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
