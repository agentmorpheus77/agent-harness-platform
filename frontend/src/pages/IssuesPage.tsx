import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Plus, RotateCcw, Loader2, ExternalLink, GitPullRequest, Eye, ChevronDown, ChevronUp, MessageSquare } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { AgentOutput } from '@/components/AgentOutput'
import { api } from '@/lib/api'

interface Issue {
  id: number
  repo_id: number
  submitted_by: number
  github_issue_number: number | null
  pr_number: number | null
  branch_name: string | null
  preview_url: string | null
  status: string
  model_tier: string
  title: string
  body: string | null
}

const statusColors: Record<string, string> = {
  open: 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/20',
  building: 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
  review: 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/20',
  merged: 'bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/20',
  error: 'bg-red-500/15 text-red-700 dark:text-red-400 border-red-500/20',
  closed: 'bg-gray-500/15 text-gray-700 dark:text-gray-400 border-gray-500/20',
}

function getStoredJobId(issueId: number): string | null {
  return localStorage.getItem(`issue_${issueId}_job`)
}
function storeJobId(issueId: number, jobId: string) {
  localStorage.setItem(`issue_${issueId}_job`, jobId)
}
function clearJobId(issueId: number) {
  localStorage.removeItem(`issue_${issueId}_job`)
}
function getStoredPreviewUrl(issueId: number): string | null {
  return localStorage.getItem(`issue_${issueId}_preview`)
}
function storePreviewUrl(issueId: number, url: string) {
  localStorage.setItem(`issue_${issueId}_preview`, url)
}

