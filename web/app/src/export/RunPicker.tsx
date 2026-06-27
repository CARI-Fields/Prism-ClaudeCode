import { useState } from 'react';
import { Button, Checkbox, Switch } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useExportDownload } from './useExportDownload';

export function RunPicker() {
  const { data } = useData();
  const runs = data?.runs ?? [];
  const [selected, setSelected] = useState<Set<string>>(new Set());
  const [includeTexts, setIncludeTexts] = useState(false);
  const { download, busy, error } = useExportDownload();

  const allSelected = runs.length > 0 && selected.size === runs.length;
  const toggle = (id: string) =>
    setSelected((s) => {
      const n = new Set(s);
      if (n.has(id)) n.delete(id); else n.add(id);
      return n;
    });
  const toggleAll = () =>
    setSelected(allSelected ? new Set() : new Set(runs.map((r) => r.run_id)));
  // Download the runs in the order they appear in the list (stable, not Set order).
  const orderedSelected = runs.map((r) => r.run_id).filter((id) => selected.has(id));

  return (
    <div className="run-picker">
      <div className="run-picker-head">
        <Checkbox
          checked={allSelected}
          indeterminate={selected.size > 0 && !allSelected}
          onChange={toggleAll}
          label={`Select all (${runs.length})`}
        />
        <Switch
          checked={includeTexts}
          onChange={(e) => setIncludeTexts(e.currentTarget.checked)}
          label="Include raw context text"
          aria-label="Include raw context text"
        />
      </div>
      <div className="run-picker-list">
        {runs.map((r) => (
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
