import type { Flow, OntologyPayload } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { hasEntity, roleByName } from './helpers';
import { HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  flow: Flow;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function FlowPanel({ flow, data, onNavigate }: Props) {
  const src = roleByName(data, flow.source_role);
  const dst = roleByName(data, flow.target_role);
  const kindLabel = `${flow.kind} flow${flow.returns ? ' · query' : ''}`;

  return (
    <article className="panel panel--flow">
      <PanelHeader kindLabel={kindLabel} name={flow.name} />

      <Section>
        <Row k="source">
          <Chip kind="role" boundary={src?.is_boundary} onClick={() => onNavigate({ kind: 'role', id: flow.source_role })}>
            {flow.source_role}
          </Chip>
        </Row>
        <Row k="target">
          <Chip kind="role" boundary={dst?.is_boundary} onClick={() => onNavigate({ kind: 'role', id: flow.target_role })}>
            {flow.target_role}
          </Chip>
        </Row>
        <Row k="kind">{flow.kind}</Row>
        <Row k="quantum">
          {hasEntity(data, flow.quantum) ? (
            <Chip kind="entity" onClick={() => onNavigate({ kind: 'entity', id: flow.quantum })}>
              {flow.quantum}
            </Chip>
          ) : (
            <span className="panel-muted">{flow.quantum}</span>
          )}
        </Row>
        {flow.trigger_event && (
          <Row k="trigger">
            <Chip kind="event" onClick={() => onNavigate({ kind: 'event', id: flow.trigger_event! })}>
              {flow.trigger_event}
            </Chip>
          </Row>
        )}
        {flow.lifecycle_ref && (
          <Row k="lifecycle">
            <Chip kind="state_machine" onClick={() => onNavigate({ kind: 'state_machine', id: flow.lifecycle_ref! })}>
              {flow.lifecycle_ref}
            </Chip>
          </Row>
        )}
        {flow.returns && (
          <Row k="returns">
            {hasEntity(data, flow.returns) ? (
              <Chip kind="entity" onClick={() => onNavigate({ kind: 'entity', id: flow.returns! })}>
                {flow.returns}
              </Chip>
            ) : (
              <span className="panel-muted">{flow.returns}</span>
            )}
          </Row>
        )}
        {flow.domain && <Row k="domain">{flow.domain}</Row>}
      </Section>

      {flow.axioms.length > 0 && (
        <Section title={`axioms (${flow.axioms.length})`}>
          <ul className="axiom-list">
            {flow.axioms.map((a) => (
              <li key={a.name} className="axiom-item">
                <span className={`axiom-dot axiom-dot--${a.severity ?? 'advisory'}`} aria-hidden />
                <div className="axiom-body">
                  <div className="axiom-head">
                    <Chip kind="axiom" onClick={() => onNavigate({ kind: 'axiom', id: a.name })}>
                      {a.name}
                    </Chip>
                    {a.severity && <span className="axiom-sev">{a.severity}</span>}
                  </div>
                  <p className="axiom-nl">{a.nl}</p>
                  {a.on_failure_route_to && (
                    <p className="axiom-route">
                      on failure →{' '}
                      <Chip kind="flow" onClick={() => onNavigate({ kind: 'flow', id: a.on_failure_route_to! })}>
                        {a.on_failure_route_to}
                      </Chip>
                    </p>
                  )}
                </div>
              </li>
            ))}
          </ul>
        </Section>
      )}

      {flow.llm_prompt_hint && (
        <HintBlock label="llm context">{flow.llm_prompt_hint}</HintBlock>
      )}
    </article>
  );
}
