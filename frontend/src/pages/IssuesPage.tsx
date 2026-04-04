import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext } from 'react-router-dom'
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

const statusVariants: Record<string, 'default' | 'secondary' | 'destructive' | 'outline'> = {
  open: 'outline',
  building: 'default',
  review: 'secondary',
  merged: 'default',
  closed: 'secondary',
}

export function IssuesPage() {
  const { t } = useTranslation()
  const { selectedRepoId } = useOutletContext<{ selectedRepoId: number | null }>()
  const [issues, setIssues] = useState<Issue[]>([])
  const [activeJobs, setActiveJobs] = useState<Record<number, string>>({}) // issueId -> jobId

  useEffect(() => {
    api.getIssues(selectedRepoId ?? undefined).then(setIssues).catch(() => {})
  }, [selectedRepoId])

  const handleStartAgent = async (issue: Issue) => {
    try {
      const result = await api.startAgent(issue.id, issue.model_tier || 'free')
      setActiveJobs((prev) => ({ ...prev, [issue.id]: result.job_id }))
      // Update issue status locally
      setIssues((prev) =>
        prev.map((i) => (i.id === issue.id ? { ...i, status: 'building' } : i))
      )
    } catch (e) {
      console.error('Failed to start agent:', e)
    }
  }

  const handleAgentDone = () => {
    // Refresh issues list
    api.getIssues(selectedRepoId ?? undefined).then(setIssues).catch(() => {})
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('issues.title')}</h1>
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
                      <Badge variant={statusVariants[issue.status] || 'outline'}>
                        {t(`issues.status.${issue.status}`)}
                      </Badge>
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
