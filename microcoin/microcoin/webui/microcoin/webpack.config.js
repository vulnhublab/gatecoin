// webpack.config.js
const webpack = require('webpack');
const path = require('path');

module.exports = {
  entry: {
    'microcoin': './dist/esm/index.js',
  },
  output: {
    path: path.resolve(__dirname, 'dist', 'umd'),
    filename: 'microcoin.js',
    library: 'microcoin',
    libraryTarget: 'umd'
  },
  module: {
    rules: [{
      test: /\.js$/,
      exclude: /ethjs-util/,
      use: [{
        loader: 'babel-loader',
        options: {
          presets: [
            ['env', { modules: false }]
          ]
        }
      }]
    }]
  }
};
