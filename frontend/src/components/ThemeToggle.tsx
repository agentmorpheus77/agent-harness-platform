import { useState } from 'react'
import { useTranslation } from 'react-i18next'
import { Moon, Sun, Monitor } from 'lucide-react'
import { Button } from '@/components/ui/button'
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuTrigger,
} from '@/components/ui/dropdown-menu'
import { type Theme, getStoredTheme, setTheme } from '@/lib/theme'

export function ThemeToggle() {
  const { t } = useTranslation()
  const [current, setCurrent] = useState<Theme>(getStoredTheme())

  function handleChange(theme: Theme) {
    setTheme(theme)
    setCurrent(theme)
  }

  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button variant="ghost" size="icon">
          {current === 'dark' ? <Moon className="h-4 w-4" /> : current === 'light' ? <Sun className="h-4 w-4" /> : <Monitor className="h-4 w-4" />}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end">
        <DropdownMenuItem onClick={() => handleChange('light')}>
          <Sun className="mr-2 h-4 w-4" /> {t('theme.light')}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleChange('dark')}>
          <Moon className="mr-2 h-4 w-4" /> {t('theme.dark')}
        </DropdownMenuItem>
        <DropdownMenuItem onClick={() => handleChange('system')}>
          <Monitor className="mr-2 h-4 w-4" /> {t('theme.system')}
        </DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
