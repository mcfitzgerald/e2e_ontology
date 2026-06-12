import { Handle, Position, type NodeProps } from '@xyflow/react';
import type { PBVariant } from './layout';

export interface PlaybookNodeData extends Record<string, unknown> {
  label: string;
  variant: PBVariant;
  tag?: string;
  clickable: boolean;
  dimmed: boolean;
}

/**
 * One node in the playbook choreography graph. The center playbook reads as
 * an emphasized double-rule card; sources/queries/resolutions/effects carry a
 * left accent bar colored by their branch family so the fan-out is legible at
 * a glance. Unresolvable refs (a flow not in the ontology) render non-clickable.
 */
export function PlaybookNode({ data, selected }: NodeProps) {
  const d = data as PlaybookNodeData;
  const cls = ['rf-pb-node', `rf-pb-node--${d.variant}`];
  if (selected) cls.push('selected');
  if (d.dimmed) cls.push('dimmed');
  if (d.clickable) cls.push('clickable');

  return (
    <div className={cls.join(' ')}>
      <Handle type="target" position={Position.Left} isConnectable={false} className="rf-handle" />
      <div className="rf-pb-node-body">
        {d.tag && <span className="rf-pb-node-tag">{d.tag}</span>}
        <span className="rf-pb-node-name">{d.label}</span>
      </div>
      <Handle type="source" position={Position.Right} isConnectable={false} className="rf-handle" />
    </div>
  );
}
