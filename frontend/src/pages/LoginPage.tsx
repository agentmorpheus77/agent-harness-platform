import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Bot } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle, CardFooter } from '@/components/ui/card'
import { Input } from '@/components/ui/input'
import { Label } from '@/components/ui/label'
import { ThemeToggle } from '@/components/ThemeToggle'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'
import { api } from '@/lib/api'

export function LoginPage() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const [isRegister, setIsRegister] = useState(false)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState('')

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    setError('')
    try {
      const fn = isRegister ? api.register : api.login
      const { access_token } = await fn(email, password)
      localStorage.setItem('token', access_token)
      navigate('/app/issues')
    } catch (err) {
      setError(isRegister ? t('auth.registerError') : t('auth.loginError'))
      console.error(err)
    }
  }

  return (
    <div className="min-h-screen flex flex-col items-center justify-center p-4">
      <div className="absolute top-4 right-4 flex gap-1">
        <ThemeToggle />
        <LanguageSwitcher />
      </div>
      <Card className="w-full max-w-md">
        <CardHeader className="text-center">
          <div className="flex justify-center mb-2">
            <Bot className="h-10 w-10" />
          </div>
          <CardTitle className="text-2xl">{t('app.name')}</CardTitle>
          <p className="text-muted-foreground text-sm">{t('app.tagline')}</p>
        </CardHeader>
        <CardContent>
          <form onSubmit={handleSubmit} className="space-y-4">
            <div className="space-y-2">
              <Label htmlFor="email">{t('auth.email')}</Label>
              <Input
                id="email"
                type="email"
                value={email}
                onChange={(e) => setEmail(e.target.value)}
                required
              />
            </div>
            <div className="space-y-2">
              <Label htmlFor="password">{t('auth.password')}</Label>
              <Input
                id="password"
                type="password"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                required
              />
            </div>
            {error && <p className="text-destructive text-sm">{error}</p>}
            <Button type="submit" className="w-full">
              {isRegister ? t('auth.register') : t('auth.login')}
            </Button>
            <p className="text-center text-sm text-muted-foreground">
              {isRegister ? t('auth.hasAccount') : t('auth.noAccount')}{' '}
              <button
                type="button"
                className="underline text-foreground"
                onClick={() => setIsRegister(!isRegister)}
              >
                {isRegister ? t('auth.login') : t('auth.register')}
              </button>
            </p>
          </form>
        </CardContent>
        <CardFooter className="justify-center">
          <p className="text-muted-foreground text-xs">
            v1.0.0 •{' '}
            <a
              href="https://github.com/agent-harness/agent-harness-platform"
              target="_blank"
              rel="noopener noreferrer"
              className="underline"
            >
              GitHub
            </a>
          </p>
        </CardFooter>
      </Card>
    </div>
  )
}
