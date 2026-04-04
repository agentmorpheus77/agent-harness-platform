---
name: error-handling-monitoring
description: Use when implementing error handling and monitoring — React Error Boundaries, Sentry integration, user-friendly error feedback, retry logic, loading states, and optimistic updates with rollback.
version: 0.1.0
---

# Error Handling & Monitoring

## Core Principles

1. **Fail Gracefully** — errors should never crash the entire app; isolate failures
2. **Inform the User** — clear, actionable messages; no technical jargon for users
3. **Log Everything** — capture details for debugging, but don't expose them to users
4. **Retry When Appropriate** — smart retry for transient failures (network errors)
5. **Monitor Proactively** — catch issues before users report them

## React Error Boundaries

```typescript
// src/components/ErrorBoundary.tsx
interface Props { children: ReactNode; fallback?: ReactNode; onError?: (error: Error) => void; }
interface State { hasError: boolean; error: Error | null; }

export class ErrorBoundary extends Component<Props, State> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError(error: Error): State {
    return { hasError: true, error };
  }

  componentDidCatch(error: Error, info: React.ErrorInfo) {
    this.props.onError?.(error);
    reportError(error, { componentStack: info.componentStack });
  }

  render() {
    if (this.state.hasError) {
      return this.props.fallback ?? (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <p>Please try refreshing the page.</p>
          <button onClick={() => window.location.reload()}>Refresh</button>
        </div>
      );
    }
    return this.props.children;
  }
}

// Resettable — resets when resetKeys change
export class ResettableErrorBoundary extends Component<Props & { resetKeys?: unknown[] }, State> {
  state = { hasError: false, error: null };

  static getDerivedStateFromError = ErrorBoundary.getDerivedStateFromError;

  componentDidUpdate(prevProps: Props & { resetKeys?: unknown[] }) {
    if (this.state.hasError && this.props.resetKeys?.some(
      (k, i) => k !== prevProps.resetKeys?.[i]
    )) {
      this.setState({ hasError: false, error: null });
    }
  }

  render() {
    if (this.state.hasError) {
      return (
        <div className="error-fallback">
          <h2>Something went wrong</h2>
          <button onClick={() => this.setState({ hasError: false, error: null })}>
            Try Again
          </button>
        </div>
      );
    }
    return this.props.children;
  }
}
```

## Error Reporting (Sentry)

```typescript
// src/lib/errorReporting.ts
import * as Sentry from '@sentry/react';

export function initSentry() {
  if (import.meta.env.PROD) {
    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      environment: import.meta.env.MODE,
      tracesSampleRate: 0.1,
      beforeSend(event, hint) {
        const error = hint.originalException;
        // Filter noise
        if (error instanceof TypeError && error.message.includes('Failed to fetch')) return null;
        if (event.message?.includes('ResizeObserver loop limit')) return null;
        return event;
      },
    });
  }
}

export function reportError(error: Error, context?: Record<string, unknown>) {
  console.error('Error:', error, context);
  if (import.meta.env.PROD) {
    Sentry.captureException(error, { extra: context });
  }
}

export function reportMessage(message: string, level: 'info' | 'warning' | 'error' = 'info') {
  if (import.meta.env.PROD) Sentry.captureMessage(message, level);
}
```

## User-Friendly Error Messages

```typescript
export function getUserMessage(error: unknown): string {
  if (!(error instanceof Error)) return 'An unexpected error occurred.';

  if (error.message.includes('Failed to fetch') || error.message.includes('Network'))
    return 'Unable to connect. Please check your internet connection.';

  if (error.message.includes('permission denied'))
    return "You don't have permission to perform this action.";

  if (error.message.includes('unique constraint'))
    return 'This item already exists.';

  return 'Something went wrong. Please try again.';
}
```

## Toast Notifications

```typescript
// src/hooks/useToast.ts — using Zustand
interface Toast { id: string; type: 'success' | 'error' | 'warning' | 'info'; title: string; message?: string; }

export const useToastStore = create<{ toasts: Toast[]; add: (t: Omit<Toast, 'id'>) => void; remove: (id: string) => void }>((set) => ({
  toasts: [],
  add: (toast) => {
    const id = crypto.randomUUID();
    set(s => ({ toasts: [...s.toasts, { ...toast, id }] }));
    setTimeout(() => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })), 5000);
  },
  remove: (id) => set(s => ({ toasts: s.toasts.filter(t => t.id !== id) })),
}));

export const useToast = () => {
  const add = useToastStore(s => s.add);
  return {
    success: (title: string, message?: string) => add({ type: 'success', title, message }),
    error: (title: string, message?: string) => add({ type: 'error', title, message }),
    info: (title: string, message?: string) => add({ type: 'info', title, message }),
  };
};
```

