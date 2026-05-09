import { Handle, Position, type NodeProps } from '@xyflow/react';
import { domainFor } from '../../config/domains';
import type { Flow } from '../../api/types';

export interface FlowOccurrenceNodeData extends Record<string, unknown> {
  flow: Flow;
  srcDomain: string | null;
  dstDomain: string | null;
  showAxioms: boolean;
  dimmed: boolean;
}

/**
 * Cascade node — a single flow occurrence at a (depth, domain) position.
 * Top + bottom color bands show source and target domain tints so the
 * hop is visible at a glance. Kind glyph (INFO / MATE / CASH) upper-right,
 * axiom severity dot below it when applicable.
 */
export function FlowOccurrenceNode({ data, selected }: NodeProps) {
  const { flow, srcDomain, dstDomain, showAxioms, dimmed } =
    data as FlowOccurrenceNodeData;

  const srcTint = domainFor(srcDomain)?.tint ?? 'var(--paper-dark)';
  const dstTint = domainFor(dstDomain)?.tint ?? 'var(--paper-dark)';
  const blocking = flow.axioms.find((a) => a.severity === 'blocking');
  const warning = flow.axioms.find((a) => a.severity === 'warning');
  const axiom = blocking ?? warning ?? flow.axioms[0];
  const kindAbbr = flow.kind.slice(0, 4).toUpperCase();

  const cls = ['rf-cascade-card', flow.kind];
  if (selected) cls.push('selected');
  if (dimmed) cls.push('dimmed');

  return (
    <div className={cls.join(' ')}>
      <Handle type="target" position={Position.Left} isConnectable={false} className="rf-handle" />
      <div className="rf-cascade-card-band-src" style={{ background: srcTint }} />
      <div className="rf-cascade-card-body">
        <div className="rf-cascade-card-name">{flow.name}</div>
        <div className="rf-cascade-card-route">
          {flow.source_role} → {flow.target_role}
        </div>
      </div>
      <div className={`rf-cascade-card-kind ${flow.kind}`}>{kindAbbr}</div>
      {showAxioms && axiom && (
        <div
          className={`rf-cascade-card-axiom ${axiom.severity ?? 'advisory'}`}
          title={`${axiom.severity ?? 'advisory'} axiom: ${axiom.name}`}
        />
      )}
      <div className="rf-cascade-card-band-dst" style={{ background: dstTint }} />
      <Handle type="source" position={Position.Right} isConnectable={false} className="rf-handle" />
    </div>
  );
}
