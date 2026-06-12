import type { Entity, OntologyPayload } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { flowsCarryingEntity, flowsReturningEntity, toolsTouchingEntity } from './helpers';
import { ChipList, PanelHeader, Row, Section } from './shared';

interface Props {
  entity: Entity;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function EntityPanel({ entity, data, onNavigate }: Props) {
  const carriedBy = flowsCarryingEntity(data, entity.name);
  const returnedBy = flowsReturningEntity(data, entity.name);
  const tools = toolsTouchingEntity(data, entity.name);

  return (
    <article className="panel panel--entity">
      <PanelHeader kindLabel="entity" name={entity.name} />

      <Section>
        {entity.domain && <Row k="domain">{entity.domain}</Row>}
        <Row k="attributes">{entity.attributes.length}</Row>
        {entity.rule_count > 0 && <Row k="rules">{entity.rule_count}</Row>}
        {entity.metrics.length > 0 && <Row k="metrics">{entity.metrics.join(', ')}</Row>}
      </Section>

      {entity.description && (
        <Section title="description">
          <p className="panel-body">{entity.description}</p>
        </Section>
      )}

      {entity.attributes.length > 0 && (
        <Section title={`slots (${entity.attributes.length})`}>
          <div className="panel-attr-list">
            {entity.attributes.map((a) => (
              <code key={a} className="panel-attr">
                {a}
              </code>
            ))}
          </div>
        </Section>
      )}

      <Section title={`carried by flows (${carriedBy.length})`}>
        <ChipList empty="no flow uses this as a quantum">
          {carriedBy.map((f) => (
            <Chip key={f.name} kind="flow" onClick={() => onNavigate({ kind: 'flow', id: f.name })}>
              {f.name}
            </Chip>
          ))}
        </ChipList>
      </Section>

      {returnedBy.length > 0 && (
        <Section title={`returned by flows (${returnedBy.length})`}>
          <ChipList>
            {returnedBy.map((f) => (
              <Chip key={f.name} kind="flow" onClick={() => onNavigate({ kind: 'flow', id: f.name })}>
                {f.name}
              </Chip>
            ))}
          </ChipList>
        </Section>
      )}

      {tools.length > 0 && (
        <Section title={`tool i/o (${tools.length})`}>
          <ChipList>
            {tools.map((t) => (
              <Chip
                key={t.name}
                kind="tool"
                onClick={() => onNavigate({ kind: 'tool', id: t.name })}
                title={t.input_class === entity.name ? 'input' : 'output'}
              >
                {t.name}
              </Chip>
            ))}
          </ChipList>
        </Section>
      )}
    </article>
  );
}
