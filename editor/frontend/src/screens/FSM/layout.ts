import dagre from '@dagrejs/dagre';
import type { StateMachine } from '../../api/types';

export const STATE_WIDTH = 180;
export const STATE_HEIGHT = 56;
const GRAPH_PAD_X = 60;
const GRAPH_PAD_Y = 40;

export interface PlacedState {
  name: string;
  x: number;
  y: number;
  isInitial: boolean;
  isTerminal: boolean;
}

export interface FSMLayout {
  states: PlacedState[];
  width: number;
  height: number;
}

/**
 * Horizontal dagre layout for an FSM. States flow left-to-right by default
 * rank; the initial state lands on the left, terminals on the right (when
 * the transition graph permits — dagre is best-effort).
 */
export function computeFsmLayout(fsm: StateMachine): FSMLayout {
  const g = new dagre.graphlib.Graph();
  g.setGraph({
    rankdir: 'LR',
    nodesep: 28,
    ranksep: 100,
    marginx: 24,
    marginy: 24,
  });
  g.setDefaultEdgeLabel(() => ({}));

  for (const s of fsm.states) {
    g.setNode(s, { width: STATE_WIDTH, height: STATE_HEIGHT });
  }
  for (const t of fsm.transitions) {
    if (fsm.states.includes(t.from_state) && fsm.states.includes(t.to_state)) {
      g.setEdge(t.from_state, t.to_state);
    }
  }

  dagre.layout(g);

  const terminalSet = new Set(fsm.terminal);
  const states: PlacedState[] = fsm.states.map((name) => {
    const n = g.node(name);
    return {
      name,
      x: (n?.x ?? 0) + GRAPH_PAD_X,
      y: (n?.y ?? 0) + GRAPH_PAD_Y,
      isInitial: name === fsm.initial,
      isTerminal: terminalSet.has(name),
    };
  });

  const maxX = states.reduce((m, s) => Math.max(m, s.x + STATE_WIDTH / 2), 0);
  const maxY = states.reduce((m, s) => Math.max(m, s.y + STATE_HEIGHT / 2), 0);
  return {
    states,
    width: maxX + GRAPH_PAD_X,
    height: maxY + GRAPH_PAD_Y,
  };
}
