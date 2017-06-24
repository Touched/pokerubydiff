import React from 'react';

import BodyClasses from '../BodyClasses';
import './styles.scss';

export default function ErrorOverlay({ message }) {
  return (
    <BodyClasses className="overlay">
      <div className="error-overlay">
        <svg className="icon" viewBox="0 0 24 24">
          <path d="M19,6.41L17.59,5L12,10.59L6.41,5L5,6.41L10.59,12L5,17.59L6.41,19L12,13.41L17.59,19L19,17.59L13.41,12L19,6.41Z" />
        </svg>
        <h1>Error</h1>
        <pre>{message}</pre>
      </div>
    </BodyClasses>
  );
}
