import { describe, expect, it } from 'vitest';
import { taskLabel } from './taskLabel';

describe('taskLabel', () => {
  it('strips the _longhorizon suffix', () => {
    expect(taskLabel('coding_longhorizon')).toBe('coding');
    expect(taskLabel('research_longhorizon')).toBe('research');
  });
  it('leaves bare task keys unchanged', () => {
    expect(taskLabel('coding')).toBe('coding');
    expect(taskLabel('research')).toBe('research');
  });
});
