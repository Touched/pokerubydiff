import React from 'react';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';

import BodyClasses from '../BodyClasses';
import './styles.scss';

export default function MatchOverlay() {
  const circleStyle = {
    fill: 'none',
    stroke: '#fff',
    strokeWidth: 3,
    strokeLinejoin: 'round',
    strokeMiterlimit: 10,
  };

  const tickStyle = {
    fill: 'none',
    stroke: '#fff',
    strokeWidth: 3,
    strokeLinejoin: 'round',
    strokeMiterlimit: 10,
  };

  const style = {
    enableBackground: 'new 0 0 37 37',
  };

  return (
    <BodyClasses className="overlay">
      <ReactCSSTransitionGroup
        transitionName="draw"
        transitionAppear={true}
        transitionAppearTimeout={1500}
        transitionEnter={false}
        transitionLeave={false}
        className="match-overlay"
      >
        <svg version="1.1" id="tick" viewBox="0 0 37 37" style={style} width={200} height={200}>
          <path className="circle path" style={circleStyle} d="M30.5,6.5L30.5,6.5c6.6,6.6,6.6,17.4,0,24l0,0c-6.6,6.6-17.4,6.6-24,0l0,0c-6.6-6.6-6.6-17.4,0-24l0,0C13.1-0.2,23.9-0.2,30.5,6.5z"
	/>
          <polyline className="tick path" style={tickStyle} points="11.6,20 15.9,24.2 26.4,13.8 "/>
        </svg>
        <div>
          <h1>Match</h1>
        </div>
      </ReactCSSTransitionGroup>
    </BodyClasses>
  );
}
