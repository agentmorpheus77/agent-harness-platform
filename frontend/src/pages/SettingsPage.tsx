import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
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

export function SettingsPage() {
  const { t } = useTranslation()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getSettings().then(({ settings }) => setValues(settings)).catch(() => {})
  }, [])

  async function handleSave() {
    const items = ALL_KEYS
      .filter((key) => values[key] !== undefined && values[key] !== '')
      .map((key) => ({ key, value: values[key] }))
    await api.updateSettings(items)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-bold">{t('settings.title')}</h1>
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
    </div>
  )
}
