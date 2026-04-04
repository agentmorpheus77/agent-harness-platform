import { useEffect, useState } from 'react'
import { useTranslation } from 'react-i18next'
import { RefreshCw, Search, Package } from 'lucide-react'
import { Button } from '@/components/ui/button'
import { Input } from '@/components/ui/input'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { api } from '@/lib/api'
import toast from 'react-hot-toast'

interface Skill {
  name: string
  description: string
  version: string
  status: string
  path: string
  keywords: string[]
}

function statusColor(status: string) {
  switch (status) {
    case 'loaded':
      return 'bg-green-500/20 text-green-400 border-green-500/30'
    case 'outdated':
      return 'bg-orange-500/20 text-orange-400 border-orange-500/30'
    default:
      return 'bg-muted text-muted-foreground'
  }
}

function shortenPath(path: string) {
  const home = path.indexOf('/Users/')
  if (home >= 0) {
    const rest = path.substring(path.indexOf('/', home + 7))
    return '~' + rest
  }
  return path
}

export function SkillsPage() {
  const { t } = useTranslation()
  const [skills, setSkills] = useState<Skill[]>([])
  const [search, setSearch] = useState('')
  const [updating, setUpdating] = useState(false)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    loadSkills()
  }, [])

  async function loadSkills() {
    try {
      const data = await api.getSkills()
      setSkills(data)
    } catch {
      // Skills dirs may not exist yet
      setSkills([])
    } finally {
      setLoading(false)
    }
  }

  async function handleUpdateAll() {
    setUpdating(true)
    try {
      await api.updateSkills()
      toast.success(t('skills.updated'))
      await loadSkills()
    } catch {
      toast.error(t('skills.updateFailed'))
    } finally {
      setUpdating(false)
    }
  }

  const filtered = skills.filter(
    (s) =>
      s.name.toLowerCase().includes(search.toLowerCase()) ||
      s.description.toLowerCase().includes(search.toLowerCase())
  )

  return (
    <div className="space-y-6">
      {/* Header */}
      <div className="flex items-center justify-between">
        <h1 className="text-2xl font-bold">{t('skills.title')}</h1>
        <Button onClick={handleUpdateAll} disabled={updating} variant="outline">
          <RefreshCw className={`mr-2 h-4 w-4 ${updating ? 'animate-spin' : ''}`} />
          {t('skills.updateAll')}
        </Button>
      </div>

      {/* Search */}
      <div className="relative">
        <Search className="absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-muted-foreground" />
        <Input
          placeholder={t('skills.search')}
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          className="pl-10"
        />
      </div>

      {/* Grid */}
      {loading ? (
        <p className="text-muted-foreground">{t('skills.loading')}</p>
      ) : filtered.length === 0 ? (
        <p className="text-muted-foreground">{t('skills.noSkills')}</p>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-4">
          {filtered.map((skill) => (
            <Card key={skill.name} className="flex flex-col">
              <CardHeader className="pb-3">
                <div className="flex items-start justify-between">
                  <div className="flex items-center gap-2">
                    <Package className="h-4 w-4 text-muted-foreground" />
                    <CardTitle className="text-base">{skill.name}</CardTitle>
                  </div>
                  <div className="flex items-center gap-1.5">
                    <Badge variant="outline" className="text-xs">
                      v{skill.version}
                    </Badge>
                    <Badge variant="outline" className={`text-xs ${statusColor(skill.status)}`}>
                      {t(`skills.status.${skill.status}`)}
                    </Badge>
                  </div>
                </div>
              </CardHeader>
              <CardContent className="flex-1 space-y-2">
                <p className="text-sm text-muted-foreground line-clamp-2">
                  {skill.description || t('skills.noDescription')}
                </p>
                <p className="text-xs text-muted-foreground/70 truncate" title={skill.path}>
                  {shortenPath(skill.path)}
                </p>
              </CardContent>
            </Card>
          ))}
        </div>
      )}
    </div>
  )
}
