import React from 'react';
import ReactDOM from 'react-dom';
import { Provider } from 'react-redux';
import thunk from 'redux-thunk';
import { createStore, combineReducers, applyMiddleware, compose } from 'redux';

import App from './containers/App';
import { receiveMessage } from './actions';
import * as reducers from './reducers';
import './styles/main.scss';

const PORT = process.env.NODE_ENV === 'production' ? location.port : '8080';

const reducer = combineReducers(reducers);

function configureStore() {
  const finalCreateStore = compose(
    applyMiddleware(thunk),
  )(createStore);
  const store = finalCreateStore(reducer);

  if (module.hot) {
    module.hot.accept('./reducers/', () => {
      const nextRootReducer = require('./reducers/index.js');
      store.replaceReducer(nextRootReducer);
    });
  }

  return store;
}

const store = configureStore();

ReactDOM.render(
  <Provider store={store}>
    <App />
  </Provider>,
  document.getElementById('app'),
);

const socket = new WebSocket(`ws://${document.domain}:${PORT}/socket`);

socket.addEventListener('message', function (message) {
  const { type, data } = JSON.parse(message.data);
  store.dispatch(receiveMessage(type, data));
});
