import { Component, Children } from 'react';
import PropTypes from 'prop-types';
import withSideEffect from 'react-side-effect';
import classNames from 'classnames';

class BodyClasses extends Component {
  render() {
    return Children.only(this.props.children);
  }
}

BodyClasses.propTypes = {
  className: PropTypes.string.isRequired
};

function reducePropsToState(propsList) {
  console.log(propsList.map(({ className }) => className));

  return classNames(...propsList.map(({ className }) => className));
}

function handleStateChangeOnClient(className) {
  document.body.className = className;
}

export default withSideEffect(
  reducePropsToState,
  handleStateChangeOnClient
)(BodyClasses);
