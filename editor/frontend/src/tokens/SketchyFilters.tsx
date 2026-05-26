/*
 * Sketchy SVG filter + flow-kind arrow markers. Extracted verbatim from
 * mockup's SketchyFilters() component. Render once at the root so
 * `filter: url(#roughen)` and `markerEnd="url(#arrow-*)"` resolve anywhere.
 */

export function SketchyFilters() {
  return (
    <svg width={0} height={0} style={{ position: 'absolute' }} aria-hidden="true">
      <defs>
        <filter id="roughen" x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="0.9" numOctaves={2} seed={3} result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale={1.4} />
        </filter>
        <filter id="roughen-soft" x="-5%" y="-5%" width="110%" height="110%">
          <feTurbulence type="fractalNoise" baseFrequency="1.6" numOctaves={2} seed={5} result="noise" />
          <feDisplacementMap in="SourceGraphic" in2="noise" scale={0.8} />
        </filter>
        <marker id="arrow-information" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#3b6a96" />
        </marker>
        <marker id="arrow-material" viewBox="0 0 12 12" refX="9" refY="6" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L12,6 L0,12 z" fill="#5a3b22" />
        </marker>
        <marker id="arrow-cash" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="6" markerHeight="6" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#b78d2a" />
        </marker>
        <marker id="arrow-ink" viewBox="0 0 10 10" refX="8" refY="5" markerWidth="7" markerHeight="7" orient="auto">
          <path d="M0,0 L10,5 L0,10 z" fill="#1a1a1a" />
        </marker>
      </defs>
    </svg>
  );
}
