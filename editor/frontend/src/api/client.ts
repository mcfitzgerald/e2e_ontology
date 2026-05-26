import type { DiffPayload, GitStatus, OntologyPayload } from './types';

export class ApiError extends Error {
  status: number;
  constructor(message: string, status: number) {
    super(message);
    this.name = 'ApiError';
    this.status = status;
  }
}

async function get<T>(url: string): Promise<T> {
  const res = await fetch(url);
  if (!res.ok) {
    let detail = `${res.status} ${res.statusText}`;
    try {
      const body = (await res.json()) as { detail?: string };
      if (body.detail) detail = body.detail;
    } catch {
      /* no JSON body */
    }
    throw new ApiError(detail, res.status);
  }
  return (await res.json()) as T;
}

export const fetchOntology = (): Promise<OntologyPayload> => get<OntologyPayload>('/api/ontology');

export const fetchDiff = (base = 'HEAD'): Promise<DiffPayload> =>
  get<DiffPayload>(`/api/diff?base=${encodeURIComponent(base)}`);

export const fetchGitStatus = (): Promise<GitStatus> => get<GitStatus>('/api/git-status');
