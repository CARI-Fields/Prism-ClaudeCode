import { useMemo, useState } from 'react';
import { Button, Checkbox, Switch } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useExportDownload } from './useExportDownload';
import { RunFilterBar } from './RunFilterBar';
import { filterRuns } from './filterRuns';
import type { RunFilter } from './filterRuns';

type Dim = 'task' | 'condition' | 'rep';
const EMPTY: RunFilter = { task: [], condition: [], rep: [], query: '' };
const uniqSorted = (xs: string[]): string[] => Array.from(new Set(xs)).sort();

export function RunPicker() {
  const { data } = useData();
  const runs = data?.runs ?? [];
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [includeTexts, setIncludeTexts] = useState(false);
  const [filter, setFilter] = useState<RunFilter>(EMPTY);
  const { download, busy, error } = useExportDownload();

  const domains = useMemo(() => ({
    task: uniqSorted(runs.map((r) => r.task)),
    condition: uniqSorted(runs.map((r) => r.condition)),
    rep: uniqSorted(runs.map((r) => `r${r.rep}`)),
  }), [runs]);
  const visible = useMemo(() => filterRuns(runs, filter), [runs, filter]);

  const toggle = (id: string) =>
    setSelected((s) => { const n = new Set(s); if (n.has(id)) n.delete(id); else n.add(id); return n; });
  const toggleDim = (dim: Dim, token: string) =>
    setFilter((f) => {
      const cur = f[dim];
      return { ...f, [dim]: cur.includes(token) ? cur.filter((x) => x !== token) : [...cur, token] };
    });
  const clearDim = (dim: Dim) => setFilter((f) => ({ ...f, [dim]: [] }));
  const setQuery = (query: string) => setFilter((f) => ({ ...f, query }));

  const visibleIds = visible.map((r) => r.run_id);
  const allVisibleSelected = visible.length > 0 && visibleIds.every((id) => selected.has(id));
  const someVisibleSelected = visibleIds.some((id) => selected.has(id));
  const toggleAllVisible = () =>
    setSelected((s) => {
      const n = new Set(s);
      if (allVisibleSelected) visibleIds.forEach((id) => n.delete(id));
      else visibleIds.forEach((id) => n.add(id));
      return n;
    });
  // Download all selected, in run order (across all filters).
  const orderedSelected = runs.map((r) => r.run_id).filter((id) => selected.has(id));

  return (
    <div className="run-picker">
      <RunFilterBar domains={domains} filter={filter} onToggle={toggleDim} onClear={clearDim} onQuery={setQuery} />
      <div className="run-picker-head">
        <div className="run-picker-selinfo">
          <Checkbox
            checked={allVisibleSelected}
            indeterminate={someVisibleSelected && !allVisibleSelected}
            disabled={visible.length === 0}
            onChange={toggleAllVisible}
            label={`Select all shown (${visible.length})`}
          />
          <span className="run-picker-count">{selected.size} selected</span>
        </div>
        <Switch
          checked={includeTexts}
          onChange={(e) => setIncludeTexts(e.currentTarget.checked)}
          label="Include raw context text"
          aria-label="Include raw context text"
        />
      </div>
      <div className="run-picker-list">
        {visible.length === 0 && <p className="run-picker-empty">No runs match</p>}
        {visible.map((r) => (
          <Checkbox
            key={r.run_id}
            checked={selected.has(r.run_id)}
            onChange={() => toggle(r.run_id)}
            label={`${r.task} / ${r.condition} / r${r.rep} · ${r.run_id}`}
          />
        ))}
      </div>
      {error && <p className="run-picker-error">{error}</p>}
      <Button
        intent="primary"
        icon="download"
        loading={busy}
        disabled={orderedSelected.length === 0}
        text={`Download ${orderedSelected.length || ''} ${orderedSelected.length === 1 ? 'trace' : 'traces'}`.replace('  ', ' ').trim()}
        onClick={() => download(orderedSelected, includeTexts)}
      />
    </div>
  );
}
