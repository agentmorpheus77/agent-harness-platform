---
name: testing-qa
description: Use when writing tests or reviewing test coverage — unit tests with Vitest, integration tests, E2E tests with Playwright, test patterns, and quality assurance for React/TypeScript applications.
version: 0.1.0
---

# Testing & Quality Assurance

## Core Principles

### Test Pyramid
- **70% Unit Tests** — fast, isolated, functions & components
- **20% Integration Tests** — component interactions, data flow
- **10% E2E Tests** — critical user journeys

### TDD Cycle
```
Red → Green → Refactor
1. Write failing test
2. Make test pass with minimal code
3. Refactor while keeping tests green
```

## Setup

```json
{
  "devDependencies": {
    "vitest": "^1.0.0",
    "@testing-library/react": "^14.0.0",
    "@testing-library/jest-dom": "^6.0.0",
    "@testing-library/user-event": "^14.0.0",
    "happy-dom": "^12.0.0",
    "@playwright/test": "^1.40.0"
  }
}
```

```typescript
// vitest.config.ts
export default defineConfig({
  plugins: [react()],
  test: {
    globals: true,
    environment: 'happy-dom',
    setupFiles: ['./src/test/setup.ts'],
    coverage: {
      provider: 'v8',
      thresholds: { lines: 80, functions: 80, branches: 75, statements: 80 }
    }
  },
  resolve: { alias: { '@': path.resolve(__dirname, './src') } }
});
```

```typescript
// src/test/setup.ts
import '@testing-library/jest-dom';
import { cleanup } from '@testing-library/react';
import { afterEach, vi } from 'vitest';

afterEach(() => cleanup());

Object.defineProperty(window, 'matchMedia', {
  writable: true,
  value: vi.fn().mockImplementation(query => ({
    matches: false, media: query, onchange: null,
    addListener: vi.fn(), removeListener: vi.fn(),
    addEventListener: vi.fn(), removeEventListener: vi.fn(),
    dispatchEvent: vi.fn(),
  })),
});
```

## Unit Testing

### Testing Pure Functions
```typescript
import { describe, it, expect } from 'vitest';

describe('formatDate()', () => {
  it('formats ISO date to locale string', () => {
    expect(formatDate('2025-10-27T10:30:00Z', 'de-DE')).toBe('27.10.2025');
  });

  it('handles invalid date gracefully', () => {
    expect(formatDate('invalid', 'de-DE')).toBe('Ungültiges Datum');
  });
});
```

### Testing React Components
```typescript
describe('Button', () => {
  it('renders with text', () => {
    render(<Button>Click me</Button>);
    expect(screen.getByRole('button', { name: /click me/i })).toBeInTheDocument();
  });

  it('calls onClick when clicked', async () => {
    const handleClick = vi.fn();
    const user = userEvent.setup();

    render(<Button onClick={handleClick}>Click</Button>);
    await user.click(screen.getByRole('button'));

    expect(handleClick).toHaveBeenCalledTimes(1);
  });

  it('is disabled when disabled prop is true', () => {
    render(<Button disabled>Disabled</Button>);
    expect(screen.getByRole('button')).toBeDisabled();
  });
});
```

### Testing Custom Hooks
```typescript
import { renderHook, act } from '@testing-library/react';

describe('useCounter', () => {
  it('initializes with default value', () => {
    const { result } = renderHook(() => useCounter());
    expect(result.current.count).toBe(0);
  });

  it('increments count', () => {
    const { result } = renderHook(() => useCounter());
    act(() => result.current.increment());
    expect(result.current.count).toBe(1);
  });
});
```

## Integration Testing

### Testing with Context Providers
```typescript
const renderWithProviders = (component: React.ReactElement) =>
  render(<AppProvider>{component}</AppProvider>);

describe('FileManager Integration', () => {
  it('shows uploaded file in list', async () => {
    renderWithProviders(<FileManager />);
    await userEvent.upload(screen.getByLabelText('Upload'), mockFile);
    expect(await screen.findByText('document.pdf')).toBeInTheDocument();
  });
});
```

