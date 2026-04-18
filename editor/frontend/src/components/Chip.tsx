import type { ReactNode } from 'react';

export type ChipKind = 'role' | 'flow' | 'event' | 'state_machine' | 'entity' | 'axiom';

interface ChipProps {
  kind?: ChipKind;
  boundary?: boolean;
  onClick?: () => void;
  title?: string;
  children: ReactNode;
}

/**
 * Inline pill used inside panels for cross-references. Colored by kind
 * (role/flow/event/fsm/entity); dashed border when the referenced role is
 * a boundary role. Click navigates via the caller-supplied handler.
 */
export function Chip({ kind, boundary, onClick, title, children }: ChipProps) {
  const cls = ['chip'];
  if (kind) cls.push(`chip--${kind}`);
  if (boundary) cls.push('chip--boundary');
  if (onClick) cls.push('chip--clickable');
  return (
    <span
      className={cls.join(' ')}
      onClick={onClick}
      role={onClick ? 'button' : undefined}
      tabIndex={onClick ? 0 : undefined}
      onKeyDown={(e) => {
        if (onClick && (e.key === 'Enter' || e.key === ' ')) {
          e.preventDefault();
          onClick();
        }
      }}
      title={title}
    >
      {children}
    </span>
  );
}
