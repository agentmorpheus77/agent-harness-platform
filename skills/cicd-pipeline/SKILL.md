---
name: cicd-pipeline
description: Use when implementing or reviewing CI/CD pipelines — GitHub Actions workflows, code quality gates, test automation, environment management, bundle size monitoring, preview deployments, and rollback strategies.
version: 0.1.0
---

# CI/CD Pipeline

## Core Principles

1. **Automate Everything** — manual processes are error-prone; automate testing, building, deploying
2. **Fail Fast** — run quick checks (lint, types) before expensive ones (tests, build)
3. **Keep Pipelines Fast** — feedback within minutes, not hours; use parallel jobs
4. **Make Deployments Safe** — preview environments, smoke tests, rollback strategy ready
5. **Monitor After Deploy** — verify health after every deployment

## GitHub Actions — CI Workflow

```yaml
# .github/workflows/ci.yml
name: CI

on:
  push:
    branches: [main, staging]
  pull_request:
    branches: [main, staging]

concurrency:
  group: ${{ github.workflow }}-${{ github.ref }}
  cancel-in-progress: true

jobs:
  # Run in parallel for speed
  lint:
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run lint
      - run: npm run type-check

  test:
    runs-on: ubuntu-latest
    timeout-minutes: 15
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run test:coverage
      - uses: codecov/codecov-action@v4
        with:
          files: ./coverage/coverage-final.json

  build:
    needs: [lint, test]
    runs-on: ubuntu-latest
    timeout-minutes: 10
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npm run build
        env:
          VITE_API_URL: ${{ secrets.VITE_API_URL }}
      - uses: actions/upload-artifact@v4
        with: { name: build, path: dist/, retention-days: 7 }

  e2e:
    needs: [build]
    runs-on: ubuntu-latest
    timeout-minutes: 20
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci
      - run: npx playwright install --with-deps
      - run: npm run test:e2e
      - uses: actions/upload-artifact@v4
        if: always()
        with: { name: playwright-report, path: playwright-report/ }
```

## Deployment Workflow

```yaml
# .github/workflows/deploy.yml
name: Deploy

on:
  push:
    branches: [main]

jobs:
  deploy-production:
    runs-on: ubuntu-latest
    environment:
      name: production
      url: https://your-app.com

    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-node@v4
        with: { node-version: '20', cache: 'npm' }
      - run: npm ci && npm test
      - run: npm run build
        env:
          NODE_ENV: production
          VITE_API_URL: ${{ secrets.PROD_API_URL }}
      - name: Deploy
        run: | # Replace with your deploy command (Railway, Vercel, Docker, etc.)
          npx vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
      - name: Verify health
        run: |
          sleep 10
          curl -f https://your-app.com/health || exit 1
```

## Code Quality Gates

```typescript
// .eslintrc.cjs
module.exports = {
  extends: [
    'eslint:recommended',
    'plugin:@typescript-eslint/recommended',
    'plugin:react-hooks/recommended',
  ],
  rules: {
    'no-console': process.env.NODE_ENV === 'production' ? 'error' : 'warn',
    '@typescript-eslint/no-explicit-any': 'error',
    '@typescript-eslint/no-unused-vars': ['error', { argsIgnorePattern: '^_' }],
    'react-hooks/rules-of-hooks': 'error',
    'react-hooks/exhaustive-deps': 'warn',
  },
};
```

```json
// tsconfig.json — enforce strict mode
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true
  }
}
```

## Bundle Size Monitoring

```yaml
# .github/workflows/bundle-size.yml
name: Bundle Size

on:
  pull_request:
    branches: [main]

jobs:
  size:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - run: npm ci && npm run build
      - uses: andresz1/size-limit-action@v1
        with:
          github_token: ${{ secrets.GITHUB_TOKEN }}
```

```json
// package.json
{
  "size-limit": [
    { "name": "Main bundle", "path": "dist/assets/index-*.js", "limit": "200 KB" },
    { "name": "CSS", "path": "dist/assets/index-*.css", "limit": "50 KB" }
  ]
}
```

## Environment Variables

```yaml
# GitHub Secrets (Settings → Secrets → Actions)
# Required secrets — adjust per project:
PROD_API_URL          # Production API base URL
STAGING_API_URL       # Staging API base URL
VERCEL_TOKEN          # Deployment token
SENTRY_AUTH_TOKEN     # Error monitoring
```

```typescript
// src/config/env.ts — validate at startup
import { z } from 'zod';

const envSchema = z.object({
  VITE_API_URL: z.string().url(),
  VITE_ENV: z.enum(['development', 'staging', 'production']),
});

export const env = envSchema.parse(import.meta.env);
```

## Database Migrations in CI

```yaml
# Only run when migration files change
on:
  push:
    paths: ['migrations/**']

jobs:
  migrate:
    steps:
      - run: npm run db:migrate:staging
      - run: npm run db:migrate # production, only on main
```

## Rollback Strategy

```yaml
# .github/workflows/rollback.yml
name: Rollback

on:
  workflow_dispatch:
    inputs:
      version:
        description: 'Version to rollback to (e.g., v1.2.0)'
        required: true

jobs:
  rollback:
    runs-on: ubuntu-latest
    environment: production
    steps:
      - uses: actions/checkout@v4
        with: { ref: ${{ inputs.version }} }
      - run: npm ci && npm run build
        env: { VITE_API_URL: ${{ secrets.PROD_API_URL }} }
      - name: Deploy rollback version
        run: npx vercel --prod --token ${{ secrets.VERCEL_TOKEN }}
```

```bash
# Manual rollback steps
git tag | sort -V | tail -5          # Find last good version
# Trigger rollback workflow via GitHub UI → Actions → Rollback
```

## Best Practices

**DO:**
- Run tests before every deployment
- Use separate environments (dev → staging → production)
- Implement code quality gates (lint, type-check, coverage)
- Monitor bundle size on PRs
- Use preview deployments for PRs
- Run migrations before app deployment
- Implement health checks post-deploy
- Tag all production releases
- Have rollback strategy ready and tested

**DON'T:**
- Don't skip tests to deploy faster
- Don't commit secrets to repository
- Don't deploy directly to production without staging
- Don't ignore failing tests or lint errors
- Don't deploy without smoke tests
- Don't ignore bundle size increases

## Common Pitfalls

```yaml
# BAD — missing env vars, build fails silently
- run: npm run build

# GOOD — explicitly pass required vars
- run: npm run build
  env:
    VITE_API_URL: ${{ secrets.VITE_API_URL }}

# BAD — sequential jobs (45 min)
- run: npm run test:unit
- run: npm run test:integration
- run: npm run test:e2e

# GOOD — parallel jobs (15 min)
jobs:
  unit: { steps: [{ run: npm run test:unit }] }
  integration: { steps: [{ run: npm run test:integration }] }
  e2e: { needs: [unit, integration], steps: [{ run: npm run test:e2e }] }
```

## When to Use This Skill

- Setting up a new project (configure CI early)
- Adding new deployment targets
- Improving pipeline speed
- Adding quality gates
- Handling production incidents (use rollback workflow)
- Code reviews (verify CI passes)