### Mocking API / DB Calls
```typescript
// Mock the service layer (preferred — test behavior, not DB internals)
vi.mock('@/services/userService', () => ({
  userService: {
    getProfile: vi.fn(),
    updateRole: vi.fn(),
  }
}));

describe('UserService', () => {
  beforeEach(() => vi.clearAllMocks());

  it('fetches user profile successfully', async () => {
    const mockProfile = { id: 'user-123', role: 'admin', email: 'admin@example.com' };
    vi.mocked(userService.getProfile).mockResolvedValue(mockProfile);

    const result = await userService.getProfile('user-123');
    expect(result).toEqual(mockProfile);
    expect(userService.getProfile).toHaveBeenCalledWith('user-123');
  });

  it('handles not found error', async () => {
    vi.mocked(userService.getProfile).mockResolvedValue(null);
    const result = await userService.getProfile('invalid-id');
    expect(result).toBeNull();
  });
});

// Mock HTTP client (fetch / axios) for API boundary tests
vi.stubGlobal('fetch', vi.fn().mockResolvedValue({
  ok: true,
  json: () => Promise.resolve({ id: 'user-123', name: 'Test' }),
}));
```

## E2E Testing (Playwright)

```typescript
// playwright.config.ts
export default defineConfig({
  testDir: './e2e',
  use: { baseURL: 'http://localhost:5173', trace: 'on-first-retry' },
  webServer: { command: 'npm run dev', url: 'http://localhost:5173' }
});
```

```typescript
// e2e/auth.spec.ts
test('user can login with valid credentials', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'test@example.com');
  await page.fill('input[name="password"]', 'password123');
  await page.click('button[type="submit"]');

  await expect(page).toHaveURL('/dashboard');
  await expect(page.locator('[data-testid="welcome"]')).toBeVisible();
});

test('shows error with invalid credentials', async ({ page }) => {
  await page.goto('/login');
  await page.fill('input[name="email"]', 'wrong@example.com');
  await page.fill('input[name="password"]', 'wrongpass');
  await page.click('button[type="submit"]');

  await expect(page.locator('text=Ungültige Anmeldedaten')).toBeVisible();
});
```

## Test Best Practices

### AAA Pattern (Arrange-Act-Assert)
```typescript
it('updates user role', async () => {
  // Arrange
  const userId = 'user-123';
  vi.mocked(userService.updateRole).mockResolvedValue({ error: null });

  // Act
  const result = await userService.updateRole(userId, 'admin');

  // Assert
  expect(userService.updateRole).toHaveBeenCalledWith(userId, 'admin');
  expect(result).toEqual({ error: null });
});
```

### Query Priority
```typescript
// Priority (highest to lowest):
screen.getByRole('button', { name: /submit/i })  // ✅ Best
screen.getByLabelText('Email')                    // ✅ Good for forms
screen.getByText('Welcome')                       // ✅ OK
screen.getByTestId('submit-btn')                  // ⚠️ Last resort
```

### Test User Behavior, Not Implementation
```typescript
// ❌ BAD — testing implementation detail
it('sets isOpen to true', () => {
  const { result } = renderHook(() => useState(false));
  act(() => result.current[1](true));
  expect(result.current[0]).toBe(true);
});

// ✅ GOOD — testing user-visible behavior
it('shows modal when open button is clicked', async () => {
  render(<ModalComponent />);
  await userEvent.click(screen.getByRole('button', { name: /open/i }));
  expect(screen.getByRole('dialog')).toBeVisible();
});
```

## Package.json Scripts

```json
{
  "scripts": {
    "test": "vitest run",
    "test:watch": "vitest",
    "test:coverage": "vitest run --coverage",
    "test:ui": "vitest --ui",
    "test:e2e": "playwright test",
    "test:e2e:ui": "playwright test --ui"
  }
}
```

## Coverage Goals

| Metric | Minimum |
|--------|---------|
| Lines | 80% |
| Functions | 80% |
| Branches | 75% |
| Statements | 80% |

**Focus on:** auth flows, data mutations, complex business logic, error handling
**Can skip:** thin third-party wrappers, simple presentational components, config files

## When to Use This Skill

- Writing new features (test as you go)
- Fixing bugs (write test first to reproduce)
- Refactoring code (ensure tests stay green)
- Reviewing PRs (check test coverage and quality)
- Setting up a new project (configure testing stack)
