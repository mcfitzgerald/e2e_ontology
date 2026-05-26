/*
 * Flow-kind stroke specs. Extracted from mockup's FlowGlyph() component
 * and edge drawing rules. The mockup encodes three conservation laws
 * through stroke weight + dash + color:
 *
 *   material    — earth-tone, heavy, solid  (mass-conserving)
 *   information — cool blue, light, dashed  (copyable)
 *   cash        — gold, doubled parallel    (value-conserving)
 */

export type FlowKind = 'material' | 'information' | 'cash';

export interface FlowStyle {
  color: string;
  strokeWidth: number;
  dashArray?: string;
  doubled?: boolean;
  arrowMarker: string;
}

export const FLOW_STYLES: Record<FlowKind, FlowStyle> = {
  material: {
    color: '#5a3b22',
    strokeWidth: 3.2,
    arrowMarker: 'url(#arrow-material)',
  },
  information: {
    color: '#3b6a96',
    strokeWidth: 1.4,
    dashArray: '5 3',
    arrowMarker: 'url(#arrow-information)',
  },
  cash: {
    color: '#b78d2a',
    strokeWidth: 1.4,
    doubled: true,
    arrowMarker: 'url(#arrow-cash)',
  },
};

export type AxiomSeverity = 'blocking' | 'warning' | 'advisory';

export const AXIOM_COLORS: Record<AxiomSeverity, string> = {
  blocking: '#c04a3a',
  warning: '#d49a2a',
  advisory: '#8a8070',
};

export type DiffState = 'added' | 'changed' | 'removed';

export const DIFF_COLORS: Record<DiffState, string> = {
  added: '#4b8a4a',
  changed: '#c9a227',
  removed: '#b24a3a',
};
