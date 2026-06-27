import { describe, expect, it } from 'vitest';
import type { Run, SectionSel, Turn } from '../types';
import { inVariantRuns, inVariantTurns, presentAgentTypes, scopeRuns, scopeTurns } from './filters';

const runs = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1 },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2 },
  { run_id: 'c', task: 'research', condition: 'single_agent', rep: 1 },
] as unknown as Run[];
const turns = [
  { run_id: 'a', task: 'coding', condition: 'single_agent', rep: 1, request_type: 'main-agent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: 'task-subagent' },
  { run_id: 'b', task: 'coding', condition: 'subagents', rep: 2, request_type: null },
] as unknown as Turn[];
const sec = (o: Partial<SectionSel>): SectionSel => ({ condition: [], rep: [], agent: [], ...o });

describe('filters', () => {
  it('empty section + empty task returns all', () => {
    expect(scopeRuns(runs, [], sec({}))).toHaveLength(3);
  });
  it('global task + section condition narrow runs', () => {
    expect(scopeRuns(runs, ['coding'], sec({ condition: ['subagents'] })).map((r) => r.run_id)).toEqual(['b']);
  });
  it('rep matches r-prefixed token', () => {
    expect(scopeRuns(runs, [], sec({ rep: ['r1'] })).map((r) => r.run_id)).toEqual(['a', 'c']);
  });
  it('scopeTurns filters by agent and drops null when agent set', () => {
    expect(scopeTurns(turns, [], sec({ agent: ['task-subagent'] })).map((t) => t.run_id)).toEqual(['b']);
  });
  it('presentAgentTypes returns sorted distinct non-null', () => {
    expect(presentAgentTypes(turns)).toEqual(['main-agent', 'task-subagent']);
  });

  // Bug: the two variants share the dynamic_workflow condition, so filtering by
  // user selection alone leaked the other variant's runs into a view.
  it('inVariantRuns keeps only rows whose task AND condition belong to the variant', () => {
    const mixed = [
      { run_id: 'm', task: 'coding', condition: 'dynamic_workflow', rep: 1 },          // multi-agent
      { run_id: 'l', task: 'coding_longhorizon', condition: 'dynamic_workflow', rep: 1 }, // long-horizon (shared condition)
      { run_id: 'x', task: 'coding_longhorizon', condition: 'single_agent', rep: 1 },   // wrong condition for long-horizon
    ] as unknown as Run[];
    const lh = { tasks: ['coding_longhorizon', 'research_longhorizon'], conditions: ['goal', 'ralph_loop', 'dynamic_workflow'] };
    expect(inVariantRuns(mixed, lh).map((r) => r.run_id)).toEqual(['l']);
  });
  it('inVariantTurns scopes turns to the variant the same way', () => {
    const mixed = [
      { run_id: 'm', task: 'coding', condition: 'dynamic_workflow', rep: 1 },
      { run_id: 'l', task: 'coding_longhorizon', condition: 'goal', rep: 1 },
    ] as unknown as Turn[];
    const lh = { tasks: ['coding_longhorizon'], conditions: ['goal', 'dynamic_workflow'] };
    expect(inVariantTurns(mixed, lh).map((t) => t.run_id)).toEqual(['l']);
  });
});
