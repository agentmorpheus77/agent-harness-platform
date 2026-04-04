import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'
import { Tabs, TabsContent, TabsList, TabsTrigger } from '@/components/ui/tabs'
import { api } from '@/lib/api'

const SETTING_GROUPS = [
  {
    titleKey: 'settings.groups.llmProviders',
    keys: [
      'openrouter_api_key',
      'anthropic_api_key',
      'openai_api_key',
      'gemini_api_key',
    ],
  },
  {
    titleKey: 'settings.groups.tools',
    keys: [
      'github_token',
      'railway_api_key',
      'firecrawl_api_key',
      'elevenlabs_api_key',
      'whisper_api_key',
    ],
  },
] as const

type SettingKey = (typeof SETTING_GROUPS)[number]['keys'][number]

const ALL_KEYS: SettingKey[] = SETTING_GROUPS.flatMap((g) => [...g.keys])

interface DomainEntry {
  id: number
  workspace_id: number
  service_id: string
  domain_name: string
  status: string
  created_at: string
}

function statusVariant(status: string): 'default' | 'secondary' | 'destructive' | 'outline' {
  switch (status) {
    case 'active': return 'default'
    case 'pending': return 'secondary'
    case 'error': return 'destructive'
    default: return 'outline'
  }
}

export function SettingsPage() {
  const { t } = useTranslation()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  // Domains state
  const [domains, setDomains] = useState<DomainEntry[]>([])
  const [newServiceId, setNewServiceId] = useState('')
  const [newDomainName, setNewDomainName] = useState('')
  const [domainError, setDomainError] = useState('')

  useEffect(() => {
    api.getSettings().then(({ settings }) => setValues(settings)).catch(() => {})
    api.getDomains().then(setDomains).catch(() => {})
  }, [])

  async function handleSave() {
    const items = ALL_KEYS
      .filter((key) => values[key] !== undefined && values[key] !== '')
      .map((key) => ({ key, value: values[key] }))
    await api.updateSettings(items)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  async function handleAddDomain() {
    if (!newServiceId.trim() || !newDomainName.trim()) return
    setDomainError('')
    try {
      const domain = await api.addDomain(newServiceId.trim(), newDomainName.trim())
      setDomains([...domains, domain])
      setNewServiceId('')
      setNewDomainName('')
    } catch (err) {
      setDomainError(err instanceof Error ? err.message : 'Failed to add domain')
    }
  }

  async function handleRemoveDomain(id: number) {
    try {
      await api.removeDomain(id)
      setDomains(domains.filter((d) => d.id !== id))
    } catch {
      // ignore
    }
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
      <Tabs defaultValue="api-keys">
        <TabsList>
          <TabsTrigger value="api-keys">{t('settings.apiKeys')}</TabsTrigger>
          <TabsTrigger value="domains">{t('settings.domains.tab')}</TabsTrigger>
        </TabsList>

        <TabsContent value="api-keys" className="space-y-6 mt-4">
          {SETTING_GROUPS.map((group) => (
            <Card key={group.titleKey}>
              <CardHeader>
                <CardTitle>{t(group.titleKey)}</CardTitle>
              </CardHeader>
              <CardContent className="space-y-4">
                {group.keys.map((key) => (
                  <div key={key} className="space-y-2">
                    <Label htmlFor={key}>{t(`settings.keys.${key}`)}</Label>
                    <Input
                      id={key}
                      type="password"
                      value={values[key] || ''}
                      onChange={(e) => setValues({ ...values, [key]: e.target.value })}
                      placeholder="••••••••"
                    />
                  </div>
                ))}
              </CardContent>
            </Card>
          ))}
          <Button onClick={handleSave}>
            {saved ? t('settings.saved') : t('settings.save')}
          </Button>
        </TabsContent>

        <TabsContent value="domains" className="space-y-6 mt-4">
          <Card>
            <CardHeader>
              <CardTitle>{t('settings.domains.title')}</CardTitle>
            </CardHeader>
            <CardContent className="space-y-4">
              {/* Add domain form */}
              <div className="flex gap-2 items-end">
                <div className="flex-1 space-y-1">
                  <Label>{t('settings.domains.serviceId')}</Label>
                  <Input
                    value={newServiceId}
                    onChange={(e) => setNewServiceId(e.target.value)}
                    placeholder="railway-service-id"
                  />
                </div>
                <div className="flex-1 space-y-1">
                  <Label>{t('settings.domains.domainName')}</Label>
                  <Input
                    value={newDomainName}
                    onChange={(e) => setNewDomainName(e.target.value)}
                    placeholder="app.example.com"
                  />
                </div>
                <Button onClick={handleAddDomain}>{t('settings.domains.add')}</Button>
              </div>
              {domainError && <p className="text-sm text-destructive">{domainError}</p>}

              {/* Domain list */}
              {domains.length === 0 ? (
                <p className="text-sm text-muted-foreground">{t('settings.domains.empty')}</p>
              ) : (
                <div className="space-y-2">
                  {domains.map((d) => (
                    <div key={d.id} className="flex items-center justify-between rounded-md border p-3">
                      <div className="space-y-1">
                        <div className="font-medium">{d.domain_name}</div>
                        <div className="text-xs text-muted-foreground">{d.service_id}</div>
                      </div>
                      <div className="flex items-center gap-2">
                        <Badge variant={statusVariant(d.status)}>
                          {t(`settings.domains.status.${d.status}`)}
                        </Badge>
                        <Button variant="ghost" size="sm" onClick={() => handleRemoveDomain(d.id)}>
                          {t('settings.domains.remove')}
                        </Button>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </CardContent>
          </Card>
        </TabsContent>
      </Tabs>
    </div>
  )
}
