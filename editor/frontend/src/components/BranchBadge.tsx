import { useDiff } from '../store/diff';

/**
 * Top-bar diff summary. Layout from mockup line 2575:
 *   branch: <feat/x> · +N ~M -K
 *
 * Degrades when git-status is unavailable (detached HEAD, non-git checkout):
 * shows just "no git" instead of the branch slot. Diff counts hide the
 * "−K" segment when there are no removals to keep the badge tight.
 */
export function BranchBadge() {
  const gitStatus = useDiff((s) => s.gitStatus);
  const diff = useDiff((s) => s.diff);
  const loading = useDiff((s) => s.loading);

  const summary = diff?.summary;
  const branchLabel = gitStatus?.branch_label ?? null;
  const headShort = gitStatus?.head_short;

  const tip = buildTooltip(diff?.base, diff?.base_resolved, gitStatus?.dirty);

  return (
    <div className="branch-badge" title={tip}>
      {branchLabel ? (
        <>
          <span className="branch-badge-key">branch:</span>{' '}
          <b>{branchLabel}</b>
          {headShort && branchLabel !== `detached@${headShort}` && (
            <span className="branch-badge-sha"> @{headShort}</span>
          )}
        </>
      ) : (
        <span className="branch-badge-key">{loading ? 'loading…' : 'no git'}</span>
      )}
      {summary && (summary.added || summary.changed || summary.removed) ? (
        <>
          {' · '}
          <span className="diff-count">
            {summary.added > 0 && <span className="diff-add">+{summary.added}</span>}
            {summary.changed > 0 && (
              <span className="diff-change">
                {summary.added > 0 ? ' ' : ''}~{summary.changed}
              </span>
            )}
            {summary.removed > 0 && (
              <span className="diff-remove">
                {summary.added > 0 || summary.changed > 0 ? ' ' : ''}-{summary.removed}
              </span>
            )}
          </span>
        </>
      ) : (
        diff && <span className="diff-count diff-clean"> · clean</span>
      )}
    </div>
  );
}

function buildTooltip(base: string | undefined, resolved: string | null | undefined, dirty: boolean | null | undefined): string {
  const parts: string[] = [];
  if (base) {
    parts.push(resolved ? `base: ${base} (${resolved})` : `base: ${base}`);
  }
  if (dirty != null) parts.push(dirty ? 'working tree dirty' : 'working tree clean');
  return parts.join(' · ');
}
