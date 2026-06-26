interface ChipProps { label: string; active: boolean; dot?: string; onClick: () => void; }
export function Chip({ label, active, dot, onClick }: ChipProps) {
  return (
    <button type="button" className={active ? 'chip on' : 'chip'} aria-pressed={active} onClick={onClick}>
      {dot && <span className="dot" style={{ background: dot }} />}
      {label}
    </button>
  );
}
