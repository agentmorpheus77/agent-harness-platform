import { useEffect, useState, useRef } from 'react'
import { useOutletContext } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { CheckCircle2, XCircle, Bot } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface Issue {
  id: number
  repo_id: number
  submitted_by: number
  github_issue_number: number | null
  status: string
  model_tier: string
  title: string
  body?: string | null
}

interface OutletCtx {
  selectedRepoId: number | null
}

const COLUMNS = ['open', 'building', 'review', 'merged', 'closed'] as const

function tierBadge(tier: string) {
  switch (tier) {
    case 'free':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'balanced':
      return 'bg-blue-500/20 text-blue-400 border-blue-500/30'
    case 'premium':
      return 'bg-purple-500/20 text-purple-400 border-purple-500/30'
    default:
      return ''
  }
}

function columnColor(col: string) {
  switch (col) {
    case 'open':
      return 'border-t-blue-500'
    case 'building':
      return 'border-t-yellow-500'
    case 'review':
      return 'border-t-orange-500'
    case 'merged':
      return 'border-t-green-500'
    case 'closed':
      return 'border-t-gray-500'
    default:
      return ''
  }
}

export function StatusBoardPage() {
  const { t } = useTranslation()
  const { selectedRepoId } = useOutletContext<OutletCtx>()
  const [issues, setIssues] = useState<Issue[]>([])
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)

  async function loadIssues() {
    try {
      const data = await api.getIssues(selectedRepoId ?? undefined)
      setIssues(data)
    } catch {
      // ignore
    }
  }

  useEffect(() => {
    loadIssues()
    // Poll every 5 seconds
    intervalRef.current = setInterval(loadIssues, 5000)
    return () => {
      if (intervalRef.current) clearInterval(intervalRef.current)
    }
  }, [selectedRepoId])

  async function handleApprove(issueId: number) {
    try {
      const result = await api.approveIssue(issueId)
      if (result.success) {
        toast.success(result.message)
        loadIssues()
      } else {
        toast.error(result.message)
      }
    } catch {
      toast.error(t('board.approveFailed'))
    }
  }

  async function handleRequestChanges(issueId: number) {
    const feedback = prompt(t('board.feedbackPrompt'))
    if (!feedback) return
    try {
      await api.requestChanges(issueId, feedback)
      toast.success(t('board.feedbackSent'))
      loadIssues()
    } catch {
      toast.error(t('board.feedbackFailed'))
    }
  }

  const grouped = Object.fromEntries(COLUMNS.map((c) => [c, issues.filter((i) => i.status === c)]))

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('board.title')}</h1>

      <div className="grid grid-cols-1 md:grid-cols-5 gap-4 min-h-[60vh]">
        {COLUMNS.map((col) => (
          <div key={col} className={`rounded-lg border border-t-4 ${columnColor(col)} bg-card p-3 space-y-3`}>
            <div className="flex items-center justify-between">
              <h2 className="text-sm font-semibold uppercase tracking-wide text-muted-foreground">
                {t(`issues.status.${col}`)}
              </h2>
              <Badge variant="secondary" className="text-xs">
                {grouped[col]?.length ?? 0}
              </Badge>
            </div>

            <div className="space-y-2">
              {grouped[col]?.map((issue) => (
                <Card key={issue.id} className="shadow-sm">
                  <CardHeader className="p-3 pb-1">
                    <div className="flex items-start justify-between gap-2">
                      <CardTitle className="text-sm font-medium leading-tight">
                        {issue.title}
                      </CardTitle>
                      {issue.github_issue_number && (
                        <span className="text-xs text-muted-foreground shrink-0">
                          #{issue.github_issue_number}
                        </span>
                      )}
                    </div>
                  </CardHeader>
                  <CardContent className="p-3 pt-1 space-y-2">
                    <Badge variant="outline" className={`text-xs ${tierBadge(issue.model_tier)}`}>
                      {issue.model_tier}
                    </Badge>

                    {issue.status === 'building' && (
                      <div className="flex items-center gap-1 text-xs text-yellow-400">
                        <Bot className="h-3 w-3 animate-pulse" />
                        <span>{t('agent.running')}</span>
                      </div>
                    )}

                    {/* Action buttons for review state */}
                    {issue.status === 'review' && (
                      <div className="flex gap-1.5 pt-1">
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs text-green-400 hover:text-green-300"
                          onClick={() => handleApprove(issue.id)}
                        >
                          <CheckCircle2 className="mr-1 h-3 w-3" />
                          {t('board.approve')}
                        </Button>
                        <Button
                          size="sm"
                          variant="ghost"
                          className="h-7 text-xs text-red-400 hover:text-red-300"
                          onClick={() => handleRequestChanges(issue.id)}
                        >
                          <XCircle className="mr-1 h-3 w-3" />
                          {t('board.changes')}
                        </Button>
                      </div>
                    )}
                  </CardContent>
                </Card>
              ))}

              {(!grouped[col] || grouped[col].length === 0) && (
                <p className="text-xs text-muted-foreground/50 text-center py-4">
                  {t('board.empty')}
                </p>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  )
}
