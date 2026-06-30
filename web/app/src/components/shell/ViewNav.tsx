import { Tab, Tabs } from '@blueprintjs/core';
import { useView } from '../../state/AppStateProvider';
import type { ViewKey } from '../../types';

const TABS: { id: ViewKey; title: string }[] = [
  { id: 'overview', title: 'Overview' },
  { id: 's1', title: '§1 Averages' },
  { id: 's2', title: '§2 Distributions' },
  { id: 's3', title: '§3 Single run' },
];
export function ViewNav() {
  const { view, setView } = useView();
  return (
    <Tabs
      id="view-nav"
      large
      selectedTabId={view}
      onChange={(id) => setView(id as ViewKey)}
      className="view-nav"
    >
      {TABS.map((t) => (
        <Tab key={t.id} id={t.id} title={t.title} />
      ))}
    </Tabs>
  );
}
