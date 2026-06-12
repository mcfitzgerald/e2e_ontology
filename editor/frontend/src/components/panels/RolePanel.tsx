import type { OntologyPayload, Role } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { incomingFlows, observedEvents, outgoingFlows, playbooksForRole, toolsAvailableTo } from './helpers';
import { ChipList, HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  role: Role;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function RolePanel({ role, data, onNavigate }: Props) {
  const outgoing = outgoingFlows(data, role.name);
  const incoming = incomingFlows(data, role.name);
  const events = observedEvents(data, role.name);
  const playbooks = playbooksForRole(data, role.name);
  const tools = toolsAvailableTo(data, role.name);
  const kindLabel = role.is_boundary ? 'boundary role' : 'role';

  return (
    <article className="panel panel--role">
      <PanelHeader kindLabel={kindLabel} name={role.name} />

      <Section>
        {role.domain && <Row k="domain">{role.domain}</Row>}
        {role.is_boundary && <Row k="boundary">true — external to the supply chain</Row>}
        {role.human_involvement && <Row k="hitl">{role.human_involvement}</Row>}
        {role.can_be_played_by && <Row k="played by">{role.can_be_played_by}</Row>}
      </Section>

      {role.description && (
        <Section title="description">
          <p className="panel-body">{role.description}</p>
        </Section>
      )}

      <Section title={`outgoing flows (${outgoing.length})`}>
        <ChipList empty="no outgoing flows">
          {outgoing.map((f) => (
            <Chip
              key={f.name}
              kind="flow"
              onClick={() => onNavigate({ kind: 'flow', id: f.name })}
              title={`→ ${f.target_role}`}
            >
              {f.name}
            </Chip>
          ))}
        </ChipList>
      </Section>

      <Section title={`incoming flows (${incoming.length})`}>
        <ChipList empty="no incoming flows">
          {incoming.map((f) => (
            <Chip
              key={f.name}
              kind="flow"
              onClick={() => onNavigate({ kind: 'flow', id: f.name })}
              title={`from ${f.source_role}`}
            >
              {f.name}
            </Chip>
          ))}
        </ChipList>
      </Section>

      {events.length > 0 && (
        <Section title={`observed events (${events.length})`}>
          <ChipList>
            {events.map((e) => (
              <Chip key={e.name} kind="event" onClick={() => onNavigate({ kind: 'event', id: e.name })}>
                {e.name}
              </Chip>
            ))}
          </ChipList>
        </Section>
      )}

      {playbooks.length > 0 && (
        <Section title={`playbooks (${playbooks.length})`}>
          <ChipList>
            {playbooks.map((p) => (
              <Chip key={p.name} kind="playbook" onClick={() => onNavigate({ kind: 'playbook', id: p.name })}>
                {p.name}
              </Chip>
            ))}
          </ChipList>
        </Section>
      )}

      {tools.length > 0 && (
        <Section title={`tools available (${tools.length})`}>
          <ChipList>
            {tools.map((t) => (
              <Chip key={t.name} kind="tool" onClick={() => onNavigate({ kind: 'tool', id: t.name })}>
                {t.name}
              </Chip>
            ))}
          </ChipList>
        </Section>
      )}

      {role.llm_prompt_hint && (
        <HintBlock label="llm context">{role.llm_prompt_hint}</HintBlock>
      )}
    </article>
  );
}
