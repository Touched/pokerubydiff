import React from 'react';
import { connect } from 'react-redux';

import Diff from '../../components/Diff';
import LoadingOverlay from '../../components/LoadingOverlay';

function App({ diff, error, loading }) {
  return (
    <div>
      {loading ? <LoadingOverlay /> : null}
      {error ? <pre>{error}</pre> : <Diff diff={diff} />}
    </div>
  );
}

function mapStateToProps(state) {
  return {
    diff: state.messages.diff,
    loading: state.messages.building,
    error: state.messages.error,
  };
}

export default connect(mapStateToProps, null)(App);
