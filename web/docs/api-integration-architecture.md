# API Integration Architecture

## Overview

This document describes the architecture and design decisions for the Nexus-AI web frontend API integration layer.

## Architecture Layers

```
┌─────────────────────────────────────────────┐
│            React Components                 │
│  (UI logic, user interactions, rendering)   │
└───────────────┬─────────────────────────────┘
                │
                │ uses
                ▼
┌─────────────────────────────────────────────┐
│         React Query Hooks                   │
│  (src/hooks/*.ts)                          │
│  - Data fetching & caching                 │
│  - Loading & error states                  │
│  - Cache invalidation strategies           │
└───────────────┬─────────────────────────────┘
                │
                │ calls
                ▼
┌─────────────────────────────────────────────┐
│         API Client Functions                │
│  (src/lib/*.ts)                            │
│  - Type-safe HTTP calls                    │
│  - Request/response transformation         │
│  - Error handling                          │
└───────────────┬─────────────────────────────┘
                │
                │ uses
                ▼
┌─────────────────────────────────────────────┐
│            Base API Client                  │
│  (src/lib/api-client.ts)                   │
│  - HTTP client wrapper (fetch)             │
│  - Global error handling                   │
│  - Authentication headers                  │
└───────────────┬─────────────────────────────┘
                │
                │ HTTP
                ▼
┌─────────────────────────────────────────────┐
│          Backend REST API                   │
│  (Python FastAPI @ localhost:8000)          │
└─────────────────────────────────────────────┘
```

## Directory Structure

```
web/
├── src/
│   ├── types/
│   │   ├── api.ts              # Backend API types (requests/responses)
│   │   └── projects.ts         # Frontend domain types
│   │
│   ├── lib/                    # API Client Layer
│   │   ├── api-client.ts       # Base HTTP client
│   │   ├── projects.ts         # Project-related API calls
│   │   ├── agents.ts           # Agent-related API calls
│   │   ├── sessions.ts         # Session management API calls
│   │   └── statistics.ts       # Statistics API calls
│   │
│   └── hooks/                  # React Query Hooks Layer
│       ├── use-projects.ts     # Project data hooks
│       ├── use-agents.ts       # Agent data hooks
│       ├── use-sessions.ts     # Session data hooks
│       └── use-statistics.ts   # Statistics data hooks
│
└── docs/
    ├── api-integration-architecture.md  # This file
    └── api-usage-guide.md              # Usage examples
```

## Design Principles

### 1. Separation of Concerns

**API Client Layer (`src/lib/*.ts`)**
- Pure functions that make HTTP calls
- No React dependencies
- Can be tested independently
- Can be used in Node.js scripts or other contexts

**React Query Hooks Layer (`src/hooks/*.ts`)**
- React-specific data fetching
- Manages loading/error states
- Implements caching strategies
- Handles cache invalidation

### 2. Type Safety

All API interactions are fully typed using TypeScript:

```typescript
// API request/response types
export interface CreateProjectRequest {
  requirement: string;
  user_id?: string;
  project_name?: string;
}

export interface CreateProjectResponseData {
  project_id: string;
  status: ProjectStatus;
  progress: number;
}

// API client function
export async function createProject(
  request: CreateProjectRequest
): Promise<CreateProjectResponseData> {
  const response = await apiFetch<CreateProjectResponse>('/api/v1/projects', {
    method: 'POST',
    body: JSON.stringify(request),
  });

  if (!response.success) {
    throw new Error('Failed to create project');
  }

  return response.data;
}

// React Query hook
export function useCreateProject(
  options?: UseMutationOptions<
    CreateProjectResponseData,
    Error,
    CreateProjectRequest
  >
) {
  const queryClient = useQueryClient();

  return useMutation<CreateProjectResponseData, Error, CreateProjectRequest>({
    mutationFn: createProject,
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['projects', 'summaries'] });
    },
    ...options,
  });
}
```

