import { useMemo } from 'react';
import { Card, Elevation } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { inVariantRuns, scopeRuns } from '../data/filters';
import { taskLabel } from '../data/taskLabel';
import { conditionColor } from '../theme';
import { EChart } from '../components/EChart';
import { matrixData } from '../charts/matrix';
import { matrixOption } from '../charts/section1Options';

export function OverviewView() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  const runs = data?.runs ?? [];
  const sel = effective('overview');
  const selTask = effectiveTask('overview');
  const scoped = useMemo(
    () => (variant ? scopeRuns(inVariantRuns(runs, variant), selTask, sel) : []),
    [runs, variant, selTask, sel],
  );
  if (!variant || !data) return null;

  const tasks = selTask.length ? selTask : variant.tasks;
  const reps = Array.from(new Set(scoped.map((r) => r.rep))).sort((a, b) => a - b);
  const matrix = matrixData(scoped, tasks, reps, variant.conditions);
  const matrixPanel = mode === 'dark' ? '#1e242c' : '#ffffff';

  return (
    <div className="view view-overview">
      <div className="overview-grid">
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">{variant.title}</h2>
          <p className="panel-lede" dangerouslySetInnerHTML={{ __html: variant.lede }} />
          <ul className="strategy-legend">
            {variant.conditions.map((c) => (
              <li key={c}><span className="rail-dot" style={{ background: conditionColor(c) }} /><b>{c}</b> — <span>{data.manifest.strategy_desc[c] ?? ''}</span></li>
            ))}
          </ul>
        </Card>
        <Card elevation={Elevation.ZERO} className="panel-card">
          <h2 className="panel-title">Experiment matrix</h2>
          <p className="panel-sub">Run status for each task × feature cell — green passed, red failed, grey missing.</p>
          <EChart className="chart" themeMode={mode} option={matrixOption(matrix, matrixPanel)} />
        </Card>
      </div>
      <div className="task-briefs">
        {variant.tasks.map((task) => {
          const meta = data.manifest.task_meta[task];
          const prompt = data.manifest.task_prompts?.[task] ?? '';
          return (
            <Card elevation={Elevation.ZERO} className="panel-card task-brief" key={task}>
              <div className="task-brief-head">
                <span className="task-brief-eyebrow">{taskLabel(task)}</span>
                <h3 className="panel-title">{meta?.title ?? task}</h3>
              </div>
              <p className="panel-lede">{meta?.measures ?? ''}</p>
              {prompt ? (
                <details className="task-prompt">
                  <summary>
                    Prompt <span className="task-prompt-src">experiment/tasks/{task}/prompt.md</span>
                  </summary>
                  <pre>{prompt}</pre>
                </details>
              ) : (
                <p className="task-prompt-empty">Full prompt spec not committed for this task.</p>
              )}
            </Card>
          );
        })}
      </div>
    </div>
  );
}
