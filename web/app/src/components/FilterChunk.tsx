import { Chip } from './Chip';

interface Props {
  tag: string;
  items: string[];
  active: string[];
  onToggle: (item: string) => void;
  onClear: () => void;
  dotFor?: (item: string) => string | undefined;
}
export function FilterChunk({ tag, items, active, onToggle, onClear, dotFor }: Props) {
  return (
    <div className="fchunk">
      <span className="fchunk-tag">{tag}</span>
      <span className="ftoggle" role="button" tabIndex={0} onClick={onClear}>all</span>
      <div className="chips">
        {items.map((it) => (
          <Chip key={it} label={it} active={active.includes(it)} dot={dotFor?.(it)} onClick={() => onToggle(it)} />
        ))}
      </div>
    </div>
  );
}
