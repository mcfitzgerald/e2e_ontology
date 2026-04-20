import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { DiffStatus, Role } from '../../api/types';

export interface RoleNodeData extends Record<string, unknown> {
  role: Role;
  diffStatus: DiffStatus | null;
  dimmed: boolean;
}

/**
 * Role node rendered inside React Flow. HTML-based so CSS cascades
 * naturally and the hit-target is a regular DOM element (React Flow
 * handles selection + click via its own event layer). Source and target
 * handles are hidden visually but required so edges have attachment
 * points; we don't support manual wire-up so Handle isConnectable={false}.
 */
export function RoleNode({ data, selected }: NodeProps) {
  const { role, diffStatus, dimmed } = data as RoleNodeData;

  const cls = ['rf-role-node'];
  if (role.is_boundary) cls.push('boundary');
  if (selected) cls.push('selected');
  if (dimmed) cls.push('dimmed');

  return (
    <div className={cls.join(' ')}>
      <Handle type="target" position={Position.Left} isConnectable={false} className="rf-handle" />
      {diffStatus && diffStatus !== 'removed' && (
        <span className={`rf-diff-gutter ${diffStatus}`} title={`${diffStatus} since HEAD`}>
          {diffStatus === 'added' ? '+' : '~'}
        </span>
      )}
      <span className="rf-role-name">{role.name}</span>
      {role.human_involvement && role.human_involvement !== 'autonomous' && (
        <span
          className="rf-hitl-badge"
          title={`HITL ${role.human_involvement}`}
          aria-label={`HITL ${role.human_involvement}`}
        >
          {role.human_involvement === 'required' ? '!' : '?'}
        </span>
      )}
      <Handle type="source" position={Position.Right} isConnectable={false} className="rf-handle" />
    </div>
  );
}