export function IssuesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { selectedRepoId } = useOutletContext<{ selectedRepoId: number | null }>()
  const [issues, setIssues] = useState<Issue[]>([])
  const [activeJobs, setActiveJobs] = useState<Record<number, string>>({})
  const [expandedOutputs, setExpandedOutputs] = useState<Record<number, boolean>>({})
  const [expandedDetails, setExpandedDetails] = useState<Record<number, boolean>>({})
  const [resetting, setResetting] = useState<Record<number, boolean>>({})
  const [starting, setStarting] = useState<Record<number, boolean>>({})
  const [previewUrls, setPreviewUrls] = useState<Record<number, string>>({})
  const [feedback, setFeedback] = useState<Record<number, string>>({})
  const [sendingFeedback, setSendingFeedback] = useState<Record<number, boolean>>({})

  const loadIssues = useCallback(() => {
    api.getIssues(selectedRepoId ?? undefined).then((loaded) => {
      setIssues(loaded)
      const restored: Record<number, string> = {}
      const expanded: Record<number, boolean> = {}
      const previews: Record<number, string> = {}
      for (const issue of loaded) {
        const storedJob = getStoredJobId(issue.id)
        const storedPreview = getStoredPreviewUrl(issue.id)
        if (storedPreview) previews[issue.id] = storedPreview
        if (['building', 'review', 'error'].includes(issue.status) && storedJob) {
          restored[issue.id] = storedJob
          expanded[issue.id] = true
        }
        if (!['building'].includes(issue.status) && storedJob) {
          // keep job id for output viewing but don't auto-expand
        }
      }
      setActiveJobs((prev) => ({ ...prev, ...restored }))
      setExpandedOutputs((prev) => ({ ...prev, ...expanded }))
      setPreviewUrls((prev) => ({ ...prev, ...previews }))
    }).catch(() => {})
  }, [selectedRepoId])

  useEffect(() => { loadIssues() }, [loadIssues])

  const handleStartAgent = async (issue: Issue) => {
    if (starting[issue.id]) return
    setStarting((prev) => ({ ...prev, [issue.id]: true }))
    try {
      const result = await api.startAgent(issue.id, issue.model_tier || 'free')
      storeJobId(issue.id, result.job_id)
      setActiveJobs((prev) => ({ ...prev, [issue.id]: result.job_id }))
      setExpandedOutputs((prev) => ({ ...prev, [issue.id]: true }))
      setIssues((prev) =>
        prev.map((i) => (i.id === issue.id ? { ...i, status: 'building' } : i))
      )
    } catch (e) {
      console.error('Failed to start agent:', e)
    } finally {
      setStarting((prev) => { const n = { ...prev }; delete n[issue.id]; return n })
    }
  }

  const handleAgentDone = useCallback((jobId?: string, previewUrl?: string) => {
    // Store preview URL if available
    if (previewUrl) {
      setPreviewUrls((prev) => {
        const issueId = Object.entries(activeJobs).find(([, j]) => j === jobId)?.[0]
        if (issueId) {
          storePreviewUrl(Number(issueId), previewUrl)
          return { ...prev, [Number(issueId)]: previewUrl }
        }
        return prev
      })
    }
    loadIssues()
  }, [selectedRepoId, activeJobs, loadIssues])

  const handleReset = async (issue: Issue) => {
    setResetting((prev) => ({ ...prev, [issue.id]: true }))
    try {
      await api.resetIssue(issue.id)
      clearJobId(issue.id)
      setActiveJobs((prev) => { const n = { ...prev }; delete n[issue.id]; return n })
      setExpandedOutputs((prev) => { const n = { ...prev }; delete n[issue.id]; return n })
      // Optimistic update + reload from API
      setIssues((prev) => prev.map((i) => (i.id === issue.id ? { ...i, status: 'open' } : i)))
      setTimeout(() => loadIssues(), 500)
    } catch (e) {
      console.error('Failed to reset issue:', e)
    } finally {
      setResetting((prev) => ({ ...prev, [issue.id]: false }))
    }
  }

  const handleFeedback = async (issue: Issue) => {
    const text = feedback[issue.id]?.trim()
    if (!text) return
    setSendingFeedback((prev) => ({ ...prev, [issue.id]: true }))
    try {
      const result = await api.requestChanges(issue.id, text)
      if (result?.job_id) {
        storeJobId(issue.id, result.job_id)
        setActiveJobs((prev) => ({ ...prev, [issue.id]: result.job_id }))
        setExpandedOutputs((prev) => ({ ...prev, [issue.id]: true }))
        setIssues((prev) => prev.map((i) => (i.id === issue.id ? { ...i, status: 'building' } : i)))
        setFeedback((prev) => { const n = { ...prev }; delete n[issue.id]; return n })
      }
    } catch (e) {
      console.error('Feedback failed:', e)
    } finally {
      setSendingFeedback((prev) => ({ ...prev, [issue.id]: false }))
    }
  }

  const toggleOutput = (issueId: number) =>
    setExpandedOutputs((prev) => ({ ...prev, [issueId]: !prev[issueId] }))

  const toggleDetails = (issueId: number) =>
    setExpandedDetails((prev) => ({ ...prev, [issueId]: !prev[issueId] }))

  const isStuck = (issue: Issue) => issue.status === 'building' && !activeJobs[issue.id]
  const hasJob = (issue: Issue) => !!activeJobs[issue.id]
  const prUrl = (issue: Issue) =>
    issue.pr_number
      ? `https://github.com/agentmorpheus77/agent-harness-platform/pull/${issue.pr_number}`
      : null

  return (
    <div>
      <div className="flex items-center justify-between mb-6">
        <h1 className="text-2xl font-bold">{t('issues.title')}</h1>
        <Button onClick={() => navigate('/app/issues/new')}>
          <Plus className="h-4 w-4 mr-1" />
          {t('issues.newIssue')}
        </Button>
      </div>

      {issues.length === 0 ? (
        <Card>
          <CardContent className="py-10 text-center text-muted-foreground">
            {t('issues.noIssues')}
          </CardContent>
        </Card>
      ) : (
        <div className="space-y-3">
          {issues.map((issue) => (
            <div key={issue.id} className="space-y-2">
              <Card className="hover:border-primary/40 transition-colors">
                <CardHeader className="py-3">
                  {/* Title row */}
                  <div className="flex items-start justify-between gap-2">
                    <button
                      className="text-left flex-1 min-w-0"
                      onClick={() => toggleDetails(issue.id)}
                    >
                      <CardTitle className="text-base leading-snug">
                        {issue.github_issue_number && (
                          <span className="text-muted-foreground mr-2 text-sm">#{issue.github_issue_number}</span>
                        )}
                        {issue.title || `Issue ${issue.id}`}
                      </CardTitle>
                      {issue.body && (
                        <p className="text-xs text-muted-foreground mt-1 line-clamp-1">{issue.body}</p>
                      )}
                    </button>

                    {/* Actions */}
                    <div className="flex items-center gap-2 flex-shrink-0 flex-wrap justify-end">
                      <Badge variant="outline" className="text-xs">{issue.model_tier}</Badge>

                      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusColors[issue.status] || statusColors.open}`}>
                        {issue.status === 'building' && hasJob(issue) && (
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        )}
                        {t(`issues.status.${issue.status}`) || issue.status}
                      </span>

                      {/* Start agent */}
                      {issue.status === 'open' && (
                        <Button size="sm" onClick={() => handleStartAgent(issue)} disabled={!!starting[issue.id]}>
                          {starting[issue.id] ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : null}
                          {t('agent.start')}
                        </Button>
                      )}

                      {/* View output */}
                      {hasJob(issue) && (
                        <Button size="sm" variant="outline" onClick={() => toggleOutput(issue.id)}>
                          {expandedOutputs[issue.id] ? <ChevronUp className="h-3 w-3 mr-1" /> : <ChevronDown className="h-3 w-3 mr-1" />}
                          {expandedOutputs[issue.id] ? t('agent.hideOutput') : t('agent.viewOutput')}
                        </Button>
                      )}

                      {/* PR link */}
                      {prUrl(issue) && (
                        <a href={prUrl(issue)!} target="_blank" rel="noreferrer">
                          <Button size="sm" variant="outline">
                            <GitPullRequest className="h-3 w-3 mr-1" />
                            PR #{issue.pr_number}
                          </Button>
                        </a>
                      )}

                      {/* Preview URL */}
                      {previewUrls[issue.id] && (
                        <a href={previewUrls[issue.id]} target="_blank" rel="noreferrer">
                          <Button size="sm" variant="outline" className="text-purple-600 border-purple-400">
                            <Eye className="h-3 w-3 mr-1" />
                            Preview
                            <ExternalLink className="h-3 w-3 ml-1" />
                          </Button>
                        </a>
                      )}

                      {/* Reset (stuck or error) */}
                      {(isStuck(issue) || issue.status === 'error') && (
                        <Button size="sm" variant="destructive" onClick={() => handleReset(issue)} disabled={resetting[issue.id]}>
                          {resetting[issue.id] ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <RotateCcw className="h-3 w-3 mr-1" />}
                          Reset
                        </Button>
                      )}

                      {/* Expand/collapse details */}
                      <Button size="sm" variant="ghost" onClick={() => toggleDetails(issue.id)}>
                        {expandedDetails[issue.id] ? <ChevronUp className="h-3 w-3" /> : <ChevronDown className="h-3 w-3" />}
                      </Button>
                    </div>
                  </div>

                  {/* Expanded detail: body + feedback */}
                  {expandedDetails[issue.id] && (
                    <div className="mt-3 space-y-3 border-t pt-3">
                      {issue.body && (
                        <p className="text-sm text-muted-foreground whitespace-pre-wrap">{issue.body}</p>
                      )}

                      {/* Feedback box for review/error status */}
                      {['review', 'error', 'merged'].includes(issue.status) && (
                        <div className="space-y-2">
                          <p className="text-xs font-medium text-muted-foreground">Feedback an Agent:</p>
                          <textarea
                            className="w-full text-sm rounded-md border bg-background px-3 py-2 min-h-[60px] resize-none focus:outline-none focus:ring-2 focus:ring-ring"
                            placeholder="z.B. Button zu groß, bitte kleiner machen..."
                            value={feedback[issue.id] || ''}
                            onChange={(e) => setFeedback((prev) => ({ ...prev, [issue.id]: e.target.value }))}
                          />
                          <Button
                            size="sm"
                            onClick={() => handleFeedback(issue)}
                            disabled={!feedback[issue.id]?.trim() || !!sendingFeedback[issue.id]}
                          >
                            {sendingFeedback[issue.id] ? <Loader2 className="h-3 w-3 mr-1 animate-spin" /> : <MessageSquare className="h-3 w-3 mr-1" />}
                            Agent nochmal starten
                          </Button>
                        </div>
                      )}
                    </div>
                  )}
                </CardHeader>
              </Card>

              {/* Agent Output */}
              {hasJob(issue) && expandedOutputs[issue.id] && (
                <AgentOutput
                  jobId={activeJobs[issue.id]}
                  onDone={handleAgentDone}
                />
              )}
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
