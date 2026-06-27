import { afterEach, describe, expect, it, vi } from 'vitest';
import { act, renderHook } from '@testing-library/react';
import { useExportDownload } from './useExportDownload';
import * as client from '../api/client';

afterEach(() => vi.restoreAllMocks());

describe('useExportDownload', () => {
  it('downloads a blob: fetch → object URL → anchor click, toggling busy', async () => {
    const blob = new Blob(['zip']);
    vi.spyOn(client, 'fetchExport').mockResolvedValue(blob);
    vi.stubGlobal('URL', { createObjectURL: vi.fn(() => 'blob:x'), revokeObjectURL: vi.fn() });
    const click = vi.fn();
    const origCreate = document.createElement.bind(document);
    vi.spyOn(document, 'createElement').mockImplementation((tag: string) =>
      tag === 'a'
        ? ({ href: '', download: '', click, remove: vi.fn() } as unknown as HTMLAnchorElement)
        : origCreate(tag),
    );
    vi.spyOn(document.body, 'appendChild').mockImplementation((n) => n);

    const { result } = renderHook(() => useExportDownload());
    await act(async () => { await result.current.download(['r1'], false); });

    expect(client.fetchExport).toHaveBeenCalledWith(['r1'], false);
    expect(click).toHaveBeenCalled();
    expect(result.current.busy).toBe(false);
    expect(result.current.error).toBeNull();
  });
});
