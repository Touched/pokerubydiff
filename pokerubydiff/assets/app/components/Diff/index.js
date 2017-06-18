import React from 'react';
import R from 'ramda';
import classNames from 'classnames';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';

import './styles.scss';

const prefixes = {
  ' ': 'equal',
  '+': 'insert',
  '-': 'delete',
};

function formatAddress(address) {
  return address.toString(16).padStart(8, '0');
}

function makeLine([prefix, type, address, size, text, label]) {
  return {
    diff: prefixes[prefix],
    address,
    type,
    size,
    text,
    label,
    blank: false,
  };
}

function Pre({ children }) {
  return <pre>{children}</pre>;
}

function Cell(props) {
  return <div {...props} className={classNames('cell', props.className)} />
}

function Gutter({ address, blank }) {
  return <Cell className="gutter">{blank ? <span>&nbsp;</span> : formatAddress(address)}</Cell>;
}

function Row({ className, address, blank, children }) {
  return blank ? (
    <div className={classNames('row', className)} >
      <Gutter address={address} blank={blank} />
    </div>
  ) : (
    <div className={classNames('row', className)} >
      <Gutter address={address} />
      {children}
    </div>
  );
}

function CodeDiffLine({ className, blank, label, address, diff, text }) {
  const indentedText = `\t\t${text}`;

  return (
    <div>
      {label && (
         <Row className={className} address={address} blank={blank}>
           <Cell className="code-label">
             <Pre>{label}:</Pre>
           </Cell>
         </Row>
      )}
      <Row className={className} address={address} blank={blank}>
        <Cell className="code">
          <Pre>{indentedText}</Pre>
        </Cell>
      </Row>
    </div>
  );
}

function DataDiffLine({ className, label, blank, address, diff, text }) {
  return (
    <Row className={className} address={address} blank={blank}>
      <Cell className="data">
        <Pre>{label && `${label}:\t`}{text}</Pre>
      </Cell>
    </Row>
  );
}

function PaddingDiffLine({ className, blank, address, diff, text }) {
  return (
    <Row className={className} address={address} blank={blank}>
      <Cell className="padding"><Pre>{text}</Pre></Cell>
    </Row>
  );
}

function DiffLine(props) {
  const className = classNames({
    insert: !props.blank && props.diff === 'insert',
    delete: !props.blank && props.diff === 'delete',
  });

  switch (props.type) {
    case 'code':
      return <CodeDiffLine className={className} {...props} />;
    case 'data':
      return <DataDiffLine className={className} {...props} />;
    case 'padding':
      return <PaddingDiffLine className={className} {...props} />;
  }
}

function InlineDiff({ diff }) {
  return (
    <ReactCSSTransitionGroup
      className="diff-inline"
      transitionName="diff-change"
      transitionEnterTimeout={1000}
      transitionLeaveTimeout={1000}
    >
      {diff.map((line) => <DiffLine key={`${line.address}${line.text}`} {...line} />, diff)}
    </ReactCSSTransitionGroup>
  );
}

function SideBySideDiff({ diff }) {
  const prepareLines = R.curry((prefix, line) => {
    if (R.head(line) === prefix) {
      return {
        ...makeLine(line),
        blank: true,
      };
    }

    return makeLine(line);
  });

  const left = R.map(prepareLines('+'), diff);
  const right = R.map(prepareLines('-'), diff);

  return (
    <div className="diff-side-by-side">
      <div className="diff-side-by-side-pane">
        <InlineDiff diff={left} />
      </div>
      <div className="diff-side-by-side-pane">
        <InlineDiff diff={right} />
      </div>
    </div>
  );
}

export default function Diff({ diff }) {
  return (
    <div className="diff">
      <SideBySideDiff diff={diff} />
    </div>
  );
}
