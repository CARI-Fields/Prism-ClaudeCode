import type { ReactNode } from 'react';
import { useView } from '../../state/AppStateProvider';
import type { ViewKey } from '../../types';
import { ScopeNote } from './ScopeNote';

export function ViewCanvas({ views }: { views: Record<ViewKey, ReactNode> }) {
  const { view } = useView();
  return <div className="view-canvas"><ScopeNote />{views[view]}</div>;
}
