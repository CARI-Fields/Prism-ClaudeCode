// Long-horizon task keys (e.g. `coding_longhorizon`) read better as their bare
// domain ("coding" / "research") in the UI — the long-horizon panel already says
// "long-horizon", so the suffix is redundant noise. Display-only: the raw key is
// still what we filter and join on.
export const taskLabel = (task: string): string => task.replace(/_longhorizon$/, '');
