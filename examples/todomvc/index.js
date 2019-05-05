WasmForth.boot({
    wasmURL: 'node_modules/wasm-forth/dist/kernel.wasm',
    sources: ['node_modules/wasm-forth/dist/core.f', 'node_modules/wasm-forth/dist/vdom.f', 'index.f'],
    write: msg => console.log(msg)
});
