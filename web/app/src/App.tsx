import { useCallback, useEffect, useMemo, useState } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { Masthead } from './components/Masthead';
import { GlobalTaskStrip } from './components/GlobalTaskStrip';
import { parseHash, toHash } from './state/urlState';
import { clearSection, clearTask, initState, setReport, toggleSection, toggleTask } from './state/appState';
import { BriefBand } from './components/BriefBand';
import { KpiBand } from './components/KpiBand';
import { Section1 } from './components/Section1';
import { Section2 } from './components/Section2';
import { Section3 } from './components/Section3';
import { presentAgentTypes, scopeRuns, scopeTurns } from './data/filters';
import type { AppState, Component, Manifest, Run, Turn } from './types';

function firstVariantKey(manifest: Manifest, fromUrl: string | null): string {
  if (fromUrl && manifest.variants.some((v) => v.key === fromUrl)) return fromUrl;
  return manifest.variants[0]?.key ?? '';
}

function Dashboard({ manifest, runs, turns, components }: { manifest: Manifest; runs: Run[]; turns: Turn[]; components: Component[] }) {
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

  const variantRuns = useMemo(
    () => runs.filter((r) => variant && variant.tasks.includes(r.task) && variant.conditions.includes(r.condition)),
    [runs, variant],
  );
  const reps = useMemo(() => Array.from(new Set(variantRuns.map((r) => `r${r.rep}`))).sort(), [variantRuns]);
  // Agent chip lists ignore the section's own agent selection, so picking one agent
  // doesn't hide the others (matches the report's stable agent chips).
  const agents2 = useMemo(() => presentAgentTypes(scopeTurns(turns, state.task, { ...state.s2, agent: [] })), [turns, state.task, state.s2]);
  const agents3 = useMemo(() => presentAgentTypes(scopeTurns(turns, state.task, { ...state.s3, agent: [] })), [turns, state.task, state.s3]);
  const sectionToggle = useCallback(
    (scope: 's1' | 's2' | 's3') => (dim: 'condition' | 'rep' | 'agent', token: string) =>
      setState((s) => toggleSection(s, scope, dim, token)),
    [],
  );
  const sectionClear = useCallback(
    (scope: 's1' | 's2' | 's3') => (dim: 'condition' | 'rep' | 'agent') =>
      setState((s) => clearSection(s, scope, dim)),
    [],
  );

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
        <Section1 variant={variant} state={state} runs={scopeRuns(runs, state.task, { condition: [], rep: [], agent: [] })} onToggle={sectionToggle('s1')} onClear={sectionClear('s1')} />
        <Section2 variant={variant} state={state} turns={scopeTurns(turns, state.task, state.s2)} reps={reps} agentTypes={agents2} onToggle={sectionToggle('s2')} onClear={sectionClear('s2')} />
        <Section3 variant={variant} state={state} runs={scopeRuns(runs, state.task, state.s3)} turns={scopeTurns(turns, state.task, state.s3)} reps={reps} agentTypes={agents3} components={components} onToggle={sectionToggle('s3')} onClear={sectionClear('s3')} />
      </main>
    </>
  );
}

function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <main><p className="note">Loading…</p></main>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <main><p className="note">Failed to load: {error}</p></main>;
  if (status === 'ready' && data) return <Dashboard manifest={data.manifest} runs={data.runs} turns={data.turns} components={data.components} />;
  return null;
}

export default function App() {
  return (
    <DataProvider>
      <Gate />
    </DataProvider>
  );
}
