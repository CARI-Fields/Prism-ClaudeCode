import type { ReactNode } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { AppStateProvider } from './state/AppStateProvider';
import { AppShell } from './components/shell/AppShell';
import { FilterRail } from './components/shell/FilterRail';
import { ViewNav } from './components/shell/ViewNav';
import { ViewCanvas } from './components/shell/ViewCanvas';
import { OverviewView } from './views/OverviewView';
import { Section1View } from './views/Section1View';
import { Section2View } from './views/Section2View';
import { Section3View } from './views/Section3View';
import type { ViewKey } from './types';

function Dashboard() {
  const { data } = useData();
  if (!data) return null;
  const views: Record<ViewKey, ReactNode> = {
    overview: <OverviewView />, s1: <Section1View />, s2: <Section2View />, s3: <Section3View />,
  };
  return (
    <AppStateProvider manifest={data.manifest}>
      <AppShell manifest={data.manifest} sidebar={<FilterRail />}
        canvas={<><ViewNav /><ViewCanvas views={views} /></>} />
    </AppStateProvider>
  );
}
function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <div className="app-root"><p className="bp5-running-text" style={{ padding: 24 }}>Loading…</p></div>;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error') return <div className="app-root"><p style={{ padding: 24 }}>Failed to load: {error}</p></div>;
  if (status === 'ready' && data) return <Dashboard />;
  return null;
}
export default function App() { return <DataProvider><Gate /></DataProvider>; }
