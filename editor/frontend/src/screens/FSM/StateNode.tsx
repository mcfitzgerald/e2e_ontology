import { Handle, Position, type NodeProps } from '@xyflow/react';

export interface StateNodeData extends Record<string, unknown> {
  name: string;
  isInitial: boolean;
  isTerminal: boolean;
  dimmed: boolean;
}

/**
 * FSM state rendered as an HTML custom node.
 * - Initial states get a small entry-arrow glyph on the left.
 * - Terminal states get a concentric outer border (the classic
 *   "accept state" double-rule from automata diagrams).
 * - Otherwise plain rectangle.
 */
export function StateNode({ data, selected }: NodeProps) {
  const d = data as StateNodeData;
  const cls = ['rf-fsm-state'];
  if (selected) cls.push('selected');
  if (d.dimmed) cls.push('dimmed');
  if (d.isInitial) cls.push('initial');
  if (d.isTerminal) cls.push('terminal');

  return (
    <div className={cls.join(' ')}>
      <Handle
        type="target"
        position={Position.Left}
        isConnectable={false}
        className="rf-handle"
      />
      {d.isInitial && <span className="rf-fsm-state-entry" aria-hidden>▸</span>}
      {d.isTerminal && <div className="rf-fsm-state-terminal-ring" aria-hidden />}
      <div className="rf-fsm-state-body">
        <span className="rf-fsm-state-name">{d.name}</span>
        <span className="rf-fsm-state-tags">
          {d.isInitial && <span className="rf-fsm-state-tag">initial</span>}
          {d.isTerminal && <span className="rf-fsm-state-tag terminal">terminal</span>}
        </span>
      </div>
      <Handle
        type="source"
        position={Position.Right}
        isConnectable={false}
        className="rf-handle"
      />
    </div>
  );
}
