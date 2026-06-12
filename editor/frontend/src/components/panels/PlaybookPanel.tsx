import type { OntologyPayload, Playbook } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { hasEntity, hasFlow, roleByName } from './helpers';
import { ChipList, HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  playbook: Playbook;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

/**
 * Playbook detail. A playbook is a (role, trigger_event) choreography: it
 * scaffolds how an agent assembles typed context and the choice space it
 * then decides over. It declares world content only — which queries, which
 * criteria, which resolution paths — never the preference or ordering. The
 * `selects_one_of` list is rendered neutralized to reinforce that the order
 * carries no priority (agent_system_design.md §2 / §6.1).
 */
export function PlaybookPanel({ playbook, data, onNavigate }: Props) {
  const anchor = roleByName(data, playbook.role);
  const decision = playbook.decision;

  return (
    <article className="panel panel--playbook">
      <PanelHeader kindLabel="playbook" name={playbook.name} />

      <Section>
        <Row k="role">
          <Chip kind="role" boundary={anchor?.is_boundary} onClick={() => onNavigate({ kind: 'role', id: playbook.role })}>
            {playbook.role}
          </Chip>
        </Row>
        <Row k="trigger">
          <Chip kind="event" onClick={() => onNavigate({ kind: 'event', id: playbook.triggered_by })}>
            {playbook.triggered_by}
          </Chip>
        </Row>
        <Row k="input">
          {hasEntity(data, playbook.input_quantum) ? (
            <Chip kind="entity" onClick={() => onNavigate({ kind: 'entity', id: playbook.input_quantum })}>
              {playbook.input_quantum}
            </Chip>
          ) : (
            <span className="panel-muted">{playbook.input_quantum}</span>
          )}
        </Row>
        {playbook.synchronization && <Row k="sync">{playbook.synchronization}</Row>}
        <Row k="evidence set">{playbook.closed_set ? 'closed — sufficient' : 'open'}</Row>
        {playbook.domain && <Row k="domain">{playbook.domain}</Row>}
      </Section>

      <Section title={`context assembly (${playbook.context_assembly.length})`}>
        {playbook.context_assembly.length === 0 ? (
          <p className="panel-empty">no context-assembly queries</p>
        ) : (
          <ul className="playbook-steps">
            {playbook.context_assembly.map((step) => (
              <li key={step.flow} className="playbook-step">
                <div className="playbook-step-head">
                  <Chip kind="flow" onClick={() => onNavigate({ kind: 'flow', id: step.flow })}>
                    {step.flow}
                  </Chip>
                  {step.required === false && <span className="playbook-step-opt">optional</span>}
                </div>
                {step.inputs_from_quantum.length > 0 && (
                  <ul className="playbook-bindings">
                    {step.inputs_from_quantum.map((b) => (
                      <li key={b.param}>
                        <code className="playbook-bind-param">{b.param}</code>
                        <span className="playbook-bind-arrow">←</span>
                        <code className="playbook-bind-src">{b.from_quantum}</code>
                      </li>
                    ))}
                  </ul>
                )}
              </li>
            ))}
          </ul>
        )}
      </Section>

      {decision && (
        <Section title="decision">
          <div className="playbook-decision-sub">criteria (advisory)</div>
          <ChipList empty="no criteria">
            {decision.criteria_refs.map((c) => (
              <Chip key={c} kind="axiom" onClick={() => onNavigate({ kind: 'axiom', id: c })}>
                {c}
              </Chip>
            ))}
          </ChipList>
          <div className="playbook-decision-sub">selects one of</div>
          <ChipList empty="no resolution paths">
            {decision.selects_one_of.map((f) => (
              <Chip
                key={f}
                kind="flow"
                onClick={() => hasFlow(data, f) && onNavigate({ kind: 'flow', id: f })}
              >
                {f}
              </Chip>
            ))}
          </ChipList>
          <p className="playbook-note">
            list order carries no priority — the agent weighs the criteria and picks exactly one.
          </p>
        </Section>
      )}

      {playbook.always_fires.length > 0 && (
        <Section title={`always fires (${playbook.always_fires.length})`}>
          <ChipList>
            {playbook.always_fires.map((af) => {
              if (af.event) {
                return (
                  <Chip key={`e:${af.event}`} kind="event" onClick={() => onNavigate({ kind: 'event', id: af.event! })}>
                    {af.event}
                  </Chip>
                );
              }
              if (af.flow) {
                return (
                  <Chip key={`f:${af.flow}`} kind="flow" onClick={() => hasFlow(data, af.flow!) && onNavigate({ kind: 'flow', id: af.flow! })}>
                    {af.flow}
                  </Chip>
                );
              }
              return null;
            })}
          </ChipList>
        </Section>
      )}

      {playbook.llm_prompt_hint && (
        <HintBlock label="llm context">{playbook.llm_prompt_hint}</HintBlock>
      )}
    </article>
  );
}
