import { Alignment, Button, Navbar } from '@blueprintjs/core';
import type { KeyboardEvent } from 'react';
import type { Manifest } from '../../types';
import { useReport, useTheme } from '../../state/AppStateProvider';
import { useData } from '../../data/DataContext';
import { ExportControl } from '../../export/ExportControl';

// Enter / Space activate a role="tab" element (native button behavior for the
// non-button segments of the report switch).
function activate(fn: () => void) {
  return (e: KeyboardEvent) => {
    if (e.key === 'Enter' || e.key === ' ') {
      e.preventDefault();
      fn();
    }
  };
}

export function TopBar({ manifest }: { manifest: Manifest }) {
  const { report, setReport } = useReport();
  const { mode, toggle } = useTheme();
  const { reload } = useData();
  const variants = manifest.variants;
  const activeIdx = Math.max(
    0,
    variants.findIndex((v) => v.key === report),
  );
  const themeAria = `Switch to ${mode === 'dark' ? 'light' : 'dark'} theme`;
  return (
    <Navbar className="app-topbar">
      <Navbar.Group align={Alignment.LEFT}>
        <Navbar.Heading>CC Orchestration Report</Navbar.Heading>
      </Navbar.Group>
      {variants.length > 1 && (
        <div className="topbar-variants" role="group" aria-label="Report">
          {/* A single capsule thumb glides between equal-width segments. Replaces
              Blueprint's sliding underline with a Foundry-style segmented control. */}
          <div className="bp5-tab-list seg-track" role="tablist">
            <span
              className="seg-thumb"
              aria-hidden
              style={{
                width: `calc((100% - 6px) / ${variants.length})`,
                transform: `translateX(${activeIdx * 100}%)`,
              }}
            />
            {variants.map((v) => {
              const selected = v.key === report;
              return (
                <div
                  key={v.key}
                  className="bp5-tab seg-opt"
                  role="tab"
                  tabIndex={0}
                  aria-selected={selected}
                  onClick={() => setReport(v.key)}
                  onKeyDown={activate(() => setReport(v.key))}
                >
                  {v.title}
                </div>
              );
            })}
          </div>
        </div>
      )}
      <Navbar.Group align={Alignment.RIGHT}>
        <ExportControl />
        <Navbar.Divider />
        <Button
          minimal
          className="topbar-icon-btn"
          onClick={toggle}
          aria-label={themeAria}
          title={themeAria}
        >
          {mode === 'dark' ? '☾' : '☀'}
        </Button>
        <Button
          minimal
          className="topbar-icon-btn"
          onClick={reload}
          aria-label="Reload data"
          title="Reload data"
        >
          {'↻'}
        </Button>
      </Navbar.Group>
    </Navbar>
  );
}
