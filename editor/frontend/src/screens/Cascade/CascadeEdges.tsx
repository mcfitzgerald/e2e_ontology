import { BaseEdge, EdgeLabelRenderer, getBezierPath, type EdgeProps } from '@xyflow/react';

/**
 * Cascade edges come in two kinds: event-mediated (ordinary flow of
 * causation via observed_by → trigger_event) and axiom_trip (recovery
 * branches from blocking axioms with on_failure_route_to). Labels are
 * hidden by default and pop on edge hover or when an endpoint is in
 * focus (hovered/selected) — keeps the canvas legible at density.
 */

export interface CascadeEdgeData extends Record<string, unknown> {
  via: string;
  dimmed: boolean;
  showLabel: boolean;
}

export function EventEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const d = (data ?? {}) as CascadeEdgeData;
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });
  const cls = ['cascade-arrow', 'event'];
  if (selected) cls.push('selected');
  if (d.dimmed) cls.push('dimmed');
  return (
    <>
      <BaseEdge id={id} path={path} className={cls.join(' ')} markerEnd="url(#arrow-ink)" interactionWidth={24} />
      {d.showLabel && (
        <EdgeLabelRenderer>
          <div
            className="rf-cascade-arrow-label event"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            via {d.via}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}

export function AxiomTripEdge({
  id,
  sourceX,
  sourceY,
  targetX,
  targetY,
  sourcePosition,
  targetPosition,
  data,
  selected,
}: EdgeProps) {
  const d = (data ?? {}) as CascadeEdgeData;
  const [path, labelX, labelY] = getBezierPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
  });
  const cls = ['cascade-arrow', 'axiom_trip'];
  if (selected) cls.push('selected');
  if (d.dimmed) cls.push('dimmed');
  return (
    <>
      <BaseEdge id={id} path={path} className={cls.join(' ')} markerEnd="url(#arrow-ink)" interactionWidth={24} />
      {d.showLabel && (
        <EdgeLabelRenderer>
          <div
            className="rf-cascade-arrow-label axiom_trip"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            ⊥ {d.via}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
