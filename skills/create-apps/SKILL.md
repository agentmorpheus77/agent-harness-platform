---
name: create-apps
description: Use when starting a new web or mobile application — tech stack selection, project structure, authentication, database setup, API integration, testing, deployment, and project scaffolding decisions.
version: 0.1.0
---

# Create Apps

## Phase 1: Before Writing Code

### Requirements Analysis
- **Define the problem**: What specific problem does this solve?
- **Target users**: Who will use this?
- **MVP features**: List 3–5 essential features only
- **Success metrics**: How do you measure success?
- **Constraints**: Platform, budget, team size, timeline

## Phase 2: Tech Stack Selection

### Frontend (React recommended for most projects)
```bash
# Modern React + Vite
npm create vite@latest my-app -- --template react-ts

# Next.js for SSR/SSG
npx create-next-app@latest my-app --typescript --tailwind --app
```

**Essential dependencies:**
| Category | Recommended |
|----------|------------|
| Styling | Tailwind CSS |
| State | Zustand (simple) / Redux Toolkit (complex) |
| Forms | React Hook Form + Zod |
| Data fetching | TanStack Query |
| UI Components | shadcn/ui + Radix UI |
| Routing | React Router (SPA) / Next.js built-in |

### Backend
```bash
# Node.js options
npm install express cors dotenv     # Express (traditional)
npm i -g @nestjs/cli && nest new    # NestJS (enterprise)
pip install fastapi uvicorn         # FastAPI (Python)
```

**BaaS for fast MVPs:**
- **Supabase** — hosted PostgreSQL + Auth + Storage + Realtime (good for prototypes)
- **Firebase** — NoSQL + Auth + Hosting
- **Appwrite** — open-source alternative

### Database
| Use case | Choice |
|----------|--------|
| General purpose | PostgreSQL (self-hosted or managed) |
| Flexible schema / prototyping | MongoDB |
| Local-first / edge | SQLite |
| Caching / sessions | Redis |

## Phase 3: Project Structure

```
# Frontend (React)
src/
├── components/
│   ├── ui/           # Base components (Button, Input, etc.)
│   ├── features/     # Feature-specific components
│   └── layout/       # Header, Footer, Sidebar
├── pages/            # Route pages
├── hooks/            # Custom hooks
├── services/         # API calls, external services
├── store/            # State management
├── types/            # TypeScript types
├── lib/              # Utilities (cn, formatters, etc.)
└── config/           # App configuration

# Backend (Node.js)
src/
├── routes/           # API route handlers
├── controllers/      # Business logic
├── models/           # Database models/schemas
├── middleware/        # Auth, logging, validation
├── services/         # External integrations
└── utils/            # Helpers
```

## Phase 4: Essential Setup

```json
// tsconfig.json
{
  "compilerOptions": {
    "strict": true,
    "paths": { "@/*": ["./src/*"] }
  }
}
```

```bash
# .env.example (commit this)
DATABASE_URL=postgresql://localhost:5432/myapp
API_KEY=your_api_key_here

# .env.local (gitignored)
DATABASE_URL=postgresql://user:password@localhost:5432/myapp
API_KEY=actual_secret_key
```

```bash
npm install -D eslint prettier eslint-config-prettier
# .prettierrc
{ "semi": true, "singleQuote": true, "tabWidth": 2, "trailingComma": "es5" }
```

## Phase 5: Core Features

### Authentication (use a provider)
```typescript
// Preferred: use an auth library (Clerk, Auth0, Passport.js) or self-hosted solution
// Example with node-postgres + bcrypt:
const user = await pool.query('SELECT * FROM users WHERE email = $1', [email]);
const valid = await bcrypt.compare(password, user.rows[0].password_hash);

// DIY JWT (only if necessary)
const token = jwt.sign({ userId }, process.env.JWT_SECRET, { expiresIn: '7d' });
const middleware = (req, res, next) => {
  try {
    const token = req.headers.authorization?.split(' ')[1];
    if (!token) return res.status(401).json({ error: 'No token provided' });
    req.user = jwt.verify(token, process.env.JWT_SECRET);
    next();
  } catch (err) {
    return res.status(401).json({ error: 'Invalid or expired token' });
  }
};
```

