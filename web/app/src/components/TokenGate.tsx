import { useState } from 'react';
import type { FormEvent } from 'react';
import { setToken } from '../api/token';
import { useData } from '../data/DataContext';

export function TokenGate() {
  const { reload } = useData();
  const [value, setValue] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); setToken(value.trim()); reload(); };
  return (
    <main style={{ maxWidth: 'var(--maxw)', margin: '0 auto', padding: '40px 28px' }}>
      <form onSubmit={submit} style={{ maxWidth: 360 }}>
        <p>This dashboard is private. Enter the access token to continue.</p>
        <label className="control">access token
          <input type="password" value={value} onChange={(e) => setValue(e.target.value)} style={{ width: '100%' }} />
        </label>
        <button type="submit" className="sb-reset" style={{ marginTop: 10 }}>Enter</button>
      </form>
    </main>
  );
}
