import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { ChevronDown, ChevronRight, ExternalLink, Eye, GitPullRequest } from 'lucide-react'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'

interface AgentEvent {
  type: 'thought' | 'tool_call' | 'tool_result' | 'error' | 'done'
  content: string
  timestamp: string
}

interface AgentOutputProps {
  jobId: string
  onDone?: (jobId?: string, previewUrl?: string, prUrl?: string) => void
  defaultCollapsed?: boolean
}

const eventIcons: Record<string, string> = {
  thought: '\u{1F4AD}',   // thought bubble
  tool_call: '\u{1F527}', // wrench
  tool_result: '\u2705',  // checkmark
  error: '\u274C',        // cross mark
  done: '\u{1F3C1}',      // finish flag
}

const eventColors: Record<string, string> = {
  thought: 'text-blue-400',
  tool_call: 'text-yellow-400',
  tool_result: 'text-green-400',
  error: 'text-red-400',
  done: 'text-emerald-400',
}

export function AgentOutput({ jobId, onDone, defaultCollapsed = false }: AgentOutputProps) {
  const { t } = useTranslation()
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [finished, setFinished] = useState(false)
  const [collapsed, setCollapsed] = useState(defaultCollapsed)
  const [previewUrl, setPreviewUrl] = useState<string | null>(null)
  const [prUrl, setPrUrl] = useState<string | null>(null)
  const scrollRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    if (!jobId) return

    const eventSource = new EventSource(`/api/agent/${jobId}/stream`)
    setConnected(true)

    eventSource.onmessage = (e) => {
      try {
        const event: AgentEvent = JSON.parse(e.data)
        setEvents((prev) => [...prev, event])

        if (event.type === 'done' || event.type === 'error') {
          setFinished(true)
          setConnected(false)
          eventSource.close()
          // Poll job status for preview/pr URLs
          fetch(`/api/agent/${jobId}/status`, {
            headers: { Authorization: `Bearer ${localStorage.getItem('token')}` },
          })
            .then((r) => r.json())
            .then((status) => {
              if (status.preview_url) setPreviewUrl(status.preview_url)
              if (status.pr_url) setPrUrl(status.pr_url)
              onDone?.(jobId, status.preview_url, status.pr_url)
            })
            .catch(() => onDone?.(jobId))
        }
      } catch {
        // ignore parse errors
      }
    }

    eventSource.onerror = () => {
      setConnected(false)
      eventSource.close()
    }

    return () => {
      eventSource.close()
      setConnected(false)
    }
  }, [jobId, onDone])

  // Auto-scroll to bottom
  useEffect(() => {
    if (scrollRef.current) {
      scrollRef.current.scrollTop = scrollRef.current.scrollHeight
    }
  }, [events])

  return (
    <Card className="border-muted">
      <CardHeader className="py-3 cursor-pointer select-none" onClick={() => setCollapsed((c) => !c)}>
        <div className="flex items-center justify-between">
          <div className="flex items-center gap-2">
            {collapsed ? <ChevronRight className="h-4 w-4" /> : <ChevronDown className="h-4 w-4" />}
            <CardTitle className="text-base">{t('agent.output')}</CardTitle>
          </div>
          <div className="flex items-center gap-2">
            {connected && !finished && (
              <Badge variant="default" className="animate-pulse">
                {t('agent.running')}
              </Badge>
            )}
            {finished && (
              <Badge variant={events.some(e => e.type === 'error') ? 'destructive' : 'secondary'}>
                {events.some(e => e.type === 'error') ? t('agent.failed') : t('agent.completed')}
              </Badge>
            )}
            {prUrl && (
              <a href={prUrl} target="_blank" rel="noreferrer">
                <Button size="sm" variant="outline" className="h-6 text-xs px-2">
                  <GitPullRequest className="h-3 w-3 mr-1" /> PR
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              </a>
            )}
            {previewUrl && (
              <a href={previewUrl} target="_blank" rel="noreferrer">
                <Button size="sm" variant="outline" className="h-6 text-xs px-2 text-purple-600 border-purple-400">
                  <Eye className="h-3 w-3 mr-1" /> Preview
                  <ExternalLink className="h-3 w-3 ml-1" />
                </Button>
              </a>
            )}
            {events.length > 0 && (
              <span className="text-xs text-muted-foreground">{events.length} events</span>
            )}
          </div>
        </div>
      </CardHeader>
      {!collapsed && (
        <CardContent>
          <div
            ref={scrollRef}
            className="bg-black/80 dark:bg-black/60 rounded-lg p-4 font-mono text-sm max-h-[500px] overflow-y-auto space-y-1"
          >
            {events.length === 0 && connected && (
              <div className="text-muted-foreground animate-pulse">
                {t('agent.connecting')}
              </div>
            )}
            {events.map((event, i) => (
              <div key={i} className={`flex gap-2 ${eventColors[event.type] || 'text-gray-400'}`}>
                <span className="shrink-0">{eventIcons[event.type] || '>'}</span>
                <span className="whitespace-pre-wrap break-all">{event.content}</span>
              </div>
            ))}
          </div>
        </CardContent>
      )}
    </Card>
  )
}
