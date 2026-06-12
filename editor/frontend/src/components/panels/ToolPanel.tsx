import type { OntologyPayload, Tool } from '../../api/types';
import type { Selection } from '../../store/ontology';
import { Chip } from '../Chip';
import { hasEntity, roleByName } from './helpers';
import { ChipList, HintBlock, PanelHeader, Row, Section } from './shared';

interface Props {
  tool: Tool;
  data: OntologyPayload;
  onNavigate: (sel: Selection) => void;
}

/**
 * Tool detail. A Tool is a declared deterministic service the orchestrator
 * wires and an agent invokes via `call_tool` — either a `reader` (reads world
 * state, no side effects) or a `compute` (pure function). `implementation` is
 * a contract name the orchestrator binds to a Python callable at boot; it does
 * not resolve to anything in the ontology. `available_to` is the capability
 * surface the role-view renderer filters on (agent_system_design.md §6.2).
 */
export function ToolPanel({ tool, data, onNavigate }: Props) {
  const kindLabel = tool.category ? `${tool.category} tool` : 'tool';

  const classCell = (name: string) =>
    hasEntity(data, name) ? (
      <Chip kind="entity" onClick={() => onNavigate({ kind: 'entity', id: name })}>
        {name}
      </Chip>
    ) : (
      <span className="panel-muted">{name}</span>
    );

  return (
    <article className="panel panel--tool">
      <PanelHeader kindLabel={kindLabel} name={tool.name} />

      <Section>
        {tool.category && <Row k="category">{tool.category}</Row>}
        <Row k="input">{classCell(tool.input_class)}</Row>
        <Row k="output">{classCell(tool.output_class)}</Row>
        <Row k="impl">
          <code className="panel-mono">{tool.implementation}</code>
        </Row>
        {tool.deterministic != null && <Row k="deterministic">{String(tool.deterministic)}</Row>}
        {tool.domain && <Row k="domain">{tool.domain}</Row>}
      </Section>

      {tool.description && (
        <Section title="description">
          <p className="panel-body">{tool.description}</p>
        </Section>
      )}

      <Section title={`available to (${tool.available_to.length})`}>
        <ChipList empty="no roles">
          {tool.available_to.map((roleName) => {
            const r = roleByName(data, roleName);
            return (
              <Chip
                key={roleName}
                kind="role"
                boundary={r?.is_boundary}
                onClick={() => onNavigate({ kind: 'role', id: roleName })}
              >
                {roleName}
              </Chip>
            );
          })}
        </ChipList>
      </Section>

      {tool.llm_prompt_hint && (
        <HintBlock label="llm context">{tool.llm_prompt_hint}</HintBlock>
      )}
    </article>
  );
}
