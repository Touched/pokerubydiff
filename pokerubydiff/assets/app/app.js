import React from 'react';
import ReactDOM from 'react-dom';
import io from 'socket.io-client';

import './styles/main.scss';

var socket = io.connect('http://' + document.domain + ':' + location.port);
socket.on('connect', console.log);
socket.on('event', console.log);

ReactDOM.render(
  <h1>Hello, World from WebPack!</h1>,
  document.getElementById('app')
)
