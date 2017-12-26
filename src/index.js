let interpreter;
let memBytes;
let inputBuffer = '';
let onSourceAvailable;

function decodeString(memoryIndex, nBytes) {
  let chars = [];

  for (let i = 0; i < nBytes; i++) {
    chars.push(String.fromCharCode(memBytes[memoryIndex + i]));
  }

  return chars.join('');
}

function makeFFI(config) {
    let io = {
        read: (memoryIndex, nBytes) => {
            let continuation = () => {
                let limit = Math.min(nBytes, inputBuffer.length);
                for (let i = 0; i < limit; i++) {
                    memBytes[memoryIndex + i] = inputBuffer.charCodeAt(i);
                }
                inputBuffer = inputBuffer.substr(limit);
                onSourceAvailable = undefined;
                interpreter.exports.exec(1, limit);
            };

            if (inputBuffer.length > 0) {
                continuation();
            } else {
                onSourceAvailable = continuation;
            }
        },

        write: (memoryIndex, nBytes) => {
            try {
                config.write(decodeString(memoryIndex, nBytes));
            } finally {
                interpreter.exports.exec(1, nBytes);
            }
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
 *     wasmURL: string; // URL to npm_dist/kernel.wasm
 *     coreURL: string; // URL to npm_dist/core.f
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
        window.memBytes = memBytes;

        interpreter.exports.exec(0, 0);
    }).then(
        () => fetch(config.coreURL)
    ).then(
        res => res.text()
    ).then(source);
}
