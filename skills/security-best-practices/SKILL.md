---
name: security-best-practices
description: Use when implementing security measures — XSS prevention, CSRF protection, input validation, secure storage, authentication, session management, and database security. Applies to all web apps in the CDB ecosystem.
version: 0.1.0
---

# Security Best Practices

## Core Principles

1. **Never Trust User Input** — validate and sanitize all data, even from authenticated users
2. **Defense in Depth** — multiple layers of security; don't rely on one mechanism
3. **Principle of Least Privilege** — grant only the minimum permissions needed
4. **Secure by Default** — make the secure path the easy path
5. **Keep Secrets Secret** — never expose API keys, tokens, or credentials in client-side code

## XSS Prevention

### React & DOM
```typescript
// React automatically escapes JSX content — SAFE:
return <div>{user.name}</div>;

// DANGEROUS — bypass only with sanitized content:
return <div dangerouslySetInnerHTML={{ __html: sanitize(content) }} />;

// Sanitize with DOMPurify before using dangerouslySetInnerHTML
import DOMPurify from 'dompurify';

export function sanitizeHtml(html: string): string {
  return DOMPurify.sanitize(html, {
    ALLOWED_TAGS: ['b', 'i', 'em', 'strong', 'a', 'p', 'br', 'ul', 'ol', 'li'],
    ALLOWED_ATTR: ['href', 'title', 'target'],
  });
}
```

### URL Validation
```typescript
export function sanitizeUrl(url: string): string {
  const lower = url.trim().toLowerCase();
  const dangerous = ['javascript:', 'data:', 'vbscript:', 'file:'];
  if (dangerous.some(p => lower.startsWith(p))) return 'about:blank';

  // Allow relative URLs (paths starting with /)
  if (lower.startsWith('/')) return url;

  try {
    const parsed = new URL(url);
    if (!['http:', 'https:', 'mailto:'].includes(parsed.protocol)) return 'about:blank';
    return url;
  } catch {
    // Not an absolute URL and not a relative path — reject
    return 'about:blank';
  }
}

// Always use rel="noopener noreferrer" for external links
<a href={sanitizeUrl(href)} target="_blank" rel="noopener noreferrer">{children}</a>
```

## Input Validation

```typescript
import { z } from 'zod';

// Validate at system boundaries (user input, API responses)
const fileNameSchema = z
  .string()
  .min(1)
  .max(255)
  .regex(/^[^<>:"/\\|?*\x00-\x1f]+$/, 'Invalid characters')
  .refine(name => !name.startsWith('.'), 'Cannot start with dot');

const emailSchema = z.string().email();

const passwordSchema = z
  .string()
  .min(8)
  .regex(/[a-z]/, 'Needs lowercase')
  .regex(/[A-Z]/, 'Needs uppercase')
  .regex(/[0-9]/, 'Needs number')
  .regex(/[^a-zA-Z0-9]/, 'Needs special character');
```

## CSRF Protection

```typescript
// Generate CSRF token
export function generateCsrfToken(): string {
  const array = new Uint8Array(32);
  crypto.getRandomValues(array);
  return Array.from(array, b => b.toString(16).padStart(2, '0')).join('');
}

// Include in state-changing requests
async function apiCall(endpoint: string, data: unknown) {
  const token = sessionStorage.getItem('csrf-token');
  return fetch(endpoint, {
    method: 'POST',
    headers: {
      'Content-Type': 'application/json',
      ...(token && { 'X-CSRF-Token': token }),
    },
    body: JSON.stringify(data),
  });
}
```

## Content Security Policy

```typescript
// vite.config.ts — add CSP meta tag
{
  name: 'csp-plugin',
  transformIndexHtml(html) {
    return html.replace('<head>', `<head>
      <meta http-equiv="Content-Security-Policy" content="
        default-src 'self';
        script-src 'self' 'unsafe-inline';
        style-src 'self' 'unsafe-inline';
        img-src 'self' data: https:;
        connect-src 'self' https:;
      ">`);
    // NOTE: frame-ancestors must be set via HTTP header, not meta tags (browsers ignore it in meta).
    // Configure in your server/reverse proxy:
    //   Content-Security-Policy: frame-ancestors 'none';
  }
}
```

## Secure Storage

```typescript
// localStorage — non-sensitive, persists across sessions
// Use for: theme preferences, UI settings

