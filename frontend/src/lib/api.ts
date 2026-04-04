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

  startAgent: (issueId: number, modelTier = 'free', modelId?: string) =>
    request<{ job_id: string; model: string; worktree_path: string }>('/api/agent/start', {
      method: 'POST',
      body: JSON.stringify({ issue_id: issueId, model_tier: modelTier, model_id: modelId }),
    }),

  getJobStatus: (jobId: string) =>
    request<{ job_id: string; status: string; model: string; event_count: number }>(`/api/agent/${jobId}/status`),

  estimateComplexity: (title: string, body = '') =>
    request<{ tier: string; reason: string; estimated_files: number; score: number; categories: string[] }>(
      '/api/agent/estimate-complexity',
      { method: 'POST', body: JSON.stringify({ title, body }) }
    ),

  getModels: () => request<Record<string, { id: string; name: string; cost: string }[]>>('/api/agent/models'),

  // Chat
  startChat: (repoId: number) =>
    request<{ session_id: string; message: string }>('/api/chat/start', {
      method: 'POST',
      body: JSON.stringify({ repo_id: repoId }),
    }),

  chatMessage: (sessionId: string, message: string) =>
    request<{ message: string; is_draft: boolean; draft_title: string | null; draft_body: string | null; is_ui_feature: boolean }>(
      `/api/chat/${sessionId}/message`,
      { method: 'POST', body: JSON.stringify({ message }) }
    ),

  // Transcribe
  transcribe: async (blob: Blob): Promise<{ text: string }> => {
    const formData = new FormData()
    formData.append('file', blob, 'recording.webm')
    const token = localStorage.getItem('token')
    const res = await fetch('/api/transcribe', {
      method: 'POST',
      headers: token ? { Authorization: `Bearer ${token}` } : {},
      body: formData,
    })
    if (!res.ok) throw new Error('Transcription failed')
    return res.json()
  },

  // Mockup
  generateMockup: (title: string, description: string) =>
    request<{ image_base64: string; model_used: string }>('/api/mockup', {
      method: 'POST',
      body: JSON.stringify({ title, description }),
    }),

  // Issue submission
  submitIssue: (data: { repo_id: number; title: string; body: string; labels?: string[]; assignee?: string }) =>
    request<{ id: number; github_issue_number: number; github_url: string; title: string }>(
      '/api/issues/submit',
      { method: 'POST', body: JSON.stringify(data) }
    ),

  // Issue approval / feedback
  approveIssue: (issueId: number) =>
    request<{ success: boolean; message: string; conflicts: string[] | null }>(
      `/api/issues/${issueId}/approve`,
      { method: 'POST' }
    ),

  requestChanges: (issueId: number, feedback: string) =>
    request<{ issue_id: number; feedback: string; stored: boolean }>(
      `/api/issues/${issueId}/request-changes`,
      { method: 'POST', body: JSON.stringify({ feedback }) }
    ),

  // Skills
  getSkills: () =>
    request<{ name: string; description: string; version: string; status: string; path: string; keywords: string[]; required_keys: string[]; has_all_keys: boolean }[]>(
      '/api/skills'
    ),

  getSkillContent: (name: string) =>
    request<{ name: string; content: string }>(`/api/skills/${name}`),

  updateSkills: () =>
    request<{ results: Record<string, unknown>[] }>('/api/skills/update', { method: 'POST' }),

  getRelevantSkills: (text: string) =>
    request<{ skills: string[] }>('/api/skills/relevant', {
      method: 'POST',
      body: JSON.stringify({ text }),
    }),

  getSkillsForRepo: (repoId: number) =>
    request<{ skills: string[] }>(`/api/skills/for-repo/${repoId}`),
}
