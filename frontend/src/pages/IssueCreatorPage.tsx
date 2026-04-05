import { useState, useRef, useEffect } from 'react'
import { useTranslation } from 'react-i18next'
import { useOutletContext, useNavigate } from 'react-router-dom'
import { X, Send, Bot, User as UserIcon, Loader2, CheckCircle2, Pencil } from 'lucide-react'
import ReactMarkdown from 'react-markdown'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Badge } from '@/components/ui/badge'
import { Separator } from '@/components/ui/separator'
import { Card, CardHeader, CardTitle } from '@/components/ui/card'
import { VoiceRecorder } from '@/components/VoiceRecorder'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface Repo {
  id: number
  workspace_id: number
  github_full_name: string
  deploy_provider: string
}

interface ChatMessage {
  role: 'user' | 'assistant'
  content: string
  imageBase64?: string
}

type ChatPhase = 'greeting' | 'clarification' | 'draft' | 'confirm' | 'chat'

const phaseColors: Record<ChatPhase, string> = {
  greeting: 'bg-blue-500/15 text-blue-400 border-blue-500/30',
  clarification: 'bg-yellow-500/15 text-yellow-400 border-yellow-500/30',
  draft: 'bg-green-500/15 text-green-400 border-green-500/30',
  confirm: 'bg-purple-500/15 text-purple-400 border-purple-500/30',
  chat: 'bg-gray-500/15 text-gray-400 border-gray-500/30',
}

