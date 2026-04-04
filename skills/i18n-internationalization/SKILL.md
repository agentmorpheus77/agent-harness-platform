---
name: i18n-internationalization
description: Use when implementing internationalization — react-i18next setup, translation management, pluralization, date/time/number formatting, language switching, and multilingual React applications.
version: 0.1.0
---

# Internationalization (i18n)

## Core Principles

1. **Externalize All Text** — never hardcode UI strings; always use translation keys
2. **Context Matters** — provide context for ambiguous terms (e.g., "close" = button vs verb)
3. **Plan for Text Expansion** — German/Finnish can be 30–50% longer than English; use flexible layouts
4. **Format Culture-Specific Data** — dates, numbers, currencies must match locale
5. **Start Early** — retrofitting i18n is much harder than building it in from the start

## Setup (react-i18next)

```typescript
// src/i18n/config.ts
import i18n from 'i18next';
import { initReactI18next } from 'react-i18next';
import LanguageDetector from 'i18next-browser-languagedetector';
import de from './locales/de/translation.json';
import en from './locales/en/translation.json';

i18n
  .use(LanguageDetector)
  .use(initReactI18next)
  .init({
    resources: {
      de: { translation: de },
      en: { translation: en },
    },
    fallbackLng: 'de',
    debug: import.meta.env.DEV,
    interpolation: { escapeValue: false }, // React already escapes
    detection: {
      order: ['localStorage', 'navigator'],
      caches: ['localStorage'],
    },
  });

export default i18n;
```

```typescript
// src/main.tsx
import './i18n/config'; // Initialize before rendering
```

### TypeScript Types
```typescript
// src/i18n/types.ts
import 'react-i18next';
import type enTranslation from './locales/en/translation.json';

declare module 'react-i18next' {
  interface CustomTypeOptions {
    defaultNS: 'translation';
    resources: { translation: typeof enTranslation };
  }
}
```

## Translation File Structure

```json
// src/i18n/locales/de/translation.json
{
  "common": {
    "actions": {
      "save": "Speichern",
      "cancel": "Abbrechen",
      "delete": "Löschen",
      "close": "Schließen"
    },
    "status": {
      "loading": "Lädt...",
      "error": "Fehler"
    }
  },
  "auth": {
    "login": "Anmelden",
    "logout": "Abmelden",
    "email": "E-Mail-Adresse",
    "password": "Passwort",
    "errors": {
      "invalidCredentials": "Ungültige Anmeldedaten"
    }
  },
  "fileManager": {
    "title": "Dateimanager",
    "empty": "Dieser Ordner ist leer",
    "fileCount_one": "{{count}} Datei",
    "fileCount_other": "{{count}} Dateien",
    "deleteConfirm": "\"{{fileName}}\" wirklich löschen?"
  }
}
```

## Usage in Components

```typescript
import { useTranslation } from 'react-i18next';

function FileManager() {
  const { t } = useTranslation();

  return (
    <div>
      <h1>{t('fileManager.title')}</h1>
      <button>{t('common.actions.save')}</button>
      <button>{t('common.actions.cancel')}</button>
    </div>
  );
}
```

## Pluralization

```typescript
// Translation file
{
  "items_one": "{{count}} Element",
  "items_other": "{{count}} Elemente",
  "items_zero": "Keine Elemente"
}

// Usage — i18next picks the right form automatically
<p>{t('items', { count: selectedCount })}</p>
// count=0 → "Keine Elemente"
// count=1 → "1 Element"
// count=5 → "5 Elemente"
```

## Interpolation

```json
{
  "welcome": "Willkommen, {{name}}!",
  "uploadProgress": "{{fileName}} wird hochgeladen... {{progress}}%",
  "deleteConfirm": "\"{{fileName}}\" wirklich löschen?",
  "joinedDate": "Mitglied seit {{date}}"
}
```

```typescript
// Variable interpolation
t('welcome', { name: user.name })
t('deleteConfirm', { fileName: file.name })
t('uploadProgress', { fileName, progress: 75 })
```

## Date, Number & Currency Formatting

