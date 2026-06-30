import { Button, Tag } from '@blueprintjs/core';

interface Props {
  label: string;
  items: string[];
  active: string[];
  dotFor?: (t: string) => string;
  labelFor?: (t: string) => string;
  onToggle: (t: string) => void;
  onClear: () => void;
}
export function RailFilterGroup({
  label,
  items,
  active,
  dotFor,
  labelFor,
  onToggle,
  onClear,
}: Props) {
  if (!items.length) return null;
  return (
    <div className="rail-group">
      <div className="rail-head">
        <span className="rail-name">{label}</span>
        {active.length > 0 && <Button minimal small text="clear" onClick={onClear} />}
      </div>
      <div className="rail-chips">
        {items.map((t) => (
          <Tag
            key={t}
            interactive
            round
            minimal={!active.includes(t)}
            intent={active.includes(t) ? 'primary' : 'none'}
            onClick={() => onToggle(t)}
            aria-pressed={active.includes(t)}
            role="button"
          >
            {dotFor && <span className="rail-dot" style={{ background: dotFor(t) }} />}
            {labelFor ? labelFor(t) : t}
          </Tag>
        ))}
      </div>
    </div>
  );
}
