import type { ThemeMode } from '../types';

export const THEME_KEY = 'cc_report_theme';

// Resolve the active theme from (in order) an explicit URL theme, the stored
// preference, then the OS setting. Shared by AppStateProvider and the loading
// skeleton so the pre-data paint matches the app's eventual theme (no flash).
export function resolveThemeMode(urlTheme: ThemeMode | null = null): ThemeMode {
  if (urlTheme) return urlTheme;
  const stored = localStorage.getItem(THEME_KEY);
  if (stored === 'light' || stored === 'dark') return stored;
  // Double optional chain: guard against jsdom (no matchMedia) AND undefined result.
  return window.matchMedia?.('(prefers-color-scheme: dark)')?.matches ? 'dark' : 'light';
}
