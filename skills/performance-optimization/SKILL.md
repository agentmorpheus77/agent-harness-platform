---
name: performance-optimization
description: Use when optimizing React application performance — useMemo, useCallback, React.memo, code splitting, bundle analysis, caching with TanStack Query, virtual scrolling, Web Workers, and image optimization.
version: 0.1.0
---

# Performance Optimization

## Core Principles

1. **Measure Before Optimizing** — profile first with React DevTools Profiler, don't guess
2. **Perceived Performance** — focus on what users feel: fast load, smooth interactions
3. **Lazy Load Non-Critical Resources** — defer components, routes, assets not immediately needed
4. **Minimize Re-renders** — proper memoization and state design
5. **Profile in Production** — dev builds are slower; test with `npm run build && preview`

## React Optimizations

### useMemo — Expensive Computations
```typescript
function SearchResults({ items, query }: { items: Item[]; query: string }) {
  // Only recompute when items or query change
  const filtered = useMemo(
    () => items
      .filter(item => item.name.toLowerCase().includes(query.toLowerCase()))
      .sort((a, b) => a.name.localeCompare(b.name)),
    [items, query]
  );

  return <ItemList items={filtered} />;
}

// DON'T use useMemo for cheap operations:
const doubled = useMemo(() => count * 2, [count]); // Unnecessary overhead
const doubled = count * 2; // Just compute it directly
```

### useCallback — Stable Function References
```typescript
function Parent({ items }: { items: Item[] }) {
  // Stable references prevent child re-renders
  const handleSelect = useCallback((id: string) => {
    setSelectedId(id);
  }, []); // Empty deps — function never needs to change

  const handleDelete = useCallback(async (id: string) => {
    await deleteItem(id);
    refetch();
  }, [refetch]);

  return items.map(item => (
    <Item key={item.id} item={item} onSelect={handleSelect} onDelete={handleDelete} />
  ));
}
```

### React.memo — Prevent Re-renders
```typescript
// Basic memo — re-renders only when props change (shallow comparison)
export const ItemCard = memo(function ItemCard({ id, title, onSelect }: ItemProps) {
  return <div onClick={() => onSelect(id)}>{title}</div>;
});

// Custom comparison for complex props
export const ExpensiveList = memo(
  function ExpensiveList({ items, onUpdate }: ListProps) {
    return <ul>{items.map(i => <li key={i.id}>{i.name}</li>)}</ul>;
  },
  (prev, next) =>
    prev.items.length === next.items.length &&
    prev.items.every((item, i) => item.id === next.items[i].id)
);
```

## Bundle Optimization (Vite)

### Code Splitting & Lazy Loading
```typescript
// Lazy load routes
const Dashboard = lazy(() => import('./pages/Dashboard'));
const Settings = lazy(() => import('./pages/Settings'));
const Reports = lazy(() => import('./apps/Reports'));

function App() {
  return (
    <Suspense fallback={<LoadingScreen />}>
      <Routes>
        <Route path="/" element={<Dashboard />} />
        <Route path="/settings" element={<Settings />} />
        <Route path="/reports" element={<Reports />} />
      </Routes>
    </Suspense>
  );
}

// Dynamic import for heavy optional features
const handleExportPDF = async () => {
  const { generatePDF } = await import('./utils/pdfGenerator'); // loads only when needed
  await generatePDF(data);
};
```

### Vite Config
```typescript
// vite.config.ts
export default defineConfig({
  build: {
    chunkSizeWarningLimit: 500,
    rollupOptions: {
      output: {
        manualChunks: {
          'react-vendor': ['react', 'react-dom', 'react-router-dom'],
          'ui-vendor': ['@radix-ui/react-dialog', '@radix-ui/react-dropdown-menu'],
        },
      },
    },
    minify: 'terser',
    terserOptions: { compress: { drop_console: true, drop_debugger: true } },
  },
});
```

### Avoid Large Imports
```typescript
// BAD — imports entire library
import _ from 'lodash';
import * as dateFns from 'date-fns';

// GOOD — import only what you need
import debounce from 'lodash/debounce';
import { format } from 'date-fns/format';
```

## Caching with TanStack Query

```typescript
export function useItems(categoryId: string) {
  return useQuery({
    queryKey: ['items', categoryId],
    queryFn: () => fetchItems(categoryId),
    staleTime: 5 * 60 * 1000,   // Fresh for 5 minutes
    gcTime: 10 * 60 * 1000,     // Keep in cache for 10 minutes after unmount (TanStack Query v5+)
  });
}

// Avoid N+1 queries — use joins instead of looping requests
// BAD:
const items = await db.from('items').select('*');
const withAuthors = await Promise.all(items.map(i => db.from('users').select('*').eq('id', i.user_id).single()));

// GOOD:
const items = await db.from('items').select('*, author:users(id, name, avatar_url)');
```

## Debouncing & Throttling