// sessionStorage — sensitive, clears when tab closes
// Use for: temporary tokens, CSRF tokens, draft data

// NEVER store in client storage:
// - API keys / secrets
// - Passwords
// - Service role keys
// - Full access tokens (prefer httpOnly cookies)

// Safe pattern:
export const storage = {
  set: (key: string, value: unknown) => {
    try { localStorage.setItem(key, JSON.stringify(value)); } catch {}
  },
  get: <T>(key: string): T | null => {
    try {
      const item = localStorage.getItem(key);
      return item ? JSON.parse(item) : null;
    } catch { return null; }
  },
};
```

## Database Security (PostgreSQL)

```sql
-- Row Level Security — restrict access at DB level
ALTER TABLE resources ENABLE ROW LEVEL SECURITY;

-- Users can only see their own rows
CREATE POLICY "owner_select" ON resources FOR SELECT
  USING (current_user_id() = user_id);

CREATE POLICY "owner_insert" ON resources FOR INSERT
  WITH CHECK (current_user_id() = user_id);

CREATE POLICY "owner_update" ON resources FOR UPDATE
  USING (current_user_id() = user_id)
  WITH CHECK (current_user_id() = user_id);

CREATE POLICY "owner_delete" ON resources FOR DELETE
  USING (current_user_id() = user_id);

-- Parameterized queries — prevent SQL injection
-- BAD: `SELECT * FROM users WHERE id = '${userId}'`
-- GOOD (node-postgres):
const result = await pool.query(
  'SELECT * FROM users WHERE id = $1',
  [userId]
);

-- GOOD (Prisma — always parameterized by default):
const user = await prisma.user.findUnique({ where: { id: userId } });

-- Limit DB user permissions (principle of least privilege)
-- App DB user should NOT have DROP, CREATE, ALTER permissions
GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA public TO app_user;
```

## Session Management

```typescript
const INACTIVITY_TIMEOUT = 30 * 60 * 1000; // 30 minutes

export function useSessionTimeout(onTimeout: () => void) {
  const timer = useRef<ReturnType<typeof setTimeout>>();

  const reset = useCallback(() => {
    clearTimeout(timer.current);
    timer.current = setTimeout(onTimeout, INACTIVITY_TIMEOUT);
  }, [onTimeout]);

  useEffect(() => {
    const events = ['mousedown', 'keydown', 'scroll', 'touchstart'];
    events.forEach(e => document.addEventListener(e, reset));
    reset();
    return () => {
      clearTimeout(timer.current);
      events.forEach(e => document.removeEventListener(e, reset));
    };
  }, [reset]);
}

// Secure logout — clear all local data
export async function secureLogout() {
  await auth.signOut();
  localStorage.clear();
  sessionStorage.clear();
  window.location.href = '/login';
}
```

## Best Practices

**DO:**
- Validate all user input at system boundaries
- Use parameterized queries (prevent SQL injection)
- Enable PostgreSQL RLS policies for row-level access control
- Use HTTPS in production
- Implement session timeouts for inactivity
- Keep dependencies updated (security patches)
- Log security events (login, permission changes, errors)
- Use established auth libraries — don't roll your own

**DON'T:**
- Don't store sensitive data in localStorage
- Don't expose API keys in client code (use env vars)
- Don't trust client-side validation alone
- Don't log passwords, tokens, or PII
- Don't concatenate user input into queries
- Don't use weak password requirements
- Don't commit .env files to git

## Common Pitfalls

```typescript
// BAD — secret in client code
const apiKey = 'sk-secret-123456';

// GOOD — only public keys in client
const apiKey = import.meta.env.VITE_PUBLIC_KEY;

// BAD — no validation
const createItem = (name: string) => db.insert({ name });

// GOOD — validate first
const createItem = (name: string) => {
  const result = nameSchema.safeParse(name);
  if (!result.success) throw new Error('Invalid name');
  return db.insert({ name: result.data });
};
```

## When to Use This Skill

- Building auth flows or user-facing forms
- Handling file uploads
- Designing database schemas
- Reviewing code for security issues
- Setting up a new project
- Before production deployments
