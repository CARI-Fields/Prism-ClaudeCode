import { Alignment, Button, Navbar, Switch, Tab, Tabs } from '@blueprintjs/core';
import type { Manifest } from '../../types';
import { useReport, useTheme } from '../../state/AppStateProvider';
import { useData } from '../../data/DataContext';

export function TopBar({ manifest }: { manifest: Manifest }) {
  const { report, setReport } = useReport();
  const { mode, toggle } = useTheme();
  const { reload } = useData();
  return (
    <Navbar className="app-topbar">
      <Navbar.Group align={Alignment.LEFT}>
        <Navbar.Heading>CC Orchestration Report</Navbar.Heading>
        {manifest.variants.length > 1 && (
          <Tabs id="variant" selectedTabId={report} onChange={(id) => setReport(String(id))} animate>
            {manifest.variants.map((v) => <Tab key={v.key} id={v.key} title={v.title} />)}
          </Tabs>
        )}
      </Navbar.Group>
      <Navbar.Group align={Alignment.RIGHT}>
        <Switch
          checked={mode === 'dark'}
          onChange={toggle}
          label={mode === 'dark' ? '☾ Dark' : '☀ Light'}
          aria-label="Toggle dark theme"
          style={{ margin: 0 }}
        />
        <Navbar.Divider />
        <Button minimal icon="refresh" aria-label="Reload data" onClick={reload} />
      </Navbar.Group>
    </Navbar>
  );
}