## Retry with Exponential Backoff

```typescript
export async function retryWithBackoff<T>(
  fn: () => Promise<T>,
  { maxRetries = 3, initialDelay = 1000, shouldRetry = () => true } = {}
): Promise<T> {
  let delay = initialDelay;

  for (let attempt = 0; attempt <= maxRetries; attempt++) {
    try {
      return await fn();
    } catch (error) {
      if (attempt === maxRetries || !shouldRetry(error as Error)) throw error;
      await new Promise(r => setTimeout(r, delay));
      delay = Math.min(delay * 2, 10000);
    }
  }
  throw new Error('Max retries exceeded');
}

// Usage
const data = await retryWithBackoff(
  () => fetch('/api/data').then(r => r.json()),
  { shouldRetry: (e) => e.message.includes('Failed to fetch') }
);
```

### TanStack Query Retry
```typescript
useQuery({
  queryKey: ['data'],
  queryFn: fetchData,
  retry: (count, error) => {
    if ((error as Error).message.includes('40')) return false; // Don't retry 4xx
    return count < 3;
  },
  retryDelay: attempt => Math.min(1000 * 2 ** attempt, 10000),
});
```

## Optimistic Updates with Rollback

```typescript
const updateItem = useMutation({
  mutationFn: (update: Partial<Item>) => api.update(update),

  onMutate: async (update) => {
    await queryClient.cancelQueries({ queryKey: ['items'] });
    const previous = queryClient.getQueryData<Item[]>(['items']);

    // Optimistically update
    queryClient.setQueryData<Item[]>(['items'], items =>
      items?.map(item => item.id === update.id ? { ...item, ...update } : item)
    );

    return { previous }; // context for rollback
  },

  onError: (_err, _vars, context) => {
    if (context?.previous) queryClient.setQueryData(['items'], context.previous);
    toast.error('Update failed', 'Please try again.');
  },

  onSettled: () => queryClient.invalidateQueries({ queryKey: ['items'] }),
});
```

## Loading & Error State Pattern

```typescript
function DataState<T>({ data, isLoading, error, children, emptyComponent }: {
  data: T | undefined; isLoading: boolean; error: Error | null;
  children: (data: T) => ReactNode; emptyComponent?: ReactNode;
}) {
  if (isLoading) return <LoadingSpinner />;
  if (error) return <div className="error-state"><p>{getUserMessage(error)}</p></div>;
  if (data == null || (Array.isArray(data) && !data.length))
    return <>{emptyComponent ?? <p>No data available</p>}</>;
  return <>{children(data)}</>;
}
```

## Best Practices

**DO:**
- Use Error Boundaries to isolate component failures
- Show user-friendly error messages (not stack traces)
- Implement retry for network/transient errors
- Log all errors to Sentry in production
- Provide clear loading states (skeleton, spinner)
- Use optimistic updates with rollback
- Test error scenarios explicitly

**DON'T:**
- Don't swallow errors silently (`catch {}`)
- Don't show technical error details to users
- Don't retry on 4xx client errors
- Don't retry indefinitely
- Don't expose sensitive information in errors
- Don't log passwords or tokens

## Common Pitfalls

```typescript
// BAD — unhandled promise
useEffect(() => { fetchData(); }, []);

// GOOD
useEffect(() => { fetchData().catch(err => { reportError(err); setError(err); }); }, []);

// BAD — generic message
toast.error('Error');

// GOOD — actionable message
toast.error('Failed to save file', 'Please check your connection and try again.');

// BAD — error state not cleared
const [error, setError] = useState(null);
// error never cleared on success

// GOOD
const handleSubmit = async () => {
  setError(null); // Clear before attempting
  try { await save(); } catch (e) { setError(e); }
};
```

## When to Use This Skill

- Building new features (add error handling from the start)
- Any network request or API integration
- User input flows
- Production monitoring setup (before launch)
- Code reviews (check for swallowed errors)
- Fixing production bugs (improve error context)
