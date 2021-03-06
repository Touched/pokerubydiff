import React from 'react';
import PropTypes from 'prop-types';
import R from 'ramda';
import classNames from 'classnames';
import ReactCSSTransitionGroup from 'react-addons-css-transition-group';

import './styles.scss';

function formatAddress(address) {
  return address.toString(16).padStart(8, '0');
}

function formatTextChanges(changes, text) {
  let last = 0;
  const tags = [];
  const classes = {
    ' ': '',
    '^': 'change',
    '+': 'insert',
    '-': 'delete',
  };

  function pushTag(tag, pos, text) {
    if (text.length) {
      tags.push(<span key={pos} className={classes[tag]}>{text}</span>);
    }
  }

  changes.forEach(([opcode, start, end]) => {
    if (start !== last) {
      pushTag(' ', last, text.substring(last, start));
    }

    pushTag(opcode, start, text.substring(start, end));
    last = end;
  });

  pushTag(' ', last, text.substring(last));

  return <span className="text">{tags}</span>;
}

function Pre({ children }) {
  return <pre>{children}</pre>;
}

function Cell(props) {
  return <div {...props} className={classNames('cell', props.className)} />
}

function Gutter({ changed, address, blank }) {
  const className = classNames('gutter', {
    'change': changed,
  });

  return <Cell className={className}>{blank ? <span>&nbsp;</span> : formatAddress(address)}</Cell>;
}

function Row({ changes, className, address, blank, children }) {
  return blank ? (
    <div className={classNames('row', className)} >
      <Gutter address={address} blank={blank} />
    </div>
  ) : (
    <div className={classNames('row', className)} >
      <Gutter address={address} changed={changes && changes.address} />
      {children}
    </div>
  );
}

function CodeDiffLine({ changes, className, blank, label, address, diff, text }) {
  const indent = '\t';
  const textChanges = changes && changes.text || [];

  return (
    <div>
      {label !== null && (
         <Row changes={changes} className={className} address={address} blank={blank}>
           <Cell className="code-label">
             {label !== '' && <Pre>{label}:</Pre>}
           </Cell>
         </Row>
      )}
      <Row changes={changes} className={className} address={address} blank={blank}>
        <Cell className="code">
          <Pre>{indent}{formatTextChanges(textChanges, text)}</Pre>
        </Cell>
      </Row>
    </div>
  );
}

function DataDiffLine({ changes, className, label, blank, address, diff, text }) {
  const textChanges = changes && changes.text || [];

  return (
    <Row changes={changes} className={className} address={address} blank={blank}>
      <Cell className="data">
        <Pre>{label && `${label}:\t`}{formatTextChanges(textChanges, text)}</Pre>
      </Cell>
    </Row>
  );
}

function PaddingDiffLine({ changes, className, blank, address, diff, text }) {
  const textChanges = changes && changes.text || [];

  return (
    <Row changes={changes} className={className} address={address} blank={blank}>
      <Cell className="padding"><Pre>{formatTextChanges(textChanges, text)}</Pre></Cell>
    </Row>
  );
}

function DiffLine(props) {
  const className = classNames({
    insert: !props.blank && props.opcode === '+',
    delete: !props.blank && props.opcode === '-',
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

function InlineDiff({ description, diff }) {
  let expectedNextAddress = null;

  const addresses = [];

  const lines = diff.map((item) => {
    if (item.opcode === 'x') {
      return {
        ...item,
        blank: true,
      };
    }

    if (expectedNextAddress && item.address !== expectedNextAddress) {
      throw new Error(
        'Disassembly item did not begin where the last one end ended: ' +
        `Expected item to be at ${formatAddress(expectedNextAddress)} ` +
        `but it was at ${formatAddress(item.address)}.`
      );
    }
    expectedNextAddress = item.address + item.size;

    return {
      ...item,
      blank: false,
    };
  });

  function makeKey(line, index) {
    console.log(line.text.trim());
    return `${formatAddress(line.address)}-${index}`;
  }

  return (
    <ReactCSSTransitionGroup
      className="diff-inline"
      transitionName="diff-change"
      transitionEnterTimeout={1000}
      transitionLeaveTimeout={1000}
    >
      {lines.map((line, index) => <DiffLine key={makeKey(line, index)} {...line} />, diff)}
    </ReactCSSTransitionGroup>
  );
}

function SideBySideDiff({ diff }) {
  const prepareLines = R.curry((prefix, item) => {
    // Blank out lines that match the prefix
    return item.opcode === prefix ? {
      ...item,
      opcode: 'x',
    } : item;
  });

  // Ensure the respective sides have blank spaces for insertions/deletions, and remove
  // any replacement changes (i.e. diffs that are not a whole line but inside the line)
  // that do not belong on that side.
  const left = R.reject(R.propEq('opcode', '>'), R.map(prepareLines('+'), diff));
  const right = R.reject(R.propEq('opcode', '<'), R.map(prepareLines('-'), diff));

  return (
    <div className="diff-side-by-side">
      <div className="diff-side-by-side-pane">
        <InlineDiff description="Original" diff={left} />
      </div>
      <div className="diff-side-by-side-pane">
        <InlineDiff description="Modified" diff={right} />
      </div>
    </div>
  );
}

export default function Diff({ diff, diffMode, setDiffMode }) {
  return (
    <div className="diff">
      <SideBySideDiff diff={diff} />
    </div>
  );
}