### 3. Consistent Naming Conventions

**API Client Functions:**
- `fetch*` - GET requests (read operations)
- `create*` - POST requests (create operations)
- `update*` - PUT requests (update operations)
- `delete*` - DELETE requests (delete operations)
- `control*` - Special control operations

**React Query Hooks:**
- `use*` prefix for all hooks
- Query hooks: `useProjectDetail`, `useAgentsList`
- Mutation hooks: `useCreateProject`, `useDeleteAgent`

### 4. Error Handling Strategy

**Three Layers of Error Handling:**

1. **Base Client (`api-client.ts`):**
   - Network errors
   - HTTP status errors (4xx, 5xx)
   - Response parsing errors

2. **API Client Functions (`src/lib/*.ts`):**
   - Business logic errors
   - Validation errors
   - Throw descriptive Error objects

3. **React Query Hooks (`src/hooks/*.ts`):**
   - UI error states via `error` property
   - Retry strategies
   - Error boundaries integration

### 5. Caching & Invalidation

**Query Key Structure:**
```typescript
// Hierarchical query keys
['projects']                                    // All projects
['projects', 'summaries']                       // Project list
['projects', 'detail', projectId]               // Specific project
['projects', 'build-dashboard', projectId]      // Build dashboard
['projects', 'stage-detail', projectId, stage]  // Stage details

['agents']                                      // All agents
['agents', 'list', limit]                       // Agent list
['agents', 'details', agentId]                  // Agent details
['agents', 'sessions', agentId]                 // Agent sessions

['sessions', 'messages', sessionId]             // Session messages
['sessions', 'details', sessionId]              // Session details

['statistics', 'overview']                      // Stats overview
['statistics', 'builds', days]                  // Build stats
```

**Cache Invalidation Strategies:**

1. **Optimistic Updates:** Mutation hooks invalidate related queries
2. **Polling:** Build dashboards refetch while status is 'building'
3. **Stale Time:** Different stale times based on data volatility
   - Statistics: 5 minutes
   - Project summaries: 30 seconds
   - Real-time data: 5 seconds

## API Endpoint Coverage

### Projects API (100% coverage)

| Endpoint | Method | Client Function | Hook |
|----------|--------|----------------|------|
| `/api/v1/projects` | GET | `fetchProjectSummaries` | `useProjectSummaries` |
| `/api/v1/projects` | POST | `createProject` | `useCreateProject` |
| `/api/v1/projects/:id` | DELETE | `deleteProject` | `useDeleteProject` |
| `/api/v1/projects/:id/build` | GET | `fetchBuildDashboard` | `useBuildDashboard` |
| `/api/v1/projects/:id/control` | PUT | `controlProject` | `useControlProject` |
| `/api/v1/projects/:id/stages` | GET | `fetchProjectStages` | (used internally) |
| `/api/v1/projects/:id/stages/:name` | GET | `fetchProjectStageDetail` | `useProjectStageDetail` |

### Agents API (100% coverage)

| Endpoint | Method | Client Function | Hook |
|----------|--------|----------------|------|
| `/api/v1/agents` | GET | `fetchAgentsList` | `useAgentsList` |
| `/api/v1/agents/:id` | GET | `fetchAgentDetails` | `useAgentDetails` |
| `/api/v1/agents/:id` | PUT | `updateAgent` | `useUpdateAgent` |
| `/api/v1/agents/:id` | DELETE | `deleteAgent` | `useDeleteAgent` |
| `/api/v1/agents/:id/status` | PUT | `updateAgentStatus` | `useUpdateAgentStatus` |
| `/api/v1/agents/:id/invoke` | POST | `invokeAgent` | `useInvokeAgent` |
| `/api/v1/agents/:id/context` | GET | `fetchAgentContext` | `useAgentContext` |
| `/api/v1/agents/:id/sessions` | GET | `fetchAgentSessions` | `useAgentSessions` |
| `/api/v1/agents/:id/sessions` | POST | `createAgentSession` | `useCreateAgentSession` |

