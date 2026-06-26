import { createContext, useCallback, useContext, useEffect, useState } from 'react';
import type { ReactNode } from 'react';
import { ApiError, getComponents, getManifest, getRuns, getTokenRates, getTurns } from '../api/client';
import type { Component, Manifest, Run, Turn } from '../types';

export type DataStatus = 'loading' | 'ready' | 'need-token' | 'error';
export interface DataBundle {
  manifest: Manifest; runs: Run[]; turns: Turn[]; components: Component[]; tokenRates: Record<string, number>;
}
interface DataState { status: DataStatus; data: DataBundle | null; error: string | null; reload: () => void; }

const Ctx = createContext<DataState | null>(null);
export function useData(): DataState {
  const v = useContext(Ctx);
  if (!v) throw new Error('useData must be used within a DataProvider');
  return v;
}

export function DataProvider({ children }: { children: ReactNode }) {
  const [status, setStatus] = useState<DataStatus>('loading');
  const [data, setData] = useState<DataBundle | null>(null);
  const [error, setError] = useState<string | null>(null);

  const load = useCallback(async () => {
    setStatus('loading'); setError(null);
    try {
      const [manifest, runs, turns, components, tokenRates] = await Promise.all([
        getManifest(), getRuns(), getTurns(), getComponents(), getTokenRates(),
      ]);
      setData({ manifest, runs, turns, components, tokenRates });
      setStatus('ready');
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) setStatus('need-token');
      else { setError(e instanceof Error ? e.message : String(e)); setStatus('error'); }
    }
  }, []);

  useEffect(() => { void load(); }, [load]);
  return <Ctx.Provider value={{ status, data, error, reload: () => void load() }}>{children}</Ctx.Provider>;
}
