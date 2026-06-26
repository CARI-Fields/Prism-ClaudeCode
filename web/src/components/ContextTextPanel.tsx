import { useEffect, useState } from 'react';
import { getComponentTexts } from '../api/client';
import type { ComponentText } from '../types';
import { fmt } from '../charts/format';

export interface CtxSelection { component: string; requestIndex: number; type: string; tokens: number }

export function ContextTextPanel({ runId, selection }: { runId: string; selection: CtxSelection | null }) {
  const [texts, setTexts] = useState<ComponentText[] | null>(null);

  useEffect(() => {
    let live = true;
    if (selection && texts === null) {
      getComponentTexts(runId).then((rows) => { if (live) setTexts(rows); }).catch(() => { if (live) setTexts([]); });
    }
    return () => { live = false; };
  }, [selection, runId, texts]);

  if (!selection) {
    return <div className="ctx-text-panel"><div className="ctx-empty">Click a stacked segment above to view the text captured for that context part.</div></div>;
  }
  const lookup = new Map<string, ComponentText>();
  for (const r of texts ?? []) {
    lookup.set(r.stable ? `${r.run_id}|*|${r.component}` : `${r.run_id}|${r.request_index}|${r.component}`, r);
  }
  const entry = lookup.get(`${runId}|${selection.requestIndex}|${selection.component}`) ?? lookup.get(`${runId}|*|${selection.component}`);
  return (
    <div className="ctx-text-panel">
      <div className="ctx-head">
        <b>{selection.component}</b>
        <span>request #{selection.requestIndex + 1}</span>
        <span>{selection.type}</span>
        <span>{fmt(selection.tokens)} est tokens</span>
        {entry && <span>{fmt(entry.bytes)} bytes{entry.truncated ? <span className="ctx-trunc"> &middot; preview truncated</span> : null}</span>}
      </div>
      {entry && entry.text
        ? <pre className="ctx-body">{entry.text}</pre>
        : <div className="ctx-empty">{texts === null ? 'Loading…' : 'No captured text for this part (it may be externalized or empty).'}</div>}
    </div>
  );
}
