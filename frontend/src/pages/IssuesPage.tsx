import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext } from 'react-router-dom'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
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

  useEffect(() => {
    api.getIssues(selectedRepoId ?? undefined).then(setIssues).catch(() => {})
  }, [selectedRepoId])

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
            <Card key={issue.id}>
              <CardHeader className="py-3">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base">
                    {issue.github_issue_number && (
                      <span className="text-muted-foreground mr-2">#{issue.github_issue_number}</span>
                    )}
                    {issue.title || `Issue ${issue.id}`}
                  </CardTitle>
                  <Badge variant={statusVariants[issue.status] || 'outline'}>
                    {t(`issues.status.${issue.status}`)}
                  </Badge>
                </div>
              </CardHeader>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
