---
name: typescript-best-practices
description: Use when writing TypeScript — advanced types, type safety patterns, generics, discriminated unions, Zod runtime validation, and type guards. Applies to all TypeScript projects in the CDB ecosystem.
version: 0.1.0
---

# TypeScript Best Practices

## Core Principles

1. **Type Safety First** — catch errors at compile time, not runtime
2. **Avoid `any`** — use `unknown` or proper types; every `any` is a hole in your safety net
3. **Make Illegal States Unrepresentable** — design types that make invalid states impossible
4. **Prefer Type Inference** — let TS infer when obvious, be explicit when it adds clarity
5. **Runtime Validation** — TypeScript types disappear at runtime; use Zod at boundaries

## Advanced Types

### Utility Types
```typescript
// Built-in utility types
type UserPreview = Pick<User, 'id' | 'name'>;
type PublicUser = Omit<User, 'password' | 'apiKey'>;
type PartialUser = Partial<User>;
type RequiredUser = Required<User>;
type ImmutableUser = Readonly<User>;

// Custom utility: make specific keys optional
type PartialBy<T, K extends keyof T> = Omit<T, K> & Partial<Pick<T, K>>;
type CreateInput = PartialBy<User, 'id' | 'createdAt'>;

// Deep partial
type DeepPartial<T> = {
  [K in keyof T]?: T[K] extends object ? DeepPartial<T[K]> : T[K];
};
```

### Discriminated Unions for State
```typescript
// Model all possible states explicitly
type ApiState<T> =
  | { status: 'idle' }
  | { status: 'loading' }
  | { status: 'success'; data: T }
  | { status: 'error'; error: Error };

function DataComponent() {
  const [state, setState] = useState<ApiState<User>>({ status: 'idle' });

  if (state.status === 'loading') return <Spinner />;
  if (state.status === 'error') return <Error message={state.error.message} />;
  if (state.status === 'success') return <Profile user={state.data} />;
  return <button onClick={load}>Load</button>;
}
```

### Generics for Reusable Components
```typescript
interface Column<T> {
  key: keyof T;
  header: string;
  render?: (value: T[keyof T], row: T) => React.ReactNode;
}

function DataTable<T extends { id: string }>({
  data,
  columns,
}: {
  data: T[];
  columns: Column<T>[];
}) {
  return (
    <table>
      {data.map(row => (
        <tr key={row.id}>
          {columns.map(col => (
            <td key={String(col.key)}>
              {col.render ? col.render(row[col.key], row) : String(row[col.key])}
            </td>
          ))}
        </tr>
      ))}
    </table>
  );
}
```

### Template Literal Types
```typescript
type HttpMethod = 'GET' | 'POST' | 'PUT' | 'PATCH' | 'DELETE';
type ApiRoute = `/api/v1/${string}`;
type EventName = `${string}:${'created' | 'updated' | 'deleted'}`;

// Valid
const route: ApiRoute = '/api/v1/users';
const event: EventName = 'user:created';
```

## Type Safety Patterns

### Avoid `any`, Use `unknown`
```typescript
// BAD
function process(data: any) {
  return data.map((item: any) => item.value);
}

// GOOD
function process(data: unknown): string[] {
  if (!Array.isArray(data)) throw new Error('Expected array');
  return data.map(item => {
    if (typeof item === 'object' && item !== null && 'value' in item) {
      return String((item as { value: unknown }).value);
    }
    throw new Error('Invalid item');
  });
}
```

### Type Guards
```typescript
interface User { id: string; name: string; email: string; }

function isUser(value: unknown): value is User {
  return (
    typeof value === 'object' &&
    value !== null &&
    typeof (value as User).id === 'string' &&
    typeof (value as User).name === 'string' &&
    typeof (value as User).email === 'string'
  );
}

// Generic property guard
function hasProperty<T extends string>(obj: unknown, prop: T): obj is Record<T, unknown> {
  return typeof obj === 'object' && obj !== null && prop in obj;
}

// Usage
function processData(data: unknown) {
  if (!isUser(data)) throw new Error('Invalid user');
  console.log(data.email.toLowerCase()); // TypeScript knows it's a User
}
```

### Assertion Functions
```typescript
function assertIsDefined<T>(
  value: T | undefined | null,
  message = 'Value must be defined'
): asserts value is T {
  if (value === undefined || value === null) throw new Error(message);
}

// Usage
const user = getUser(id);
assertIsDefined(user, `User ${id} not found`);
console.log(user.email); // TypeScript knows user is defined
```

## Zod for Runtime Validation

```typescript
import { z } from 'zod';

// Define schema once, derive TypeScript type
const userSchema = z.object({
  id: z.string().uuid(),
  name: z.string().min(1).max(100),
  email: z.string().email(),
  role: z.enum(['user', 'admin']),
  createdAt: z.string().datetime(),
});

export type User = z.infer<typeof userSchema>;

// Derived schemas
export const createUserSchema = userSchema.omit({ id: true, createdAt: true });
export const updateUserSchema = userSchema.partial().required({ id: true });

// Validate API responses at system boundary
async function fetchUser(id: string): Promise<User> {
  const response = await fetch(`/api/users/${id}`);
  const data = await response.json();

  const result = userSchema.safeParse(data);
  if (!result.success) {
    console.error('Validation failed:', result.error.errors);
    throw new Error('Invalid user data from API');
  }
  return result.data;
}

// Form validation
import { zodResolver } from '@hookform/resolvers/zod';
const { register, handleSubmit } = useForm<CreateUser>({
  resolver: zodResolver(createUserSchema),
});
```

## tsconfig Strict Mode

```json
{
  "compilerOptions": {
    "strict": true,
    "noUnusedLocals": true,
    "noUnusedParameters": true,
    "noFallthroughCasesInSwitch": true,
    "noImplicitReturns": true
  }
}
```

## Best Practices

**DO:**
- Enable `strict: true` in tsconfig
- Validate external data with Zod at runtime
- Use discriminated unions for complex state
- Create custom type guards for runtime checks
- Leverage utility types (`Pick`, `Omit`, `Partial`, etc.)
- Use generics for reusable components and functions
- Prefer `unknown` over `any`

**DON'T:**
- Don't use `any` — it defeats TypeScript's purpose
- Don't use `as` type assertions without validation
- Don't use `@ts-ignore` to suppress errors
- Don't trust external data without runtime validation
- Don't duplicate types — derive from a single source
- Don't use non-null assertions (`!`) excessively
- Don't disable strict mode flags

## Common Pitfalls

```typescript
// BAD — unsafe assertion
const user = data as User;

// GOOD — runtime validation
const user = userSchema.parse(data);

// BAD — missing null check
const name = user.name.toUpperCase();

// GOOD — safe access
const name = user?.name?.toUpperCase() ?? 'Unknown';

// BAD — wrong discriminant check
if (state.data) { return state.data.name; } // TS can't narrow properly

// GOOD — use discriminant
if (state.status === 'success') { return state.data.name; }
```

## When to Use This Skill

- Designing types for new features
- Integrating external APIs (validate responses)
- Refactoring legacy JavaScript to TypeScript
- Debugging complex type errors
- Building reusable generic components
- Handling user input and form validation
