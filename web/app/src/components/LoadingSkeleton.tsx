import { parseHash } from '../state/urlState';
import { resolveThemeMode } from '../state/themeMode';

// Canvas-area placeholder shown while a lazily-loaded view chunk is in flight
// (the shell, rail and nav are already painted around it).
export function ViewSkeleton() {
  return (
    <div className="view view-stack" aria-busy="true" aria-label="Loading view">
      {[0, 1].map((i) => (
        <div className="panel-card skel-card" key={i}>
          <span className="skel skel-line" style={{ width: '38%', marginBottom: 14 }} />
          <span className="skel skel-chart" />
        </div>
      ))}
    </div>
  );
}

// Layout-matched loading placeholder: mirrors AppShell (top bar + rail + canvas)
// and the Overview view so the first paint already has the report's shape while
// the data bundle is in flight. Theme is resolved up front to avoid a flash.
export function LoadingSkeleton() {
  const dark = resolveThemeMode(parseHash(window.location.hash).theme) === 'dark';
  return (
    <div className={`app-root${dark ? ' bp5-dark' : ''}`}>
      <div
        className="app-shell skeleton-root"
        aria-busy="true"
        aria-live="polite"
        aria-label="Loading report"
      >
        <div className="app-topbar bp5-navbar skel-topbar">
          <span className="skel skel-line" style={{ width: 170 }} />
          <span className="skel-row">
            <span className="skel skel-line" style={{ width: 96 }} />
            <span className="skel skel-line" style={{ width: 96 }} />
          </span>
        </div>
        <div className="app-body">
          <aside className="app-rail">
            <span className="skel skel-line" style={{ width: 64, marginBottom: 14 }} />
            {[0, 1, 2, 3].map((g) => (
              <div className="rail-group" key={g}>
                <span className="skel skel-line skel-rail-head" />
                <div className="rail-chips">
                  {Array.from({ length: g === 3 ? 4 : 3 }).map((_, i) => (
                    <span className="skel skel-chip" key={i} />
                  ))}
                </div>
              </div>
            ))}
          </aside>
          <main className="app-canvas">
            <div className="skel-row skel-nav">
              {Array.from({ length: 4 }).map((_, i) => (
                <span className="skel skel-line" style={{ width: 82 }} key={i} />
              ))}
            </div>
            <div className="kpi-row">
              {Array.from({ length: 5 }).map((_, i) => (
                <div className="kpi-card skel-card" key={i}>
                  <span className="skel skel-line" style={{ width: '55%' }} />
                  <span className="skel skel-line skel-kpi-value" />
                </div>
              ))}
            </div>
            <div className="overview-grid">
              {[0, 1].map((i) => (
                <div className="panel-card skel-card" key={i}>
                  <span className="skel skel-line" style={{ width: '42%', marginBottom: 14 }} />
                  <span className="skel skel-chart" />
                </div>
              ))}
            </div>
          </main>
        </div>
      </div>
    </div>
  );
}
