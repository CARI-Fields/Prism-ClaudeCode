import type { Manifest } from '../types';

interface Props { manifest: Manifest; activeKey: string; onSwitch: (key: string) => void; }

export function Masthead({ manifest, activeKey, onSwitch }: Props) {
  const active = manifest.variants.find((v) => v.key === activeKey) ?? manifest.variants[0];
  if (!active) return null;
  return (
    <header className="masthead" id="masthead">
      <div className="masthead-inner">
        <div>
          <div className="eyebrow">{active.eyebrow}</div>
          <h1>{active.title}</h1>
          <p className="lede" dangerouslySetInnerHTML={{ __html: active.lede }} />
        </div>
        <nav className="switcher" hidden={manifest.variants.length <= 1}>
          {manifest.variants.map((v) => (
            <button
              key={v.key}
              type="button"
              className={v.key === activeKey ? 'switch-tab on' : 'switch-tab'}
              onClick={() => onSwitch(v.key)}
            >
              {v.title}
            </button>
          ))}
        </nav>
      </div>
    </header>
  );
}