export function IssueCreatorPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const { selectedRepoId, repos } = useOutletContext<{
    selectedRepoId: number | null
    repos: Repo[]
  }>()

  const [sessionId, setSessionId] = useState<string | null>(null)
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [sidebarOpen, setSidebarOpen] = useState(true)
  const [draftTitle, setDraftTitle] = useState<string | null>(null)
  const [draftBody, setDraftBody] = useState<string | null>(null)
  const [mockupImage, setMockupImage] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [loadedSkills, setLoadedSkills] = useState<string[]>([])
  const [phase, setPhase] = useState<ChatPhase>('greeting')
  const chatEndRef = useRef<HTMLDivElement>(null)

  const selectedRepo = repos.find((r) => r.id === selectedRepoId)

  // Start chat session when repo is selected
  useEffect(() => {
    if (!selectedRepoId) return
    api.startChat(selectedRepoId).then((res: { session_id: string; message: string; loaded_skills?: string[] }) => {
      setSessionId(res.session_id)
      setMessages([{ role: 'assistant', content: res.message }])
      if (res.loaded_skills) setLoadedSkills(res.loaded_skills)
    }).catch(() => {
      toast.error('Failed to start chat session')
    })
  }, [selectedRepoId])

  // Auto-scroll
  useEffect(() => {
    chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const sendMessage = async (text: string) => {
    if (!text.trim() || !sessionId || loading) return

    const userMsg: ChatMessage = { role: 'user', content: text }
    setMessages((prev) => [...prev, userMsg])
    setInput('')
    setLoading(true)

    try {
      const res = await api.chatMessage(sessionId, text)
      const assistantMsg: ChatMessage = { role: 'assistant', content: res.message }
      setMessages((prev) => [...prev, assistantMsg])

      // Update phase
      if (res.phase) {
        setPhase(res.phase as ChatPhase)
      }

      if (res.is_draft && res.draft_title) {
        setDraftTitle(res.draft_title)
        setDraftBody(res.draft_body || res.message)
      }

      if (res.is_ui_feature) {
        if (res.draft_title) {
          generateMockup(res.draft_title, res.draft_body || res.message)
        }
      }
    } catch {
      toast.error('Failed to get response')
    } finally {
      setLoading(false)
    }
  }

  const generateMockup = async (title: string, description: string) => {
    try {
      const res = await api.generateMockup(title, description)
      setMockupImage(res.image_base64)
      setMessages((prev) => [
        ...prev,
        {
          role: 'assistant',
          content: 'Here\'s a wireframe mockup of the feature:',
          imageBase64: res.image_base64,
        },
      ])
    } catch {
      // Mockup generation is optional
    }
  }

  const handleSubmit = async () => {
    if (!selectedRepoId || !draftTitle || !draftBody || submitting) return
    setSubmitting(true)

    try {
      const res = await api.submitIssue({
        repo_id: selectedRepoId,
        title: draftTitle,
        body: draftBody,
      })
      toast.success(`Issue #${res.github_issue_number} created!`)
      navigate('/app/issues')
    } catch (e) {
      toast.error(e instanceof Error ? e.message : 'Failed to submit issue')
    } finally {
      setSubmitting(false)
    }
  }

  const handleEditDraft = () => {
    // Tell the agent to revise the draft
    sendMessage('Please revise the draft based on my feedback.')
  }

  const handleTranscription = (text: string) => {
    setInput((prev) => (prev ? prev + ' ' + text : text))
  }

  if (!selectedRepoId) {
    return (
      <div className="flex items-center justify-center h-full text-muted-foreground">
        {t('issueCreator.selectRepo')}
      </div>
    )
  }

  return (
    <div className="flex flex-col h-[calc(100vh-3.5rem)] -m-6">
      {/* Header */}
      <div className="flex items-center justify-between px-6 py-3 border-b bg-card">
        <div className="flex items-center gap-3">
          <h1 className="text-lg font-semibold">{t('issueCreator.title')}</h1>
          {selectedRepo && (
            <Badge variant="outline">{selectedRepo.github_full_name}</Badge>
          )}
          {loadedSkills.length > 0 && loadedSkills.map((skill) => (
            <Badge key={skill} variant="secondary" className="text-xs">
              {skill}
            </Badge>
          ))}
          {/* Phase indicator */}
          <Badge variant="outline" className={`text-xs ${phaseColors[phase] || ''}`}>
            {t(`issueCreator.phase.${phase}`, phase)}
          </Badge>
        </div>
        <Button variant="ghost" size="icon" onClick={() => navigate('/app/issues')}>
          <X className="h-4 w-4" />
        </Button>
      </div>

      <div className="flex flex-1 overflow-hidden">
        {/* Chat area */}
        <div className="flex-1 flex flex-col">
          {/* Messages */}
          <div className="flex-1 overflow-y-auto p-6 space-y-4">
            {messages.map((msg, i) => (
              <div
                key={i}
                className={`flex gap-3 ${msg.role === 'user' ? 'justify-end' : ''}`}
              >
                {msg.role === 'assistant' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                    <Bot className="h-4 w-4 text-primary" />
                  </div>
                )}
                <div
                  className={`max-w-[70%] rounded-lg px-4 py-2 ${
                    msg.role === 'user'
                      ? 'bg-primary text-primary-foreground'
                      : 'bg-muted'
                  }`}
                >
                  {msg.role === 'user' ? (
                    <div className="whitespace-pre-wrap text-sm">{msg.content}</div>
                  ) : (
                    <div className="text-sm prose prose-sm dark:prose-invert max-w-none prose-p:my-1 prose-headings:my-2 prose-ul:my-1 prose-ol:my-1 prose-li:my-0 prose-pre:bg-black/30 prose-pre:rounded prose-code:text-xs">
                      <ReactMarkdown>{msg.content}</ReactMarkdown>
                    </div>
                  )}
                  {msg.imageBase64 && (
                    <img
                      src={`data:image/png;base64,${msg.imageBase64}`}
                      alt="Mockup"
                      className="mt-2 rounded border max-w-full"
                    />
                  )}
                </div>
                {msg.role === 'user' && (
                  <div className="flex-shrink-0 w-8 h-8 rounded-full bg-secondary flex items-center justify-center">
                    <UserIcon className="h-4 w-4" />
                  </div>
                )}
              </div>
            ))}
            {loading && (
              <div className="flex gap-3">
                <div className="flex-shrink-0 w-8 h-8 rounded-full bg-primary/10 flex items-center justify-center">
                  <Bot className="h-4 w-4 text-primary" />
                </div>
                <div className="bg-muted rounded-lg px-4 py-2">
                  <Loader2 className="h-4 w-4 animate-spin" />
                </div>
              </div>
            )}
            <div ref={chatEndRef} />
          </div>

          {/* Draft card inline when phase is draft */}
          {phase === 'draft' && draftTitle && (
            <div className="px-6 pb-2">
              <Card className="border-green-500/30 bg-green-500/5">
                <CardHeader className="py-3 px-4">
                  <CardTitle className="text-sm flex items-center justify-between">
                    <span>{draftTitle}</span>
                    <div className="flex gap-2">
                      <Button
                        size="sm"
                        variant="ghost"
                        className="h-7 text-xs"
                        onClick={handleEditDraft}
                      >
                        <Pencil className="h-3 w-3 mr-1" />
                        {t('issueCreator.editDraft')}
                      </Button>
                      <Button
                        size="sm"
                        onClick={handleSubmit}
                        disabled={submitting}
                        className="h-7 bg-green-600 hover:bg-green-700 text-white text-xs"
                      >
                        {submitting ? (
                          <Loader2 className="h-3 w-3 animate-spin mr-1" />
                        ) : (
                          <CheckCircle2 className="h-3 w-3 mr-1" />
                        )}
                        {t('issueCreator.submitToGithub')}
                      </Button>
                    </div>
                  </CardTitle>
                </CardHeader>
              </Card>
            </div>
          )}

          {/* Input area */}
          <div className="border-t bg-card p-4">
            {draftTitle && phase !== 'draft' && (
              <div className="mb-3 flex items-center gap-2">
                <Badge variant="default">{t('issueCreator.draftReady')}</Badge>
                <Button
                  size="sm"
                  onClick={handleSubmit}
                  disabled={submitting}
                  className="bg-green-600 hover:bg-green-700 text-white font-semibold"
                >
                  {submitting ? (
                    <Loader2 className="h-4 w-4 animate-spin mr-1" />
                  ) : (
                    <CheckCircle2 className="h-4 w-4 mr-1" />
                  )}
                  {t('issueCreator.submitToGithub')}
                </Button>
              </div>
            )}
            <form
              className="flex items-center gap-2"
              onSubmit={(e) => {
                e.preventDefault()
                sendMessage(input)
              }}
            >
              <VoiceRecorder onTranscription={handleTranscription} disabled={loading} />
              <Input
                value={input}
                onChange={(e) => setInput(e.target.value)}
                placeholder={t('issueCreator.placeholder')}
                disabled={loading}
                className="flex-1"
              />
              <Button type="submit" size="icon" disabled={!input.trim() || loading}>
                <Send className="h-4 w-4" />
              </Button>
            </form>
          </div>
        </div>

        {/* Right sidebar - Draft preview */}
        {sidebarOpen && (draftTitle || draftBody) && (
          <>
            <Separator orientation="vertical" />
            <div className="w-80 overflow-y-auto p-4 bg-card">
              <div className="flex items-center justify-between mb-4">
                <h2 className="font-semibold text-sm">{t('issueCreator.draftPreview')}</h2>
                <Button variant="ghost" size="icon" onClick={() => setSidebarOpen(false)}>
                  <X className="h-3 w-3" />
                </Button>
              </div>
              {draftTitle && (
                <div className="mb-3">
                  <label className="text-xs text-muted-foreground">{t('issueCreator.draftTitleLabel')}</label>
                  <p className="font-medium text-sm">{draftTitle}</p>
                </div>
              )}
              {draftBody && (
                <div>
                  <label className="text-xs text-muted-foreground">{t('issueCreator.draftBodyLabel')}</label>
                  <div className="mt-1 text-xs text-muted-foreground whitespace-pre-wrap bg-muted rounded p-3">
                    {draftBody}
                  </div>
                </div>
              )}
              {mockupImage && (
                <div className="mt-4">
                  <label className="text-xs text-muted-foreground">Mockup</label>
                  <img
                    src={`data:image/png;base64,${mockupImage}`}
                    alt="Mockup preview"
                    className="mt-1 rounded border w-full"
                  />
                </div>
              )}
            </div>
          </>
        )}
      </div>
    </div>
  )
}
