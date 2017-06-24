import { RECEIVE_MESSAGE } from '../constants';

const initialState = {
  diff: [],
  building: false,
  error: null,
  match: false,
};

function handleMessage(state, event, data) {
  switch (event) {
    case 'building':
      return {
        ...state,
        building: true,
        error: null,
        match: false,
      };
    case 'diff':
      return {
        ...state,
        diff: data,
        building: false,
      };
    case 'match':
      return {
        ...state,
        building: false,
        match: true,
      };
    case 'build_error':
      return {
        ...state,
        error: data,
        building: false,
      };
    default:
      console.log(event);
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