### Database (Prisma)
```bash
npm install prisma @prisma/client && npx prisma init
```

```prisma
model User {
  id        String   @id @default(cuid())
  email     String   @unique
  name      String?
  posts     Post[]
  createdAt DateTime @default(now())
}
```

```typescript
const user = await prisma.user.create({ data: { email, name } });
const users = await prisma.user.findMany({ include: { posts: true } });
```

### API Integration (TanStack Query)
```typescript
function Posts() {
  const { data, isLoading, error } = useQuery({
    queryKey: ['posts'],
    queryFn: async () => {
      const r = await fetch('/api/posts');
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
  });

  const create = useMutation({
    mutationFn: async (post) => {
      const r = await fetch('/api/posts', { method: 'POST', body: JSON.stringify(post) });
      if (!r.ok) throw new Error(`HTTP ${r.status}`);
      return r.json();
    },
    onSuccess: () => queryClient.invalidateQueries(['posts']),
  });

  if (isLoading) return <Spinner />;
  if (error) return <ErrorState />;
  return <PostList posts={data} />;
}
```

### Form Handling
```typescript
const schema = z.object({
  email: z.string().email(),
  password: z.string().min(8),
});

function LoginForm() {
  const { register, handleSubmit, formState: { errors } } = useForm({
    resolver: zodResolver(schema),
  });
  return (
    <form onSubmit={handleSubmit(onSubmit)}>
      <input {...register('email')} />
      {errors.email && <span>{errors.email.message}</span>}
    </form>
  );
}
```

## Phase 6: Testing

```bash
npm install -D vitest @testing-library/react @testing-library/jest-dom
npm init playwright@latest
```

```typescript
// Unit test
test('formats currency correctly', () => {
  expect(formatCurrency(1234.5)).toBe('€1.234,50');
});

// E2E test
test('user can create post', async ({ page }) => {
  await page.goto('/');
  await page.click('text=New Post');
  await page.fill('input[name="title"]', 'My Post');
  await page.click('button[type="submit"]');
  await expect(page.locator('text=My Post')).toBeVisible();
});
```

## Phase 7: Deployment

| Target | Use | Command |
|--------|-----|---------|
| Railway | Fastest for full-stack MVPs | Push to GitHub → auto-deploy |
| Vercel | Best for Next.js / React | `npx vercel` |
| Render | Simple, free tier | Connect GitHub |
| Netlify | Static sites | `ntl deploy` |

## Best Practices

### Code Quality
- TypeScript strict mode
- React Error Boundaries
- Validate inputs with Zod
- Always handle loading + error states
- Functions < 200 lines, single responsibility

### Security
- Never commit secrets — use .env + gitignore
- Sanitize inputs (prevent XSS)
- Rate limit API endpoints
- Hash passwords (bcrypt, salt ≥ 10)
- Configure CORS to trusted origins only

### Performance
- Code splitting (lazy routes)
- Image optimization (WebP, lazy loading)
- Database indexes on queried fields
- Cache with TanStack Query
- Paginate large datasets
- Debounce search/filter inputs

## Quick Start Checklist

- [ ] Define MVP (3–5 features)
- [ ] Choose tech stack
- [ ] Set up project structure
- [ ] Configure TypeScript + ESLint + Prettier
- [ ] Set up Git + .gitignore + .env.example
- [ ] Implement authentication
- [ ] Create database schema
- [ ] Build API endpoints
- [ ] Create frontend components
- [ ] Add loading and error states
- [ ] Write tests for critical paths
- [ ] Set up CI/CD
- [ ] Deploy to production
- [ ] Set up error monitoring (Sentry)
- [ ] Document setup in README

## When to Use This Skill

- Starting a new project from scratch
- Choosing tech stack and architecture
- Implementing auth, database, or core features
- Setting up project scaffolding
- Reviewing project structure and conventions
