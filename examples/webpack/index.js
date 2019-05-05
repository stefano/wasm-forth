import * as WasmForth from 'wasm-forth';
import wasmURL from 'wasm-forth/dist/kernel.wasm';
import coreURL from 'wasm-forth/dist/core.f';
import vdomURL from 'wasm-forth/dist/vdom.f';

WasmForth.boot({
    wasmURL,
    sources: [coreURL, vdomURL],
    write: (text) => {
        document.getElementById('content').textContent += text;
    }
}).then(() => {
    WasmForth.source(': HELLO S" Hello, World!" TYPE ; HELLO\n');
});
