import type { OntologyPayload, StateMachine } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { flowsUsingFsm } from './helpers';
import { ChipList, PanelHeader, Row, Section } from './shared';

interface Props {
  fsm: StateMachine;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function FSMPanel({ fsm, data, onNavigate }: Props) {
  const sharing = flowsUsingFsm(data, fsm.name);

  return (
    <article className="panel panel--fsm">
      <PanelHeader kindLabel="state machine" name={fsm.name} />

      <Section>
        {fsm.domain && <Row k="domain">{fsm.domain}</Row>}
        <Row k="initial">{fsm.initial}</Row>
        {fsm.terminal.length > 0 && <Row k="terminal">{fsm.terminal.join(', ')}</Row>}
        <Row k={`states (${fsm.states.length})`}>
          <span className="panel-inline-list">
            {fsm.states.map((s, i) => (
              <span key={s} className="panel-state">
                {s}
                {i < fsm.states.length - 1 ? ', ' : ''}
              </span>
            ))}
          </span>
        </Row>
      </Section>

      {fsm.transitions.length > 0 && (
        <Section title={`transitions (${fsm.transitions.length})`}>
          <ul className="fsm-transition-list">
            {fsm.transitions.map((t, i) => (
              <li key={`${t.from_state}-${t.to_state}-${i}`} className="fsm-transition">
                <code className="fsm-state">{t.from_state}</code>
                <span className="fsm-arrow">→</span>
                <code className="fsm-state">{t.to_state}</code>
                {t.trigger && <span className="fsm-trigger"> on {t.trigger}</span>}
                {t.guard && (
                  <span className="fsm-guard">
                    {' '}
                    [{t.guard}]
                  </span>
                )}
              </li>
            ))}
          </ul>
        </Section>
      )}

      <Section title={`flows sharing this lifecycle (${sharing.length})`}>
        <ChipList empty="no flows reference this FSM">
          {sharing.map((f) => (
            <Chip key={f.name} kind="flow" onClick={() => onNavigate({ kind: 'flow', id: f.name })}>
              {f.name}
            </Chip>
          ))}
        </ChipList>
      </Section>
    </article>
  );
}
