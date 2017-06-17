import React from 'react';
import ReactDOM from 'react-dom';

import './styles/main.scss';

const socket = new WebSocket(`ws://${document.domain}:${location.port}/socket`);

socket.addEventListener('open', function (event) {
  console.log('Connected')
});

socket.addEventListener('message', function (event) {
  console.log('Message from server', event.data);
});

ReactDOM.render(
  <h1>Hello, World from WebPack!</h1>,
  document.getElementById('app')
)
