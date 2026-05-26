/*
 * Domain presentation config. Ordered top-to-bottom as the mockup's
 * swimlane stack. Tints mirror the CSS custom properties in
 * tokens/colors.css; `hand` is the hand-drawn flavor annotation the
 * mockup uses to read the domain's role.
 *
 * This is a UX surface, not ontology truth. If the ontology ever adds
 * new domains, they'll appear via orderedDomains() with default styling
 * and no hand-flavor until this config is updated.
 */

export interface DomainConfig {
  id: string;
  label: string;
  tint: string;
  ink: string;
  hand: string;
}

export const DOMAINS: DomainConfig[] = [
  { id: 'commercial',    label: 'commercial',    tint: 'var(--dom-commercial)',    ink: '#8a4b2e', hand: '~retailers & promos' },
  { id: 'demand',        label: 'demand',        tint: 'var(--dom-demand)',        ink: '#8a6a1e', hand: '~what will sell' },
  { id: 'supply_netops', label: 'supply_netops', tint: 'var(--dom-supply_netops)', ink: '#4f6b2f', hand: '~the hub' },
  { id: 'manufacturing', label: 'manufacturing', tint: 'var(--dom-manufacturing)', ink: '#2f5068', hand: '~making things' },
  { id: 'logistics',     label: 'logistics',     tint: 'var(--dom-logistics)',     ink: '#5a3d78', hand: '~moving things' },
  { id: 'procurement',   label: 'procurement',   tint: 'var(--dom-procurement)',   ink: '#8a4432', hand: '~buying things' },
];

const DOMAIN_INDEX: Record<string, DomainConfig> = Object.fromEntries(
  DOMAINS.map((d) => [d.id, d]),
);

export function domainFor(id: string | null | undefined): DomainConfig | null {
  if (!id) return null;
  return DOMAIN_INDEX[id] ?? null;
}

/**
 * Return the DomainConfig list for the given domains present in the data,
 * in the caller-supplied order. Unknown domain ids get a neutral config
 * appended at the end.
 */
export function orderedDomains(seen: Iterable<string>, preferredOrder: string[]): DomainConfig[] {
  const present = new Set(seen);
  const out: DomainConfig[] = [];
  const emitted = new Set<string>();

  for (const id of preferredOrder) {
    if (present.has(id) && !emitted.has(id)) {
      out.push(DOMAIN_INDEX[id] ?? neutralDomain(id));
      emitted.add(id);
    }
  }
  for (const id of present) {
    if (!emitted.has(id)) {
      out.push(DOMAIN_INDEX[id] ?? neutralDomain(id));
      emitted.add(id);
    }
  }
  return out;
}

function neutralDomain(id: string): DomainConfig {
  return { id, label: id, tint: 'var(--paper-dark)', ink: '#1a1a1a', hand: '' };
}
