import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { Masthead } from './components/Masthead';
import { GlobalTaskStrip } from './components/GlobalTaskStrip';
import { parseHash, toHash } from './state/urlState';
import { clearTask, initState, setReport, toggleTask } from './state/appState';
import { BriefBand } from './components/BriefBand';
import { KpiBand } from './components/KpiBand';
import { scopeRuns } from './data/filters';
import type { AppState, Manifest, Run } from './types';

function firstVariantKey(manifest: Manifest, fromUrl: string | null): string {
  if (fromUrl && manifest.variants.some((v) => v.key === fromUrl)) return fromUrl;
  return manifest.variants[0]?.key ?? '';
}

function Dashboard({ manifest, runs }: { manifest: Manifest; runs: Run[] }) {
  const [state, setState] = useState<AppState>(() => {
    const url = parseHash(window.location.hash);
    return initState(firstVariantKey(manifest, url.report), url.task);
  });

  // Sync report + task to the URL hash.
  useEffect(() => {
    const next = toHash({ report: state.report, task: state.task });
    if (next !== window.location.hash) window.history.replaceState(null, '', next || window.location.pathname);
  }, [state.report, state.task]);

  useEffect(() => {
    const onHash = () => {
      const url = parseHash(window.location.hash);
      setState((s) => (url.report && url.report !== s.report ? initState(url.report, url.task) : { ...s, task: url.task }));
    };
    window.addEventListener('hashchange', onHash);
    return () => window.removeEventListener('hashchange', onHash);
  }, []);

  const variant = useMemo(
    () => manifest.variants.find((v) => v.key === state.report) ?? manifest.variants[0],
    [manifest, state.report],
  );
  const onSwitch = useCallback((key: string) => setState((s) => setReport(s, key)), []);

  if (!variant) return null;
  return (
    <>
      <Masthead manifest={manifest} activeKey={variant.key} onSwitch={onSwitch} />
      <main>
        <GlobalTaskStrip
          tasks={variant.tasks}
          selected={state.task}
          onToggle={(t) => setState((s) => toggleTask(s, t))}
          onClear={() => setState((s) => clearTask(s))}
        />
        <BriefBand variant={variant} manifest={manifest} />
        <KpiBand runs={scopeRuns(runs, state.task, { condition: [], rep: [], agent: [] })} />
        {/* §1/§2/§3 → Task 8 */}
      </main>
    </>
  );
}

function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <main><p className="note">Loading…</p></main>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <main><p className="note">Failed to load: {error}</p></main>;
  if (status === 'ready' && data) return <Dashboard manifest={data.manifest} runs={data.runs} />;
  return null;
}

export default function App() {
  return (
    <DataProvider>
      <Gate />
    </DataProvider>
  );
}
