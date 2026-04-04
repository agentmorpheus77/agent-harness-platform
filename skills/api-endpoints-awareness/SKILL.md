---
name: api-endpoints-awareness
description: Use when designing, implementing, or reviewing API endpoints — REST conventions, HTTP methods, request/response formats, authentication, validation, rate limiting, and API documentation.
version: 0.1.0
---

# API Endpoints Awareness

## Core Principles

1. **Document First** — before implementing, define purpose, auth, request/response schema
2. **Nouns not Verbs** — resources are nouns, HTTP methods are the verbs
3. **Consistent Responses** — same success/error structure across all endpoints
4. **Validate at the Boundary** — validate all input before processing
5. **Return Appropriate Status Codes** — communicate what happened clearly

## REST Conventions

### URL Structure
```
✅ GOOD:
GET    /api/v1/users              # list
GET    /api/v1/users/:id          # get one
POST   /api/v1/users              # create
PUT    /api/v1/users/:id          # replace
PATCH  /api/v1/users/:id          # partial update
DELETE /api/v1/users/:id          # delete
GET    /api/v1/users/:id/posts    # nested resource

❌ BAD:
GET  /api/getUsers
POST /api/users/create
GET  /api/user?id=123
POST /api/deleteUser
```

### Naming Rules
- Use **nouns**, not verbs
- Use **plural** nouns: `/users` not `/user`
- Use **kebab-case**: `/blog-posts`
- **Version** your API: `/api/v1/`
- Max **2 levels** of nesting: `/users/:id/posts`

### HTTP Methods
| Method | Use | Idempotent |
|--------|-----|-----------|
| GET | Retrieve (no side effects) | Yes |
| POST | Create | No |
| PUT | Replace entire resource | Yes |
| PATCH | Partial update | Yes |
| DELETE | Remove | Yes |

## Request & Response Format

### Standardized Response
```json
// Success (201 Created)
{
  "success": true,
  "data": {
    "id": "123",
    "title": "My Post",
    "createdAt": "2025-10-23T10:30:00Z"
  },
  "meta": {
    "timestamp": "2025-10-23T10:30:00Z"
  }
}

// Error (400 Bad Request)
{
  "success": false,
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "Validation failed",
    "details": [
      { "field": "title", "message": "Title is required" }
    ]
  },
  "meta": {
    "timestamp": "2025-10-23T10:30:00Z"
  }
}
```

### HTTP Status Codes

**2xx Success:**
- `200 OK` — standard success (GET, PUT, PATCH)
- `201 Created` — resource created (POST)
- `204 No Content` — success, no body (DELETE)

**4xx Client Errors:**
- `400 Bad Request` — invalid syntax / validation failed
- `401 Unauthorized` — not authenticated
- `403 Forbidden` — authenticated but not authorized
- `404 Not Found` — resource doesn't exist
- `409 Conflict` — duplicate / conflict
- `422 Unprocessable Entity` — semantic validation error
- `429 Too Many Requests` — rate limit exceeded

**5xx Server Errors:**
- `500 Internal Server Error` — unexpected server failure
- `503 Service Unavailable` — temporarily down

## Query Parameters

```
# Filtering
GET /api/v1/posts?status=published&author=john

# Sorting
GET /api/v1/posts?sort=createdAt        # ascending
GET /api/v1/posts?sort=-createdAt       # descending (- prefix)

# Pagination (cursor-based preferred)
GET /api/v1/posts?limit=20&cursor=abc123

# Field selection
GET /api/v1/posts?fields=id,title,author
```

### Pagination Response
```json
{
  "success": true,
  "data": [...],
  "pagination": {
    "total": 150,
    "page": 2,
    "limit": 20,
    "hasNext": true,
    "hasPrev": true,
    "nextCursor": "xyz789"
  }
}
```

## Authentication

```typescript
// JWT Bearer token
GET /api/v1/profile
Authorization: Bearer eyJhbGciOiJIUzI1NiIs...

// Middleware pattern
const requireAuth = (req, res, next) => {
  if (!req.user) return res.status(401).json({ error: 'Authentication required' });
  next();
};

const requireRole = (roles: string[]) => (req, res, next) => {
  if (!roles.includes(req.user.role))
    return res.status(403).json({ error: 'Insufficient permissions' });
  next();
};

router.get('/admin/users', requireAuth, requireRole(['admin']), getUsers);
```

## Input Validation

```typescript
import { z } from 'zod';

const createPostSchema = z.object({
  title: z.string().min(1).max(200),
  content: z.string().min(10),
  tags: z.array(z.string()).max(5).optional(),
  published: z.boolean().default(false),
});

router.post('/posts', async (req, res) => {
  const result = createPostSchema.safeParse(req.body);
  if (!result.success) {
    return res.status(400).json({
      success: false,
      error: {
        code: 'VALIDATION_ERROR',
        message: 'Invalid request data',
        details: result.error.errors
      }
    });
  }
  // proceed with result.data
});
```

## Error Handler Middleware

```typescript
const ERROR_CODES = {
  VALIDATION_ERROR: 'VALIDATION_ERROR',
  UNAUTHORIZED: 'UNAUTHORIZED',
  FORBIDDEN: 'FORBIDDEN',
  NOT_FOUND: 'NOT_FOUND',
  INTERNAL_ERROR: 'INTERNAL_ERROR',
};

app.use((err, req, res, next) => {
  const status = err.statusCode || 500;
  res.status(status).json({
    success: false,
    error: {
      code: err.code || ERROR_CODES.INTERNAL_ERROR,
      message: err.message || 'Internal server error',
      ...(process.env.NODE_ENV === 'development' && { stack: err.stack })
    },
    meta: { timestamp: new Date().toISOString(), path: req.path }
  });
});
```

## Rate Limiting

```typescript
import rateLimit from 'express-rate-limit';

// General
app.use('/api/', rateLimit({ windowMs: 15 * 60 * 1000, max: 100 }));

// Strict for auth endpoints
app.use('/api/auth/', rateLimit({
  windowMs: 15 * 60 * 1000,
  max: 5,
  skipSuccessfulRequests: true
}));
```

## CORS

```typescript
app.use(cors({
  origin: process.env.FRONTEND_URL,
  credentials: true,
  methods: ['GET', 'POST', 'PUT', 'PATCH', 'DELETE'],
  allowedHeaders: ['Content-Type', 'Authorization']
}));
```

## New Endpoint Checklist

- [ ] Follows REST conventions (method, URL structure)
- [ ] Authentication/authorization implemented
- [ ] Input validated with clear error messages
- [ ] Correct HTTP status codes
- [ ] Standardized response format
- [ ] Rate limiting configured
- [ ] CORS configured for allowed origins
- [ ] Documented (OpenAPI / README)
- [ ] Unit tests for success + error cases
- [ ] Sensitive data not exposed in responses
- [ ] Logging implemented for debugging

## When to Use This Skill

- Designing new API endpoints
- Reviewing existing API implementations
- Debugging API issues
- Writing API documentation
- Implementing auth/authorization
- Setting up error handling
- Preparing for frontend/mobile integration
