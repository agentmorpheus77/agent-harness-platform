import { useEffect, useState, useCallback } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Plus, RotateCcw, Loader2 } from 'lucide-react'
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
  status: string
  model_tier: string
  title: string
}

const statusColors: Record<string, string> = {
  open: 'bg-blue-500/15 text-blue-700 dark:text-blue-400 border-blue-500/20',
  building: 'bg-yellow-500/15 text-yellow-700 dark:text-yellow-400 border-yellow-500/20',
  review: 'bg-purple-500/15 text-purple-700 dark:text-purple-400 border-purple-500/20',
  merged: 'bg-green-500/15 text-green-700 dark:text-green-400 border-green-500/20',
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

export function IssuesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { selectedRepoId } = useOutletContext<{ selectedRepoId: number | null }>()
  const [issues, setIssues] = useState<Issue[]>([])
  const [activeJobs, setActiveJobs] = useState<Record<number, string>>({})
  const [expandedOutputs, setExpandedOutputs] = useState<Record<number, boolean>>({})
  const [resetting, setResetting] = useState<Record<number, boolean>>({})
  const [starting, setStarting] = useState<Record<number, boolean>>({})

  // Load issues and restore job IDs from localStorage
  useEffect(() => {
    api.getIssues(selectedRepoId ?? undefined).then((loaded) => {
      setIssues(loaded)
      // Restore active jobs from localStorage for building issues
      const restored: Record<number, string> = {}
      const expanded: Record<number, boolean> = {}
      for (const issue of loaded) {
        const storedJob = getStoredJobId(issue.id)
        if (issue.status === 'building' && storedJob) {
          restored[issue.id] = storedJob
          expanded[issue.id] = true
        }
        // Clean up stale job IDs for non-building issues
        if (issue.status !== 'building' && storedJob) {
          clearJobId(issue.id)
        }
      }
      setActiveJobs((prev) => ({ ...prev, ...restored }))
      setExpandedOutputs((prev) => ({ ...prev, ...expanded }))
    }).catch(() => {})
  }, [selectedRepoId])

  const handleStartAgent = async (issue: Issue) => {
    // Prevent double-clicks
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
      setStarting((prev) => {
        const next = { ...prev }
        delete next[issue.id]
        return next
      })
    }
  }

  const handleAgentDone = useCallback(() => {
    api.getIssues(selectedRepoId ?? undefined).then((loaded) => {
      setIssues(loaded)
      // Clean up completed jobs
      for (const issue of loaded) {
        if (issue.status !== 'building') {
          clearJobId(issue.id)
        }
      }
    }).catch(() => {})
  }, [selectedRepoId])

  const handleReset = async (issue: Issue) => {
    setResetting((prev) => ({ ...prev, [issue.id]: true }))
    try {
      await api.resetIssue(issue.id)
      clearJobId(issue.id)
      setActiveJobs((prev) => {
        const next = { ...prev }
        delete next[issue.id]
        return next
      })
      setExpandedOutputs((prev) => {
        const next = { ...prev }
        delete next[issue.id]
        return next
      })
      setIssues((prev) =>
        prev.map((i) => (i.id === issue.id ? { ...i, status: 'open' } : i))
      )
    } catch (e) {
      console.error('Failed to reset issue:', e)
    } finally {
      setResetting((prev) => ({ ...prev, [issue.id]: false }))
    }
  }

  const toggleOutput = (issueId: number) => {
    setExpandedOutputs((prev) => ({ ...prev, [issueId]: !prev[issueId] }))
  }

  const hasActiveJob = (issue: Issue) => !!activeJobs[issue.id]
  const isStuck = (issue: Issue) => issue.status === 'building' && !activeJobs[issue.id]

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
              <Card>
                <CardHeader className="py-3">
                  <div className="flex items-center justify-between">
                    <CardTitle className="text-base">
                      {issue.github_issue_number && (
                        <span className="text-muted-foreground mr-2">#{issue.github_issue_number}</span>
                      )}
                      {issue.title || `Issue ${issue.id}`}
                    </CardTitle>
                    <div className="flex items-center gap-2">
                      <Badge variant="outline" className="text-xs">
                        {issue.model_tier}
                      </Badge>
                      <span className={`inline-flex items-center rounded-full border px-2.5 py-0.5 text-xs font-semibold ${statusColors[issue.status] || statusColors.open}`}>
                        {issue.status === 'building' && hasActiveJob(issue) && (
                          <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                        )}
                        {t(`issues.status.${issue.status}`)}
                      </span>
                      {issue.status === 'open' && !activeJobs[issue.id] && (
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleStartAgent(issue)}
                          disabled={!!starting[issue.id]}
                        >
                          {starting[issue.id] ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          ) : null}
                          {t('agent.start')}
                        </Button>
                      )}
                      {issue.status === 'building' && hasActiveJob(issue) && (
                        <Button
                          size="sm"
                          variant="outline"
                          onClick={() => toggleOutput(issue.id)}
                        >
                          {expandedOutputs[issue.id] ? t('agent.hideOutput') : t('agent.viewOutput')}
                        </Button>
                      )}
                      {isStuck(issue) && (
                        <Button
                          size="sm"
                          variant="destructive"
                          onClick={() => handleReset(issue)}
                          disabled={resetting[issue.id]}
                        >
                          {resetting[issue.id] ? (
                            <Loader2 className="h-3 w-3 mr-1 animate-spin" />
                          ) : (
                            <RotateCcw className="h-3 w-3 mr-1" />
                          )}
                          Reset
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
              </Card>
              {hasActiveJob(issue) && expandedOutputs[issue.id] && (
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
