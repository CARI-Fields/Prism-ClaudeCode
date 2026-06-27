import { useCallback, useState } from 'react';
import { fetchExport } from '../api/client';

export function useExportDownload() {
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const download = useCallback(async (runIds: string[], includeTexts: boolean) => {
    setBusy(true);
    setError(null);
    try {
      const blob = await fetchExport(runIds, includeTexts);
      const url = URL.createObjectURL(blob);
      const a = document.createElement('a');
      a.href = url;
      a.download = 'cc-traces.zip';
      document.body.appendChild(a);
      a.click();
      a.remove();
      URL.revokeObjectURL(url);
    } catch (e) {
      setError(e instanceof Error ? e.message : String(e));
    } finally {
      setBusy(false);
    }
  }, []);
  return { download, busy, error };
}
