import type { OntologyPayload } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { flowOwningAxiom } from './helpers';
import { HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  axiomName: string;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

export function AxiomPanel({ axiomName, data, onNavigate }: Props) {
  const owned = flowOwningAxiom(data, axiomName);
  if (!owned) {
    return (
      <article className="panel panel--axiom panel--notfound">
        <PanelHeader kindLabel="axiom" name={axiomName} />
        <p className="panel-body">Axiom not found on any flow.</p>
      </article>
    );
  }
  const { flow, axiom } = owned;

  return (
    <article className="panel panel--axiom">
      <PanelHeader
        kindLabel={`axiom${axiom.severity ? ` · ${axiom.severity}` : ''}`}
        name={axiom.name}
        extra={
          axiom.severity && (
            <span className={`axiom-sev-pill axiom-sev-pill--${axiom.severity}`} aria-hidden />
          )
        }
      />

      <HintBlock label="natural language (authoritative)">{axiom.nl}</HintBlock>

      <Section>
        {axiom.scope && <Row k="scope">{axiom.scope}</Row>}
        {axiom.severity && <Row k="severity">{axiom.severity}</Row>}
        <Row k="on flow">
          <Chip kind="flow" onClick={() => onNavigate({ kind: 'flow', id: flow.name })}>
            {flow.name}
          </Chip>
        </Row>
        {axiom.on_failure_route_to && (
          <Row k="route on fail">
            <Chip kind="flow" onClick={() => onNavigate({ kind: 'flow', id: axiom.on_failure_route_to! })}>
              {axiom.on_failure_route_to}
            </Chip>
          </Row>
        )}
      </Section>

      {axiom.expr && (
        <Section title="expression (semi-symbolic)">
          <pre className="panel-expr">{axiom.expr}</pre>
        </Section>
      )}

      {axiom.message && (
        <Section title="violation message">
          <p className="panel-body">{axiom.message}</p>
        </Section>
      )}
    </article>
  );
}
