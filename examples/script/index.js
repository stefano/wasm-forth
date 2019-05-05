WasmForth.boot({
    wasmURL: 'node_modules/wasm-forth/dist/kernel.wasm',
    sources: ['node_modules/wasm-forth/dist/core.f', 'node_modules/wasm-forth/dist/vdom.f'],
    write: (text) => {
        document.getElementById('content').textContent += text;
    }
}).then(() => {
    WasmForth.source(': HELLO S" Hello, World!" TYPE ; HELLO\n');
});
