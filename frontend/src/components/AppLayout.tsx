import { useEffect, useState } from 'react'
import { Outlet, useNavigate, Link, useLocation } from 'react-router-dom'
import { useTranslation } from 'react-i18next'
import { Bot, LayoutList, Kanban, Puzzle, Settings, LogOut } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'
import { ThemeToggle } from '@/components/ThemeToggle'
import { LanguageSwitcher } from '@/components/LanguageSwitcher'
import { RepoSelector } from '@/components/RepoSelector'
import { api } from '@/lib/api'

interface Repo {
  id: number
  workspace_id: number
  github_full_name: string
  deploy_provider: string
}

export function AppLayout() {
  const { t } = useTranslation()
  const navigate = useNavigate()
  const location = useLocation()
  const [repos, setRepos] = useState<Repo[]>([])
  const [selectedRepoId, setSelectedRepoId] = useState<number | null>(null)

  useEffect(() => {
    const token = localStorage.getItem('token')
    if (!token) {
      navigate('/login')
      return
    }
    api.getRepos().then(setRepos).catch(() => {})
  }, [navigate])

  function handleLogout() {
    localStorage.removeItem('token')
    navigate('/login')
  }

  return (
    <div className="min-h-screen flex flex-col">
      {/* Header */}
      <header className="border-b bg-card">
        <div className="flex items-center justify-between px-4 h-14">
          <div className="flex items-center gap-4">
            <Link to="/app" className="flex items-center gap-2 font-semibold">
              <Bot className="h-5 w-5" />
              <span>{t('app.name')}</span>
            </Link>
            <Separator orientation="vertical" className="h-6" />
            <RepoSelector
              repos={repos}
              selectedId={selectedRepoId}
              onSelect={setSelectedRepoId}
            />
          </div>
          <div className="flex items-center gap-1">
            <ThemeToggle />
            <LanguageSwitcher />
            <Button variant="ghost" size="icon" onClick={handleLogout} title={t('nav.logout')}>
              <LogOut className="h-4 w-4" />
            </Button>
          </div>
        </div>
      </header>

      <div className="flex flex-1">
        {/* Sidebar */}
        <aside className="w-56 border-r bg-card p-4 hidden md:block">
          <nav className="flex flex-col gap-1">
            <Link to="/app/issues">
              <Button
                variant={location.pathname.includes('/issues') ? 'secondary' : 'ghost'}
                className="w-full justify-start"
              >
                <LayoutList className="mr-2 h-4 w-4" />
                {t('nav.issues')}
              </Button>
            </Link>
            <Link to="/app/board">
              <Button
                variant={location.pathname.includes('/board') ? 'secondary' : 'ghost'}
                className="w-full justify-start"
              >
                <Kanban className="mr-2 h-4 w-4" />
                {t('nav.board')}
              </Button>
            </Link>
            <Link to="/app/skills">
              <Button
                variant={location.pathname.includes('/skills') ? 'secondary' : 'ghost'}
                className="w-full justify-start"
              >
                <Puzzle className="mr-2 h-4 w-4" />
                {t('nav.skills')}
              </Button>
            </Link>
            <Link to="/app/settings">
              <Button
                variant={location.pathname.includes('/settings') ? 'secondary' : 'ghost'}
                className="w-full justify-start"
              >
                <Settings className="mr-2 h-4 w-4" />
                {t('nav.settings')}
              </Button>
            </Link>
          </nav>
        </aside>

        {/* Main content */}
        <main className="flex-1 p-6">
          <Outlet context={{ selectedRepoId, repos }} />
        </main>
      </div>
    </div>
  )
}
