import { useEffect, useRef, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

interface AgentEvent {
  type: 'thought' | 'tool_call' | 'tool_result' | 'error' | 'done'
  content: string
  timestamp: string
}

interface AgentOutputProps {
  jobId: string
  onDone?: () => void
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

export function AgentOutput({ jobId, onDone }: AgentOutputProps) {
  const { t } = useTranslation()
  const [events, setEvents] = useState<AgentEvent[]>([])
  const [connected, setConnected] = useState(false)
  const [finished, setFinished] = useState(false)
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
          onDone?.()
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
      <CardHeader className="py-3">
        <div className="flex items-center justify-between">
          <CardTitle className="text-base">{t('agent.output')}</CardTitle>
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
          </div>
        </div>
      </CardHeader>
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
    </Card>
  )
}
