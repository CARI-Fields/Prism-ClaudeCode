import { useState } from 'react';
import type { FormEvent } from 'react';
import { Button, Card, InputGroup } from '@blueprintjs/core';
import { setToken } from '../api/token';
import { useData } from '../data/DataContext';

export function TokenGate() {
  const { reload } = useData();
  const [value, setValue] = useState('');
  const submit = (e: FormEvent) => { e.preventDefault(); setToken(value.trim()); reload(); };
  return (
    <div className="app-root">
      <div style={{ display: 'flex', justifyContent: 'center', padding: '40px 28px' }}>
        <Card style={{ maxWidth: 360, width: '100%' }}>
          <form onSubmit={submit}>
            <p className="bp5-running-text">This dashboard is private. Enter the access token to continue.</p>
            <label className="bp5-label" htmlFor="token-input">
              access token
              <InputGroup
                id="token-input"
                type="password"
                value={value}
                onChange={(e) => setValue(e.target.value)}
                fill
              />
            </label>
            <div style={{ marginTop: 10 }}>
              <Button type="submit" intent="primary">Enter</Button>
            </div>
          </form>
        </Card>
      </div>
    </div>
  );
}
