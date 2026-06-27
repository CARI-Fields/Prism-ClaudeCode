import { lazy, Suspense } from 'react';
import type { ReactNode } from 'react';
import { DataProvider, useData } from './data/DataContext';
import { TokenGate } from './components/TokenGate';
import { LoadingSkeleton, ViewSkeleton } from './components/LoadingSkeleton';
import { AppStateProvider } from './state/AppStateProvider';
import { AppShell } from './components/shell/AppShell';
import { FilterRail } from './components/shell/FilterRail';
import { ViewNav } from './components/shell/ViewNav';
import { ViewCanvas } from './components/shell/ViewCanvas';
import type { ViewKey } from './types';

// Views (and their heavy ECharts dependency) are code-split: only the active
// view's chunk loads, so the initial bundle stays small and the shell paints fast.
const OverviewView = lazy(() =>
  import('./views/OverviewView').then((m) => ({ default: m.OverviewView })),
);
const Section1View = lazy(() =>
  import('./views/Section1View').then((m) => ({ default: m.Section1View })),
);
const Section2View = lazy(() =>
  import('./views/Section2View').then((m) => ({ default: m.Section2View })),
);
const Section3View = lazy(() =>
  import('./views/Section3View').then((m) => ({ default: m.Section3View })),
);

function Dashboard() {
  const { data } = useData();
  if (!data) return null;
  const views: Record<ViewKey, ReactNode> = {
    overview: <OverviewView />,
    s1: <Section1View />,
    s2: <Section2View />,
    s3: <Section3View />,
  };
  return (
    <AppStateProvider manifest={data.manifest}>
      <AppShell
        manifest={data.manifest}
        sidebar={<FilterRail />}
        canvas={
          <>
            <ViewNav />
            <Suspense fallback={<ViewSkeleton />}>
              <ViewCanvas views={views} />
            </Suspense>
          </>
        }
      />
    </AppStateProvider>
  );
}
function Gate() {
  const { status, data, error } = useData();
  if (status === 'loading') return <LoadingSkeleton />;
  if (status === 'need-token') return <TokenGate />;
  if (status === 'error')
    return (
      <div className="app-root">
        <p style={{ padding: 24 }}>Failed to load: {error}</p>
      </div>
    );
  if (status === 'ready' && data) return <Dashboard />;
  return null;
}
export default function App() {
  return (
    <DataProvider>
      <Gate />
    </DataProvider>
  );
}
