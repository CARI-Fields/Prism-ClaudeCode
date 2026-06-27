import { InputGroup } from '@blueprintjs/core';
import { RailFilterGroup } from '../components/shell/RailFilterGroup';
import { conditionColor } from '../theme';
import type { RunFilter } from './filterRuns';

type Dim = 'task' | 'condition' | 'rep';

interface Props {
  domains: { task: string[]; condition: string[]; rep: string[] };
  filter: RunFilter;
  onToggle: (dim: Dim, token: string) => void;
  onClear: (dim: Dim) => void;
  onQuery: (q: string) => void;
}

export function RunFilterBar({ domains, filter, onToggle, onClear, onQuery }: Props) {
  return (
    <div className="run-filter-bar">
      <RailFilterGroup
        label="Task" items={domains.task} active={filter.task}
        onToggle={(t) => onToggle('task', t)} onClear={() => onClear('task')}
      />
      <RailFilterGroup
        label="Feature" items={domains.condition} active={filter.condition} dotFor={conditionColor}
        onToggle={(t) => onToggle('condition', t)} onClear={() => onClear('condition')}
      />
      <RailFilterGroup
        label="Rollout" items={domains.rep} active={filter.rep}
        onToggle={(t) => onToggle('rep', t)} onClear={() => onClear('rep')}
      />
      <InputGroup
        type="search" leftIcon="search" placeholder="Search runs…" aria-label="Search runs"
        value={filter.query} onChange={(e) => onQuery(e.currentTarget.value)}
      />
    </div>
  );
}
