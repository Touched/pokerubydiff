import { RECEIVE_MESSAGE } from '../constants';

const initialState = {
  diff: [],
  building: false,
};

function handleMessage(state, event, data) {
  switch (event) {
    case 'buildling':
      return {
        ...state,
        building: true,
      };
    case 'diff':
      return {
        ...state,
        diff: data,
        building: false,
      };
    default:
      return state;
  }
}

export default function messages(state = initialState, action) {
  switch (action.type) {
    case RECEIVE_MESSAGE:
      return handleMessage(state, action.event, action.data);
    default:
      return state;
  }
}
