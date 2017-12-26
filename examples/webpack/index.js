import * as WasmForth from 'wasm-forth';
import wasmURL from 'wasm-forth/dist/kernel.wasm';
import coreURL from 'wasm-forth/dist/core.f';

WasmForth.boot({
    wasmURL,
    coreURL,
    write: (text) => {
        document.getElementById('content').textContent += text;
    }
}).then(() => {
    WasmForth.source(': HELLO S" Hello, World!" TYPE ; HELLO');
});
