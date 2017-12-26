import * as WasmForth from '../src/index';

let loadingElement = document.getElementById('loading');
let content = document.getElementById('content');
let sourceInputElement = document.getElementById('source-input');
let enterElement = document.getElementById('enter');
let outputElement = document.getElementById('output');

function onInputLine(evt) {
    if (evt.keyCode === 13) {
        processLine();
    }
}

function processLine() {
    let line = sourceInputElement.value;

    outputElement.innerText += line + ' ';
    sourceInputElement.value = '';

    WasmForth.source(line + '\n');

    sourceInputElement.focus();
}

WasmForth.boot({
    wasmURL: 'dist/kernel.wasm',
    coreURL: 'dist/core.f',
    write: (text) => {
        outputElement.innerText += text;
    }
}).then(() => {
    sourceInputElement.addEventListener('keypress', onInputLine);
    enterElement.addEventListener('click', processLine);

    loadingElement.parentElement.removeChild(loadingElement);
    content.style.display = 'block';
    sourceInputElement.focus();
});
