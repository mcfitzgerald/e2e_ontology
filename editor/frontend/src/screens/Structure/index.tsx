import type { OntologyPayload } from '../../api/types';
import { Legend } from './Legend';
import { SwimlaneGraph } from './SwimlaneGraph';
import './Structure.css';

interface Props {
  data: OntologyPayload;
}

export function StructureScreen({ data }: Props) {
  return (
    <section className="structure">
      <div className="structure-canvas">
        <SwimlaneGraph data={data} />
        <Legend />
      </div>
    </section>
  );
}
