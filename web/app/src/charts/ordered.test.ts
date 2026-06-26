import { describe, expect, it } from 'vitest';
import { orderedRequests } from './ordered';
import { AGENT_TYPE_ORDER } from './agentSymbols';

describe('orderedRequests', () => {
  const typeByIndex = new Map<number, string>([[0, 'main-agent'], [1, 'task-subagent'], [2, 'main-agent']]);

  it('keeps raw order when groupMode=none', () => {
    const o = orderedRequests(typeByIndex, [0, 1, 2], 'all', 'none', AGENT_TYPE_ORDER);
    expect(o.indexes).toEqual([0, 1, 2]);
    expect(o.grouped).toBe(false);
  });
  it('groups by agent type when groupMode=agent and at=all', () => {
    const o = orderedRequests(typeByIndex, [0, 1, 2], 'all', 'agent', AGENT_TYPE_ORDER);
    expect(o.grouped).toBe(true);
    // main-agent (rank 0) before task-subagent (rank 3): indices 0,2 then 1
    expect(o.indexes).toEqual([0, 2, 1]);
    expect(o.bands.map((b) => b.type)).toEqual(['main-agent', 'task-subagent']);
    expect(o.ordinal).toEqual([1, 2, 1]); // per-band ordinals
  });
});
