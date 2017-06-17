const path = require('path');
const webpack = require('webpack');
const ExtractTextPlugin = require('extract-text-webpack-plugin');
const HtmlWebpackPlugin = require('html-webpack-plugin');

const root = './assets'

module.exports = {
  entry: {
    app: [
      path.join(__dirname, 'pokerubydiff/assets/app/app.js'),
    ],
  },
  output: {
    path: path.join(__dirname, 'pokerubydiff/public'),
    publicPath: '/assets/',
    filename: '[name].[chunkhash].js',
    chunkFilename: '[id].[chunkhash].chunk',
  },
  resolve: {
    extensions: ['.js', '.scss'],
  },
  module: {
    loaders: [
      {
        test: /\.js$/,
        exclude: /node_modules/,
        loader: 'babel-loader',
      },
      {
        test: /\.scss$/i,
        loader: ExtractTextPlugin.extract(['css-loader', 'sass-loader']),
      },
    ],
  },
  plugins: [
    new ExtractTextPlugin('[name].[chunkhash].css'),
    new webpack.optimize.UglifyJsPlugin(),
    new webpack.DefinePlugin({
      'process.env': {
        NODE_ENV: '"production"'
      }
    }),
    new webpack.NoEmitOnErrorsPlugin(),
    new HtmlWebpackPlugin({
      title: 'pokerubydiff',
      template: path.join(__dirname, 'pokerubydiff/assets/index.ejs'),
    }),
  ],
}
