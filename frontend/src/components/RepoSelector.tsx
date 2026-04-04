import { useTranslation } from 'react-i18next'
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from '@/components/ui/select'

interface Repo {
  id: number
  github_full_name: string
}

interface RepoSelectorProps {
  repos: Repo[]
  selectedId: number | null
  onSelect: (id: number) => void
}

export function RepoSelector({ repos, selectedId, onSelect }: RepoSelectorProps) {
  const { t } = useTranslation()

  return (
    <Select
      value={selectedId?.toString() ?? ''}
      onValueChange={(val) => onSelect(Number(val))}
    >
      <SelectTrigger className="w-[240px]">
        <SelectValue placeholder={t('repos.selectRepo')} />
      </SelectTrigger>
      <SelectContent>
        {repos.length === 0 ? (
          <SelectItem value="none" disabled>
            {t('repos.noRepos')}
          </SelectItem>
        ) : (
          repos.map((repo) => (
            <SelectItem key={repo.id} value={repo.id.toString()}>
              {repo.github_full_name}
            </SelectItem>
          ))
        )}
      </SelectContent>
    </Select>
  )
}
