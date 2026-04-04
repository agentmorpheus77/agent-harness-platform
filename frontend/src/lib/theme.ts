export type Theme = 'light' | 'dark' | 'system'

export function getStoredTheme(): Theme {
  return (localStorage.getItem('theme') as Theme) || 'system'
}

export function setTheme(theme: Theme) {
  localStorage.setItem('theme', theme)
  applyTheme(theme)
}

export function applyTheme(theme: Theme) {
  const root = document.documentElement
  if (theme === 'system') {
    const prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.classList.toggle('dark', prefersDark)
  } else {
    root.classList.toggle('dark', theme === 'dark')
  }
}
