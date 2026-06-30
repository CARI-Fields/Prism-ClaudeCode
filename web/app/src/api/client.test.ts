import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest';
import { ApiError, apiGet, getManifest } from './client';
import { setToken } from './token';

function mockFetch(status: number, body: unknown) {
  return vi
    .fn()
    .mockResolvedValue({ status, ok: status >= 200 && status < 300, json: async () => body });
}

describe('apiGet', () => {
  beforeEach(() => {
    localStorage.clear();
  });
  afterEach(() => {
    vi.unstubAllGlobals();
  });

  it('sends the bearer token and returns json', async () => {
    setToken('secret123');
    const fetchMock = mockFetch(200, [{ run_id: 'r1' }]);
    vi.stubGlobal('fetch', fetchMock);
    const data = await apiGet<{ run_id: string }[]>('/api/runs');
    expect(data).toEqual([{ run_id: 'r1' }]);
    const [, opts] = fetchMock.mock.calls[0];
    expect(opts.headers.Authorization).toBe('Bearer secret123');
  });
  it('throws ApiError(401) on unauthorized', async () => {
    vi.stubGlobal('fetch', mockFetch(401, {}));
    await expect(getManifest()).rejects.toMatchObject({ name: 'ApiError', status: 401 });
  });
  it('throws ApiError on other non-ok status', async () => {
    vi.stubGlobal('fetch', mockFetch(500, {}));
    await expect(apiGet('/api/runs')).rejects.toBeInstanceOf(ApiError);
  });
});
