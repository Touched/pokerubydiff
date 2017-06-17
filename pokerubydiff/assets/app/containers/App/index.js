import React from 'react';
import { connect } from 'react-redux';

import Diff from '../../components/Diff';

function App({ diff }) {
  return (
    <div>
      <Diff diff={diff} />
    </div>
  );
}

const mapStateToProps = (state) => ({
  diff: state.messages.diff,
});

export default connect(mapStateToProps, null)(App);
