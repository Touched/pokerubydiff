import React from 'react';
import Loader from 'halogen/MoonLoader';

import BodyClasses from '../BodyClasses';
import './styles.scss';

export default function LoadingOverlay() {
  return (
    <BodyClasses className="overlay">
      <div className="loading-overlay">
        <Loader color="#cccccc" size="160px" margin="4px"/>
      </div>
    </BodyClasses>
  );
}
