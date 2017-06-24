import React from 'react';
import { connect } from 'react-redux';

import Diff from '../../components/Diff';
import LoadingOverlay from '../../components/LoadingOverlay';
import ErrorOverlay from '../../components/ErrorOverlay';
import MatchOverlay from '../../components/MatchOverlay';

function App({ match, diff, error, loading }) {
  return (
    <div>
      {loading && <LoadingOverlay />}
      {error && <ErrorOverlay message={error} />}
      {match && <MatchOverlay />}
      <Diff diff={diff} />
    </div>
  );
}

function mapStateToProps(state) {
  return {
    diff: state.messages.diff,
    loading: state.messages.building,
    error: state.messages.error,
    match: state.messages.match,
  };
}

export default connect(mapStateToProps, null)(App);
