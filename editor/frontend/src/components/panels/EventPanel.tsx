import type { Event, OntologyPayload } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { flowsTriggeredBy } from './helpers';
import { ChipList, HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  event: Event;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function EventPanel({ event, data, onNavigate }: Props) {
  const triggered = flowsTriggeredBy(data, event.name);

  return (
    <article className="panel panel--event">
      <PanelHeader kindLabel="event" name={event.name} />

      <Section>
        <Row k="observed by">
          <Chip kind="role" onClick={() => onNavigate({ kind: 'role', id: event.observed_by })}>
            {event.observed_by}
          </Chip>
        </Row>
        {event.domain && <Row k="domain">{event.domain}</Row>}
      </Section>

      {event.description && (
        <Section title="description">
          <p className="panel-body">{event.description}</p>
        </Section>
      )}

      <Section title={`triggers flows (${triggered.length})`}>
        <ChipList empty="no flows triggered">
          {triggered.map((f) => (
            <Chip key={f.name} kind="flow" onClick={() => onNavigate({ kind: 'flow', id: f.name })}>
              {f.name}
            </Chip>
          ))}
        </ChipList>
      </Section>

      {event.llm_prompt_hint && (
        <HintBlock label="llm prompt hint">{event.llm_prompt_hint}</HintBlock>
      )}
    </article>
  );
}
