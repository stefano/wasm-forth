let interpreter;
let memBytes;
let memCells;
let inputBuffer = '';
let onSourceAvailable;

function decodeString(memoryIndex, nBytes) {
  let chars = [];

  for (let i = 0; i < nBytes; i++) {
    chars.push(String.fromCharCode(memBytes[memoryIndex + i]));
  }

  return chars.join('');
}

function encodeString(target, value, limit) {
    limit = Math.min(limit, value.length);
    for (let i = 0; i < limit; i++) {
        memBytes[target + i] = value.charCodeAt(i);
    }
    return limit;
}

function makeFFI(config) {
    let currentEvent = null;

    let io = {
        read: (token, memoryIndex, nBytes) => {
            let continuation = () => {
                let limit = encodeString(memoryIndex, inputBuffer, nBytes);
                inputBuffer = inputBuffer.substr(limit);
                onSourceAvailable = undefined;
                interpreter.exports.exec(token, limit);
            };

            if (inputBuffer.length > 0) {
                setTimeout(continuation, 0);
            } else {
                onSourceAvailable = continuation;
            }
        },

        patchBody: (memoryIndex, unused) => {
            let parent = document.querySelector('#body'), nodeIdx = 0;
            let parentStack = [], idxStack = [];
            loop:
            for (let idx = memoryIndex / 4;; idx += 2) {
                switch (memCells[idx]) {
                case 1: {
                    // remove attr
                    let structAddr = memCells[idx+1];
                    let nameAddr = memCells[structAddr/4];
                    let name = decodeString(nameAddr+2, memBytes[nameAddr]-1);
                    let valueNBytes = memCells[structAddr/4+1];
                    if (valueNBytes === 0xFFFFFFFF) {
                        parent.childNodes[nodeIdx][name] = undefined;
                    } else if (name === 'focus') {
                        // nothing
                    } else if (name === 'input-value') {
                        parent.childNodes[nodeIdx].value = '';
                    } else if (name === 'checked') {
                        parent.childNodes[nodeIdx].checked = false;
                    } else {
                        parent.childNodes[nodeIdx].removeAttribute(name);
                    }
                    break;
                }
                case 2: {
                    // set attr
                    let structAddr = memCells[idx+1];
                    let nameAddr = memCells[structAddr/4];
                    let name = decodeString(nameAddr+2, memBytes[nameAddr]-1);
                    let valueNBytes = memCells[structAddr/4+1];
                    let valueAddr = memCells[structAddr/4+2];
                    if (valueNBytes === 0xFFFFFFFF) {
                        parent.childNodes[nodeIdx][name] = (evt) => {
                            currentEvent = evt;
                            interpreter.exports.exec(0, valueAddr);
                        };
                    } else if (name === 'focus') {
                        parent.childNodes[nodeIdx].focus();
                    } else if (name === 'input-value') {
                        parent.childNodes[nodeIdx].value = decodeString(valueAddr, valueNBytes);
                    } else if (name === 'checked') {
                        parent.childNodes[nodeIdx].checked = true;
                    } else {
                        parent.childNodes[nodeIdx].setAttribute(name, decodeString(valueAddr, valueNBytes));
                    }
                    break;
                }
                case 3: // create
                    let addr = memCells[idx+1];
                    let nBytes = memBytes[addr];
                    let name = decodeString(addr+2, nBytes-2); // skip starting '<' and ending '>'
                    let elem = document.createElement(name);
                    parent.insertBefore(elem, parent.childNodes[nodeIdx]);
                    break;
                case 4: // skip
                    nodeIdx += memCells[idx+1];
                    break;
                case 5: // remove
                    parent.removeChild(parent.childNodes[nodeIdx]);
                    break;
                case 6: // enter
                    parentStack.push(parent);
                    idxStack.push(nodeIdx);
                    parent = parent.childNodes[nodeIdx];
                    nodeIdx = 0;
                    break;
                case 7: // leave
                    parent = parentStack.pop();
                    nodeIdx = idxStack.pop();
                    break;
                case 8: // stop
                    break loop;
                case 9: // create text node
                    parent.insertBefore(document.createTextNode(''), parent.childNodes[nodeIdx]);
                    break;
                case 10: // set text content
                    let textNBytes = memCells[memCells[idx+1]/4+1];
                    let textAddr = memCells[memCells[idx+1]/4+2];
                    parent.childNodes[nodeIdx].textContent = decodeString(textAddr, textNBytes);
                    break;
                default:
                    console.log('unknown opcode:' + memCells[idx]);
                    break loop;
                }
            }
        },

        write: (memoryIndex, nBytes) => {
            try {
                config.write(decodeString(memoryIndex, nBytes));
            } catch (e) {
                console.error(e);
            }
        },

        evtAttr: (memoryIndex, nBytes, targetAddr, limit) => {
            let path = decodeString(memoryIndex, nBytes).split('.');
            let value = currentEvent;
            for (let item of path) {
                value = value[item];
            }
            if (value === true || value === false) {
                return value;
            }
            if (typeof value === 'number') {
                return value;
            }
            return encodeString(targetAddr, value, limit);
        }
    };

    return { io };
}

/**
 * Provide Forth source code to be executed.
 *
 * @param {string} text
 */
export function source(text) {
    inputBuffer += text;

    if (onSourceAvailable) {
        onSourceAvailable();
    }
}

/**
 * Boots the forth system.
 *
 * @param config
 * {
 *     wasm: string; // URL to dist/kernel.wasm
 *     sources: string[]; // URLs to forth source code (should at least include dist/core.f)
 *     write: (text) => void; // a function called with the output emitted by Forth code
 * }
 *
 * @returns {Promise} resolved when the system is ready to process forth code.
 */
export function boot(config) {
    return fetch(config.wasmURL).then(
        res => res.arrayBuffer()
    ).then(
        bytes => WebAssembly.instantiate(bytes, makeFFI(config))
    ).then(compiled => {
        interpreter = compiled.instance;
        memBytes = new Uint8Array(interpreter.exports.mem.buffer);
        memCells = new Uint32Array(interpreter.exports.mem.buffer);
        window.memBytes = memBytes;
        window.memCells = memCells;

        interpreter.exports.exec(0, 0);
    }).then(
        () => Promise.all(config.sources.map(url => fetch(url)))
    ).then(
        results => Promise.all(results.map(res => res.text()))
    ).then(
        texts => texts.forEach(source)
    );
}
