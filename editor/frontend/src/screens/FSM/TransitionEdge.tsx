import {
  BaseEdge,
  EdgeLabelRenderer,
  getSmoothStepPath,
  type EdgeProps,
} from '@xyflow/react';

export interface TransitionEdgeData extends Record<string, unknown> {
  trigger: string | null;
  /** True when the trigger event resolves to an event in the ontology. */
  triggerResolves: boolean;
  guard: string | null;
  /** True when the guard axiom resolves to a real flow.axiom in the ontology. */
  guardResolves: boolean;
  dimmed: boolean;
  showLabel: boolean;
  onTriggerClick?: (trigger: string) => void;
  onGuardClick?: (guard: string) => void;
}

/**
 * FSM transition edge. Smoothstep paths read better than bezier on a
 * pure-LR layout (states share rank-rows). Labels are HTML so the guard
 * chip can carry its own click handler — clicking it navigates to the
 * axiom even when that axiom lives on a different flow than the
 * lifecycle owner.
 */
export function TransitionEdge({
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
  const d = (data ?? {}) as TransitionEdgeData;
  const [path, labelX, labelY] = getSmoothStepPath({
    sourceX,
    sourceY,
    targetX,
    targetY,
    sourcePosition,
    targetPosition,
    borderRadius: 6,
  });
  const cls = ['rf-fsm-transition'];
  if (selected) cls.push('selected');
  if (d.dimmed) cls.push('dimmed');

  return (
    <>
      <BaseEdge
        id={id}
        path={path}
        className={cls.join(' ')}
        markerEnd="url(#arrow-ink)"
        interactionWidth={24}
      />
      {d.showLabel && (d.trigger || d.guard) && (
        <EdgeLabelRenderer>
          <div
            className="rf-fsm-transition-label"
            style={{ transform: `translate(-50%, -50%) translate(${labelX}px, ${labelY}px)` }}
          >
            {d.trigger && (
              d.triggerResolves ? (
                <button
                  type="button"
                  className="rf-fsm-transition-trigger clickable"
                  onClick={(e) => {
                    e.stopPropagation();
                    if (d.onTriggerClick && d.trigger) d.onTriggerClick(d.trigger);
                  }}
                  title="open event"
                >
                  on {d.trigger}
                </button>
              ) : (
                <span className="rf-fsm-transition-trigger">on {d.trigger}</span>
              )
            )}
            {d.guard && (
              <button
                type="button"
                className={`rf-fsm-transition-guard${d.guardResolves ? '' : ' unresolved'}`}
                onClick={(e) => {
                  e.stopPropagation();
                  if (d.onGuardClick && d.guard) d.onGuardClick(d.guard);
                }}
                title={d.guardResolves ? 'open guard axiom' : 'guard axiom not found in ontology'}
              >
                ⊢ {d.guard}
              </button>
            )}
          </div>
        </EdgeLabelRenderer>
      )}
    </>
  );
}
