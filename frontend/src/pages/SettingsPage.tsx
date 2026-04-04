import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { Button } from '@/components/ui/button'
import { api } from '@/lib/api'

const SETTING_KEYS = ['openrouter_api_key', 'github_token', 'railway_api_key', 'gemini_api_key'] as const

export function SettingsPage() {
  const { t } = useTranslation()
  const [values, setValues] = useState<Record<string, string>>({})
  const [saved, setSaved] = useState(false)

  useEffect(() => {
    api.getSettings().then(({ settings }) => setValues(settings)).catch(() => {})
  }, [])

  async function handleSave() {
    const items = SETTING_KEYS
      .filter((key) => values[key] !== undefined && values[key] !== '')
      .map((key) => ({ key, value: values[key] }))
    await api.updateSettings(items)
    setSaved(true)
    setTimeout(() => setSaved(false), 2000)
  }

  return (
    <div>
      <h1 className="text-2xl font-bold mb-6">{t('settings.title')}</h1>
      <Card>
        <CardHeader>
          <CardTitle>{t('settings.apiKeys')}</CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          {SETTING_KEYS.map((key) => (
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
          <Button onClick={handleSave}>
            {saved ? t('settings.saved') : t('settings.save')}
          </Button>
        </CardContent>
      </Card>
    </div>
  )
}