```typescript
// src/hooks/useFormatting.ts
export function useFormatting() {
  const { i18n } = useTranslation();
  const locale = i18n.language;

  return {
    formatDate: (date: Date, options?: Intl.DateTimeFormatOptions) =>
      new Intl.DateTimeFormat(locale, options).format(date),

    formatRelativeTime: (date: Date) => {
      const rtf = new Intl.RelativeTimeFormat(locale, { numeric: 'auto' });
      const diffMs = date.getTime() - Date.now();
      const diffMin = diffMs / 60000;
      const diffH = diffMin / 60;
      const diffD = diffH / 24;

      if (Math.abs(diffD) >= 1) return rtf.format(Math.round(diffD), 'day');
      if (Math.abs(diffH) >= 1) return rtf.format(Math.round(diffH), 'hour');
      return rtf.format(Math.round(diffMin), 'minute');
    },

    formatNumber: (value: number, options?: Intl.NumberFormatOptions) =>
      new Intl.NumberFormat(locale, options).format(value),

    formatCurrency: (value: number, currency = 'EUR') =>
      new Intl.NumberFormat(locale, { style: 'currency', currency }).format(value),

    formatFileSize: (bytes: number) => {
      const units = ['B', 'KB', 'MB', 'GB'];
      let size = bytes, i = 0;
      while (size >= 1024 && i < units.length - 1) { size /= 1024; i++; }
      return `${new Intl.NumberFormat(locale, { maximumFractionDigits: 1 }).format(size)} ${units[i]}`;
    },
  };
}
```

## Language Switcher

```typescript
export function LanguageSwitcher() {
  const { i18n } = useTranslation();

  const languages = [
    { code: 'de', label: 'Deutsch' },
    { code: 'en', label: 'English' },
  ];

  const changeLanguage = async (code: string) => {
    await i18n.changeLanguage(code);
    document.documentElement.lang = code;
  };

  return (
    <select value={i18n.language} onChange={e => changeLanguage(e.target.value)}>
      {languages.map(lang => (
        <option key={lang.code} value={lang.code}>{lang.label}</option>
      ))}
    </select>
  );
}
```

## Missing Translation Detection

```typescript
i18n.init({
  saveMissing: import.meta.env.DEV,
  missingKeyHandler: (lngs, ns, key) => {
    if (import.meta.env.DEV) {
      console.warn(`Missing translation: [${ns}] ${key} for ${lngs.join(', ')}`);
    }
  },
});
```

## Best Practices

**DO:**
- Externalize all user-facing text into translation files
- Use meaningful, hierarchical translation keys (`auth.errors.invalidCredentials`)
- Provide context for ambiguous terms
- Use `Intl` API for dates, numbers, currencies
- Test UI with German — it's typically 30% longer than English
- Keep translation files in sync — update all languages together
- Use pluralization rules; don't hardcode English plural logic

**DON'T:**
- Don't hardcode text in components
- Don't concatenate translated strings (`t('hello') + name` breaks word order)
- Don't assume left-to-right reading direction for all languages
- Don't translate programmatic values (IDs, enum values)
- Don't over-nest translation keys (max 3 levels)
- Don't use fixed widths that break with longer languages

## Common Pitfalls

```typescript
// BAD — concatenation breaks in different languages
const msg = t('hello') + ' ' + name + '!';

// GOOD — use interpolation
const msg = t('greeting', { name }); // "Hallo {{name}}!"

// BAD — English-only plural
const text = `${count} file${count === 1 ? '' : 's'}`;

// GOOD — i18next handles all languages
const text = t('files', { count }); // Uses _one, _other rules

// BAD — fixed width breaks German text
.button { width: 100px; }

// GOOD — flexible layout
.button { min-width: 100px; padding: 0.5rem 1rem; }
```

## Package.json Scripts

```json
{
  "scripts": {
    "i18n:extract": "i18next-scanner --config i18next-scanner.config.js",
    "i18n:check": "node scripts/check-missing-translations.js"
  }
}
```

## When to Use This Skill

- Starting a new project (set up i18n from day 1)
- Adding new features (externalize all text)
- Adding a new language
- Reviewing code for hardcoded strings
- Displaying dates, numbers, or currencies
- Building forms with locale-specific validation
