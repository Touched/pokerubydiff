import { RECEIVE_MESSAGE } from './constants';

export function receiveMessage(event, data) {
  return {
    type: RECEIVE_MESSAGE,
    event,
    data,
  };
}
