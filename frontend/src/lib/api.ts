const API_BASE = ''

function getToken(): string | null {
  return localStorage.getItem('token')
}

async function request<T>(path: string, options: RequestInit = {}): Promise<T> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...((options.headers as Record<string, string>) || {}),
  }
  if (token) {
    headers['Authorization'] = `Bearer ${token}`
  }

  const res = await fetch(`${API_BASE}${path}`, { ...options, headers })
  if (res.status === 401) {
    localStorage.removeItem('token')
    window.location.href = '/login'
    throw new Error('Unauthorized')
  }
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body.detail || `Request failed: ${res.status}`)
  }
  return res.json()
}

export const api = {
  register: (email: string, password: string) =>
    request<{ access_token: string }>('/api/auth/register', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  login: (email: string, password: string) =>
    request<{ access_token: string }>('/api/auth/login', {
      method: 'POST',
      body: JSON.stringify({ email, password }),
    }),

  me: () => request<{ id: number; email: string; role: string }>('/api/auth/me'),

  getSettings: () => request<{ settings: Record<string, string> }>('/api/settings'),

  updateSettings: (items: { key: string; value: string }[]) =>
    request<{ settings: Record<string, string> }>('/api/settings', {
      method: 'PUT',
      body: JSON.stringify(items),
    }),

  getRepos: () =>
    request<{ id: number; workspace_id: number; github_full_name: string; deploy_provider: string }[]>('/api/repos'),

  createRepo: (github_full_name: string, deploy_provider = 'railway') =>
    request<{ id: number; workspace_id: number; github_full_name: string; deploy_provider: string }>('/api/repos', {
      method: 'POST',
      body: JSON.stringify({ github_full_name, deploy_provider }),
    }),

  getIssues: (repoId?: number) =>
    request<{ id: number; repo_id: number; submitted_by: number; github_issue_number: number | null; status: string; model_tier: string; title: string }[]>(
      `/api/issues${repoId ? `?repo_id=${repoId}` : ''}`
    ),
}
