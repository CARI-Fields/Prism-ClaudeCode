import type { ReactNode } from 'react';
import type { Manifest } from '../../types';
import { TopBar } from './TopBar';

export function AppShell({
  manifest,
  sidebar,
  canvas,
}: {
  manifest: Manifest;
  sidebar: ReactNode;
  canvas: ReactNode;
}) {
  return (
    <div className="app-shell">
      <TopBar manifest={manifest} />
      <div className="app-body">
        <aside className="app-rail">{sidebar}</aside>
        <main className="app-canvas">{canvas}</main>
      </div>
    </div>
  );
}