### Sessions API (100% coverage)

| Endpoint | Method | Client Function | Hook |
|----------|--------|----------------|------|
| `/api/v1/sessions/:id` | GET | `fetchSessionDetails` | `useSessionDetails` |
| `/api/v1/sessions/:id` | DELETE | `deleteSession` | `useDeleteSession` |
| `/api/v1/sessions/:id/messages` | GET | `fetchSessionMessages` | `useSessionMessages` |
| `/api/v1/sessions/:id/messages` | POST | `sendMessage` | `useSendMessage` |

### Statistics API (100% coverage)

| Endpoint | Method | Client Function | Hook |
|----------|--------|----------------|------|
| `/api/v1/statistics/overview` | GET | `fetchStatisticsOverview` | `useStatisticsOverview` |
| `/api/v1/statistics/builds` | GET | `fetchBuildStatistics` | `useBuildStatistics` |
| `/api/v1/statistics/invocations` | GET | `fetchInvocationStatistics` | `useInvocationStatistics` |
| `/api/v1/statistics/trends/:metric` | GET | `fetchTrendData` | `useTrendData` |

## Migration from Legacy Patterns

### Before (Direct API Calls)
```typescript
const [projects, setProjects] = useState([]);
const [loading, setLoading] = useState(true);
const [error, setError] = useState(null);

useEffect(() => {
  fetch('/api/v1/projects')
    .then(res => res.json())
    .then(data => {
      setProjects(data.projects);
      setLoading(false);
    })
    .catch(err => {
      setError(err);
      setLoading(false);
    });
}, []);
```

### After (React Query Hooks)
```typescript
const { data: projects, isLoading, error } = useProjectSummaries();
```

Benefits:
- ✅ Automatic caching
- ✅ Automatic refetching
- ✅ Built-in loading/error states
- ✅ Request deduplication
- ✅ Background refetching
- ✅ 90% less boilerplate code

## Performance Optimizations

1. **Request Deduplication:** Multiple components can call the same hook without duplicating requests
2. **Background Refetching:** Stale data is updated in the background
3. **Prefetching:** Critical data can be prefetched during navigation
4. **Pagination Support:** Large datasets can be paginated efficiently
5. **Optimistic Updates:** UI updates immediately, syncs with server in background

## Testing Strategy

### API Client Functions
```typescript
describe('createProject', () => {
  it('should create a project successfully', async () => {
    const mockFetch = jest.fn().mockResolvedValue({
      success: true,
      data: { project_id: '123', status: 'pending' }
    });

    global.fetch = mockFetch;

    const result = await createProject({
      requirement: 'Build an agent'
    });

    expect(result.project_id).toBe('123');
  });
});
```

### React Query Hooks
```typescript
describe('useCreateProject', () => {
  it('should create project and invalidate cache', async () => {
    const { result } = renderHook(() => useCreateProject(), {
      wrapper: createWrapper()
    });

    await act(async () => {
      await result.current.mutateAsync({
        requirement: 'Build an agent'
      });
    });

    expect(result.current.isSuccess).toBe(true);
  });
});
```

## Future Improvements

1. **GraphQL Migration:** Consider migrating to GraphQL for more flexible data fetching
2. **WebSocket Support:** Real-time updates for build progress and agent status
3. **Offline Support:** Service worker + local storage for offline functionality
4. **Request Batching:** Batch multiple API calls into single HTTP request
5. **Generated Types:** Auto-generate TypeScript types from OpenAPI spec

## Related Documentation

- [API Usage Guide](./api-usage-guide.md) - Practical examples and best practices
- [Backend API Documentation](../../api/docs/API_USAGE_EXAMPLES.md) - Complete API reference
- [React Query Documentation](https://tanstack.com/query/latest) - Official React Query docs
