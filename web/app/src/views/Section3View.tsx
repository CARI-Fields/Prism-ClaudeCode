import { useState } from 'react';
import { Card, Checkbox, Elevation, HTMLSelect, Slider } from '@blueprintjs/core';
import { useData } from '../data/DataContext';
import { useFilter, useReport, useTheme } from '../state/AppStateProvider';
import { scopeRuns, scopeTurns } from '../data/filters';
import { taskLabel } from '../data/taskLabel';
import { EChart } from '../components/EChart';
import { orderedRequests } from '../charts/ordered';
import { AGENT_TYPE_ORDER } from '../charts/agentSymbols';
import { costTimelineOption } from '../charts/costTimeline';
import { breakdownData, hitRateData, COMPOSE_MODES } from '../charts/contextBreakdown';
import { contextOption } from '../charts/contextOption';
import { ContextTextPanel } from '../components/ContextTextPanel';
import type { CtxSelection } from '../components/ContextTextPanel';

export function Section3View() {
  const { data } = useData();
  const { report } = useReport();
  const { effective, effectiveTask } = useFilter();
  const { mode } = useTheme();
  const [compose, setCompose] = useState('context');
  const [group, setGroup] = useState('agent');
  const [hitrate, setHitrate] = useState(true);
  const [density, setDensity] = useState(100);
  const [sel, setSel] = useState<Record<string, CtxSelection | null>>({});
  const variant = data?.manifest.variants.find((v) => v.key === report) ?? data?.manifest.variants[0];
  if (!variant || !data) return null;

  const s3 = effective('s3');
  const s3Task = effectiveTask('s3');
  const runs = scopeRuns(data.runs, s3Task, s3);
  const turns = scopeTurns(data.turns, s3Task, s3);
  const singleAgent = s3.agent.length === 1 ? s3.agent[0] : 'all';
  const mdef = COMPOSE_MODES[compose as 'context' | 'source' | 'token'] ?? COMPOSE_MODES.context;

  return (
    <div className="view view-stack">
      <Card elevation={Elevation.ZERO} className="panel-card">
        <div className="rail-head"><span className="rail-name">Display</span></div>
        <div className="s3-controls">
          <label>
            bar density
            <Slider min={0} max={100} stepSize={1} labelRenderer={false} value={density} onChange={setDensity} />
          </label>
          <label>
            compose by
            <HTMLSelect value={compose} onChange={(e) => setCompose(e.currentTarget.value)}>
              <option value="context">/context</option>
              <option value="source">source (detailed)</option>
              <option value="token">token type</option>
            </HTMLSelect>
          </label>
          <label>
            group
            <HTMLSelect value={group} onChange={(e) => setGroup(e.currentTarget.value)}>
              <option value="agent">agent type</option>
              <option value="none">none</option>
            </HTMLSelect>
          </label>
          <Checkbox checked={hitrate} onChange={(e) => setHitrate(e.currentTarget.checked)} label="cache hit rate" />
        </div>
      </Card>
      {runs.map((run) => {
        const rowsForRun = turns
          .filter((t) => t.run_id === run.run_id)
          .sort((a, b) => a.request_index - b.request_index);
        const typeByIndex = new Map<number, string>(
          rowsForRun.map((t, i) => [i, t.request_type ?? 'main-agent'])
        );
        const ordered = orderedRequests(
          typeByIndex,
          rowsForRun.map((_, i) => i),
          singleAgent,
          group,
          AGENT_TYPE_ORDER
        );
        const barMaxWidth = Math.max(6, Math.round(6 + 40 * (density / 100)));
        // Denser bars pack tighter: gap shrinks as the bars widen (and vice-versa).
        const barCategoryGap = `${Math.round(60 - 52 * (density / 100))}%`;
        const bd = breakdownData(
          mdef,
          rowsForRun,
          data.components.filter((c) => c.run_id === run.run_id)
        );
        const hitData = hitrate ? hitRateData(rowsForRun, ordered) : [];
        return (
          <Card elevation={Elevation.ZERO} className="panel-card" key={run.run_id}>
            <div className="panel-head">
              <h2 className="panel-title">
                {taskLabel(run.task)} / {run.condition} / r{run.rep}
              </h2>
              <span className="run-tag">{run.run_id}</span>
            </div>
            <h3 className="cache-sub">Per-Run Request Cost Timeline</h3>
            <EChart
              className="chart"
              themeMode={mode}
              option={costTimelineOption(rowsForRun, ordered, barMaxWidth, barCategoryGap)}
            />
            <h3 className="cache-sub">Context Source Breakdown</h3>
            <EChart
              className="chart tall"
              themeMode={mode}
              option={contextOption(bd, ordered, hitrate, hitData)}
              onClick={
                mdef.clickable
                  ? (p) => {
                      const pos = ordered.indexes[p.dataIndex];
                      const row = rowsForRun[pos];
                      if (!row) return;
                      setSel((s) => ({
                        ...s,
                        [run.run_id]: {
                          component: p.seriesName,
                          requestIndex: row.request_index,
                          type: String(row.request_type ?? 'main-agent'),
                          tokens: bd.byKey.get(`${pos}:${p.seriesName}`) ?? 0,
                        },
                      }));
                    }
                  : undefined
              }
            />
            <ContextTextPanel
              runId={run.run_id}
              selection={mdef.clickable ? (sel[run.run_id] ?? null) : null}
            />
          </Card>
        );
      })}
    </div>
  );
}
