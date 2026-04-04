import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { Plus } from 'lucide-react'
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

export function IssuesPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { selectedRepoId } = useOutletContext<{ selectedRepoId: number | null }>()
  const [issues, setIssues] = useState<Issue[]>([])
  const [activeJobs, setActiveJobs] = useState<Record<number, string>>({})

  useEffect(() => {
    api.getIssues(selectedRepoId ?? undefined).then(setIssues).catch(() => {})
  }, [selectedRepoId])

  const handleStartAgent = async (issue: Issue) => {
    try {
      const result = await api.startAgent(issue.id, issue.model_tier || 'free')
      setActiveJobs((prev) => ({ ...prev, [issue.id]: result.job_id }))
      setIssues((prev) =>
        prev.map((i) => (i.id === issue.id ? { ...i, status: 'building' } : i))
      )
    } catch (e) {
      console.error('Failed to start agent:', e)
    }
  }

  const handleAgentDone = () => {
    api.getIssues(selectedRepoId ?? undefined).then(setIssues).catch(() => {})
  }

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
                        {t(`issues.status.${issue.status}`)}
                      </span>
                      {issue.status === 'open' && !activeJobs[issue.id] && (
                        <Button
                          size="sm"
                          variant="default"
                          onClick={() => handleStartAgent(issue)}
                        >
                          {t('agent.start')}
                        </Button>
                      )}
                    </div>
                  </div>
                </CardHeader>
              </Card>
              {activeJobs[issue.id] && (
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
