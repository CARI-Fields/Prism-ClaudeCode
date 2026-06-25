import type { Manifest, Variant } from '../types';
import { conditionColor } from '../theme';

export function BriefBand({ variant, manifest }: { variant: Variant; manifest: Manifest }) {
  return (
    <section className="band band-brief">
      <div className="brief-grid">
        {variant.tasks.map((task, i) => {
          const meta = manifest.task_meta[task];
          return (
            <article className="brief" key={task}>
              <div className="brief-head">
                <span className="brief-no">{i + 1}</span>
                <div className="brief-title">
                  <span className="brief-task">{task}</span>
                  <h3>{meta?.title ?? task}</h3>
                </div>
              </div>
              <p className="brief-measures">{meta?.measures ?? ''}</p>
            </article>
          );
        })}
      </div>
      <div className="strat-legend">
        <div className="strat-legend-head">Strategies</div>
        <div className="strat-grid">
          {variant.conditions.map((c) => (
            <div className="strat" key={c}>
              <span className="strat-dot" style={{ background: conditionColor(c) }} />
              <div className="strat-text">
                <span className="strat-line">
                  <b>{c}</b>
                  {c === 'single_agent' && <span className="strat-base">baseline</span>}
                </span>
                <span>{manifest.strategy_desc[c] ?? ''}</span>
              </div>
            </div>
          ))}
        </div>
      </div>
    </section>
  );
}
