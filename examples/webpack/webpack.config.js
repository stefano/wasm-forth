let path = require('path');

module.exports = {
    entry: {
        main: './index.js'
    },
    output: {
        path: path.resolve(__dirname, 'dist'),
        filename: 'index.js',
        publicPath: 'dist/'
    },
    module: {
        rules: [
            {
                test   : /\.(f|wasm)$/,
                loader : 'file-loader'
            }
        ]
    }
};