```typescript
export function useDebounce<T>(value: T, delay: number): T {
  const [debounced, setDebounced] = useState(value);
  useEffect(() => {
    const timer = setTimeout(() => setDebounced(value), delay);
    return () => clearTimeout(timer);
  }, [value, delay]);
  return debounced;
}

// Usage — search only fires 300ms after user stops typing
function SearchBox() {
  const [query, setQuery] = useState('');
  const debouncedQuery = useDebounce(query, 300);

  const { data } = useQuery({
    queryKey: ['search', debouncedQuery],
    queryFn: () => search(debouncedQuery),
    enabled: debouncedQuery.length > 1,
  });
}
```

## Virtual Scrolling (Large Lists)

```typescript
import { useVirtualizer } from '@tanstack/react-virtual';

function VirtualList({ items }: { items: Item[] }) {
  const parentRef = useRef<HTMLDivElement>(null);

  const virtualizer = useVirtualizer({
    count: items.length,
    getScrollElement: () => parentRef.current,
    estimateSize: () => 50, // Row height estimate
    overscan: 5,
  });

  return (
    <div ref={parentRef} style={{ height: '600px', overflow: 'auto' }}>
      <div style={{ height: virtualizer.getTotalSize(), position: 'relative' }}>
        {virtualizer.getVirtualItems().map(vi => (
          <div
            key={vi.key}
            style={{
              position: 'absolute', top: 0, left: 0, width: '100%',
              height: vi.size, transform: `translateY(${vi.start}px)`,
            }}
          >
            <ItemRow item={items[vi.index]} />
          </div>
        ))}
      </div>
    </div>
  );
}
// Use virtual scrolling for lists with 100+ items
```

## Web Workers (CPU-Intensive Tasks)

```typescript
// Don't block the main thread with heavy computations
// src/workers/processor.worker.ts
self.onmessage = (event) => {
  const result = heavyComputation(event.data);
  self.postMessage(result);
};

// src/hooks/useProcessor.ts
export function useProcessor() {
  const workerRef = useRef<Worker>();

  useEffect(() => {
    workerRef.current = new Worker(
      new URL('../workers/processor.worker.ts', import.meta.url),
      { type: 'module' }
    );
    return () => workerRef.current?.terminate();
  }, []);

  const process = (data: unknown) => {
    return new Promise(resolve => {
      workerRef.current!.onmessage = e => resolve(e.data);
      workerRef.current!.postMessage(data);
    });
  };

  return { process };
}
```

## Image Optimization

```typescript
// Lazy load images with IntersectionObserver
function LazyImage({ src, alt }: { src: string; alt: string }) {
  const [loaded, setLoaded] = useState(false);
  const ref = useRef<HTMLImageElement>(null);

  useEffect(() => {
    const observer = new IntersectionObserver(([entry]) => {
      if (entry.isIntersecting) { setLoaded(true); observer.disconnect(); }
    }, { rootMargin: '50px' });

    if (ref.current) observer.observe(ref.current);
    return () => observer.disconnect();
  }, []);

  return <img ref={ref} src={loaded ? src : undefined} alt={alt} loading="lazy" />;
}
```

## Best Practices

**DO:**
- Profile before optimizing (React DevTools Profiler)
- Use production builds for accurate measurements
- Implement code splitting for routes
- Cache API responses with TanStack Query
- Use `React.memo` for components with stable, expensive-to-compare props
- Implement virtual scrolling for 100+ item lists
- Debounce search/filter inputs (300ms)
- Use Web Workers for CPU-intensive work

**DON'T:**
- Don't optimize prematurely without measuring
- Don't over-memoize — memoization itself has cost
- Don't use `useMemo` for trivial computations
- Don't forget to clean up event listeners and subscriptions
- Don't create inline objects/arrays as props to memoized components
- Don't fetch the same data in multiple components — use shared queries

## Common Pitfalls

```typescript
// BAD — new object on every render breaks memo
function Parent() {
  return <Child style={{ margin: 10 }} />; // new object each render!
}

// GOOD — stable reference
const childStyle = { margin: 10 };
function Parent() {
  return <Child style={childStyle} />;
}

// BAD — missing dependency
const result = useMemo(() => compute(a, b), [a]); // Missing b!

// GOOD
const result = useMemo(() => compute(a, b), [a, b]);
```

## Tools

| Tool | Use |
|------|-----|
| React DevTools Profiler | Find slow components |
| Chrome Performance tab | Runtime bottlenecks |
| rollup-plugin-visualizer | Bundle size composition |
| Lighthouse | Automated audits + Web Vitals |
| bundlephobia.com | Check npm package sizes |

## When to Use This Skill

- Initial load is slow (> 3s TTI)
- UI feels sluggish during interactions
- Lists with 100+ items render slowly
- Bundle size growing beyond 500KB
- Before adding a heavy dependency
- After profiling identifies bottlenecks
