import { FilterChunk } from './FilterChunk';

interface Props { tasks: string[]; selected: string[]; onToggle: (t: string) => void; onClear: () => void; }
export function GlobalTaskStrip({ tasks, selected, onToggle, onClear }: Props) {
  return (
    <div className="fstrip fstrip-global">
      <FilterChunk tag="Task" items={tasks} active={selected} onToggle={onToggle} onClear={onClear} />
    </div>
  );
}
