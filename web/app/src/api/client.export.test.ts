import { afterEach, describe, expect, it, vi } from 'vitest';
import { fetchExport } from './client';

afterEach(() => vi.restoreAllMocks());

describe('fetchExport', () => {
  it('requests the export URL with auth + texts flag and returns a Blob', async () => {
    localStorage.setItem('cc_report_token', 'tok');
    const blob = new Blob(['zip']);
    const fetchMock = vi.fn().mockResolvedValue({ ok: true, status: 200, blob: () => Promise.resolve(blob) });
    vi.stubGlobal('fetch', fetchMock);
    const out = await fetchExport(['r1', 'r2'], true);
    expect(out).toBe(blob);
    const [url, opts] = fetchMock.mock.calls[0];
    expect(url).toContain('/api/export?runs=r1,r2&texts=1');
    expect((opts.headers as Record<string, string>).Authorization).toBe('Bearer tok');
  });
  it('throws ApiError on non-ok', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 500 }));
    await expect(fetchExport(['r1'], false)).rejects.toMatchObject({ status: 500 });
  });
  it('throws ApiError(401) on unauthorized', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue({ ok: false, status: 401 }));
    await expect(fetchExport(['r1'], false)).rejects.toMatchObject({ status: 401 });
  });
});
