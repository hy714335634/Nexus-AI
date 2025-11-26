# API Usage Guide

Practical examples and best practices for using the Nexus-AI frontend API integration layer.

## Table of Contents

- [Getting Started](#getting-started)
- [Basic Patterns](#basic-patterns)
- [Advanced Patterns](#advanced-patterns)
- [Error Handling](#error-handling)
- [Performance Tips](#performance-tips)
- [Common Use Cases](#common-use-cases)

## Getting Started

### Fetching Data

The simplest way to fetch data is using a Query hook:

```typescript
import { useProjectSummaries } from '@/hooks/use-projects';

function ProjectsList() {
  const { data, isLoading, error } = useProjectSummaries();

  if (isLoading) return <div>Loading...</div>;
  if (error) return <div>Error: {error.message}</div>;

  return (
    <ul>
      {data.map(project => (
        <li key={project.projectId}>{project.projectName}</li>
      ))}
    </ul>
  );
}
```

### Creating/Updating Data

Use Mutation hooks for write operations:

```typescript
import { useCreateProject } from '@/hooks/use-projects';
import { toast } from 'sonner';

function CreateProjectForm() {
  const createProject = useCreateProject({
    onSuccess: (data) => {
      toast.success(`Project ${data.project_id} created!`);
    },
    onError: (error) => {
      toast.error(`Failed: ${error.message}`);
    }
  });

  const handleSubmit = (requirement: string) => {
    createProject.mutate({ requirement });
  };

  return (
    <form onSubmit={(e) => {
      e.preventDefault();
      handleSubmit(e.currentTarget.requirement.value);
    }}>
      <input name="requirement" placeholder="Describe your agent..." />
      <button type="submit" disabled={createProject.isPending}>
        {createProject.isPending ? 'Creating...' : 'Create Project'}
      </button>
    </form>
  );
}
```

## Basic Patterns

### Pattern 1: Display Loading States

```typescript
function ProjectDetail({ projectId }: { projectId: string }) {
  const { data, isLoading, isFetching, error } = useProjectDetail(projectId);

  // Initial load
  if (isLoading) {
    return <Skeleton />;
  }

  // Error state
  if (error) {
    return <ErrorBanner message={error.message} />;
  }

  // Data loaded - show content with optional loading indicator for background refresh
  return (
    <div>
      {isFetching && <div className="refresh-indicator">Updating...</div>}
      <h1>{data.projectName}</h1>
      <StatusBadge status={data.status} />
      <Progress value={data.progressPercentage} />
    </div>
  );
}
```

### Pattern 2: Conditional Fetching

```typescript
function AgentDetails({ agentId }: { agentId?: string }) {
  // Only fetch when agentId is provided
  const { data } = useAgentDetails(agentId ?? '', {
    enabled: Boolean(agentId),
  });

  if (!agentId) {
    return <div>Select an agent to view details</div>;
  }

  return <div>{data?.agent_name}</div>;
}
```

### Pattern 3: Manual Refetch

```typescript
function BuildDashboard({ projectId }: { projectId: string }) {
  const { data, refetch } = useBuildDashboard(projectId);

  return (
    <div>
      <button onClick={() => refetch()}>
        Refresh
      </button>
      <Dashboard data={data} />
    </div>
  );
}
```

## Advanced Patterns

### Pattern 4: Polling for Updates

```typescript
function LiveBuildStatus({ projectId }: { projectId: string }) {
  const { data } = useProjectDetail(projectId);

  // Automatically refetch every 5 seconds while building
  useBuildDashboard(projectId, {
    refetchInterval: (query) => {
      const data = query.state.data;
      if (!data) return false;

      const isBuilding = data.status === 'building' || data.status === 'pending';
      return isBuilding ? 5000 : false;  // Poll every 5s or stop
    },
  });

  return <BuildProgress project={data} />;
}
```

### Pattern 5: Dependent Queries

```typescript
function ProjectWithAgents({ projectId }: { projectId: string }) {
  // First, get project details
  const { data: project } = useProjectDetail(projectId);

  // Then, fetch agents for this project
  const { data: agents } = useAgentsList(100, {
    enabled: Boolean(project),  // Wait for project to load
  });

  const projectAgents = agents?.filter(
    agent => agent.project_id === projectId
  );

  return (
    <div>
      <h2>{project?.projectName}</h2>
      <AgentsList agents={projectAgents} />
    </div>
  );
}
```

### Pattern 6: Optimistic Updates

```typescript
function ProjectControls({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();

  const controlProject = useControlProject({
    onMutate: async ({ projectId, action }) => {
      // Cancel outgoing refetches
      await queryClient.cancelQueries({ queryKey: ['projects', 'detail', projectId] });

      // Snapshot previous value
      const previous = queryClient.getQueryData(['projects', 'detail', projectId]);

      // Optimistically update to the new value
      queryClient.setQueryData(['projects', 'detail', projectId], (old: any) => ({
        ...old,
        status: action === 'pause' ? 'paused' : action === 'resume' ? 'building' : old.status,
      }));

      return { previous };
    },
    onError: (err, variables, context) => {
      // Rollback on error
      if (context?.previous) {
        queryClient.setQueryData(
          ['projects', 'detail', variables.projectId],
          context.previous
        );
      }
    },
  });

  return (
    <div>
      <button onClick={() => controlProject.mutate({ projectId, action: 'pause' })}>
        Pause
      </button>
      <button onClick={() => controlProject.mutate({ projectId, action: 'resume' })}>
        Resume
      </button>
    </div>
  );
}
```

### Pattern 7: Infinite Scrolling (Preparation)

```typescript
// Note: Current API doesn't support pagination yet
// This is how you would implement it when available

function InfiniteAgentsList() {
  const {
    data,
    fetchNextPage,
    hasNextPage,
    isFetchingNextPage,
  } = useInfiniteQuery({
    queryKey: ['agents', 'infinite'],
    queryFn: ({ pageParam = 1 }) =>
      fetchAgentsList(pageParam),
    getNextPageParam: (lastPage, pages) =>
      lastPage.pagination.has_next ? pages.length + 1 : undefined,
  });

  return (
    <div>
      {data?.pages.map((page) => (
        page.agents.map(agent => (
          <AgentCard key={agent.agent_id} agent={agent} />
        ))
      ))}

      {hasNextPage && (
        <button
          onClick={() => fetchNextPage()}
          disabled={isFetchingNextPage}
        >
          {isFetchingNextPage ? 'Loading...' : 'Load More'}
        </button>
      )}
    </div>
  );
}
```

## Error Handling

### Pattern 8: Global Error Boundary

```typescript
import { QueryErrorResetBoundary } from '@tanstack/react-query';
import { ErrorBoundary } from 'react-error-boundary';

function App() {
  return (
    <QueryErrorResetBoundary>
      {({ reset }) => (
        <ErrorBoundary
          onReset={reset}
          fallbackRender={({ error, resetErrorBoundary }) => (
            <div>
              <h1>Something went wrong</h1>
              <pre>{error.message}</pre>
              <button onClick={resetErrorBoundary}>
                Try again
              </button>
            </div>
          )}
        >
          <YourApp />
        </ErrorBoundary>
      )}
    </QueryErrorResetBoundary>
  );
}
```

### Pattern 9: Retry Strategies

```typescript
function CriticalData() {
  const { data } = useProjectDetail(projectId, {
    retry: 3,                              // Retry failed requests 3 times
    retryDelay: (attemptIndex) =>
      Math.min(1000 * 2 ** attemptIndex, 30000),  // Exponential backoff
  });

  return <div>{data?.projectName}</div>;
}
```

### Pattern 10: Custom Error Handling

```typescript
function AgentInvocation() {
  const invokeAgent = useInvokeAgent({
    onError: (error) => {
      if (error.message.includes('rate limit')) {
        toast.error('Too many requests. Please wait.');
      } else if (error.message.includes('unauthorized')) {
        // Redirect to login
        router.push('/login');
      } else {
        toast.error(`Agent invocation failed: ${error.message}`);
      }
    },
  });

  return <button onClick={() => invokeAgent.mutate({
    agentId: 'agent-123',
    request: { input_text: 'Hello' }
  })}>
    Invoke Agent
  </button>;
}
```

## Performance Tips

### Tip 1: Adjust Stale Time

```typescript
// Data that changes rarely - cache longer
const { data } = useAgentContext(agentId, {
  staleTime: 5 * 60 * 1000,  // 5 minutes
});

// Real-time data - refetch more often
const { data } = useBuildDashboard(projectId, {
  staleTime: 5000,  // 5 seconds
});
```

### Tip 2: Prefetch Data

```typescript
import { useQueryClient } from '@tanstack/react-query';
import { fetchProjectDetail } from '@/lib/projects';

function ProjectLink({ projectId }: { projectId: string }) {
  const queryClient = useQueryClient();

  const handleMouseEnter = () => {
    // Prefetch project data on hover
    queryClient.prefetchQuery({
      queryKey: ['projects', 'detail', projectId],
      queryFn: () => fetchProjectDetail(projectId),
    });
  };

  return (
    <Link
      href={`/projects/${projectId}`}
      onMouseEnter={handleMouseEnter}
    >
      View Project
    </Link>
  );
}
```

### Tip 3: Selective Re-rendering

```typescript
import { useProjectDetail } from '@/hooks/use-projects';

function ProjectName({ projectId }: { projectId: string }) {
  // Only re-render when project name changes
  const projectName = useProjectDetail(projectId, {
    select: (data) => data?.projectName,
  });

  return <h1>{projectName}</h1>;
}
```

## Common Use Cases

### Use Case 1: Create Project Flow

```typescript
function CreateProjectWizard() {
  const router = useRouter();
  const createProject = useCreateProject();

  const handleCreate = async (requirement: string) => {
    try {
      const project = await createProject.mutateAsync({ requirement });

      // Redirect to project detail page
      router.push(`/projects/${project.project_id}`);
    } catch (error) {
      console.error('Failed to create project:', error);
    }
  };

  return (
    <WizardForm onSubmit={handleCreate}>
      {/* Form fields */}
    </WizardForm>
  );
}
```

### Use Case 2: Agent Chat Interface

```typescript
function AgentChat({ agentId, sessionId }: Props) {
  const { data: messages } = useSessionMessages(sessionId);
  const sendMessage = useSendMessage();

  const handleSend = (content: string) => {
    sendMessage.mutate({
      sessionId,
      request: { content, role: 'user' },
    });
  };

  return (
    <div>
      <MessageList messages={messages} />
      <ChatInput
        onSend={handleSend}
        disabled={sendMessage.isPending}
      />
    </div>
  );
}
```

### Use Case 3: Build Dashboard with Auto-Refresh

```typescript
function BuildDashboard({ projectId }: { projectId: string }) {
  const { data: dashboard, isLoading } = useBuildDashboard(projectId);

  // Automatic polling is handled by the hook
  // See src/hooks/use-projects.ts: useBuildDashboard

  if (isLoading) return <Skeleton />;

  return (
    <div>
      <h2>{dashboard.projectName}</h2>
      <ProgressBar value={dashboard.progressPercentage} />

      <StageList stages={dashboard.stages} />

      {dashboard.metrics && (
        <MetricsPanel metrics={dashboard.metrics} />
      )}

      {dashboard.alerts && (
        <AlertsList alerts={dashboard.alerts} />
      )}
    </div>
  );
}
```

### Use Case 4: Statistics Dashboard

```typescript
function StatisticsDashboard() {
  const { data: overview } = useStatisticsOverview();
  const { data: buildStats } = useBuildStatistics(30);  // Last 30 days
  const { data: invocStats } = useInvocationStatistics(30);

  return (
    <div className="dashboard">
      <OverviewCards data={overview} />
      <BuildTrendChart data={buildStats} />
      <InvocationTrendChart data={invocStats} />
    </div>
  );
}
```

### Use Case 5: Agent Management

```typescript
function AgentManagement() {
  const { data: agents } = useAgentsList();
  const updateStatus = useUpdateAgentStatus();
  const deleteAgent = useDeleteAgent();

  const handleStatusChange = (agentId: string, status: AgentStatus) => {
    updateStatus.mutate({ agentId, status });
  };

  const handleDelete = async (agentId: string) => {
    if (confirm('Are you sure?')) {
      await deleteAgent.mutateAsync(agentId);
      toast.success('Agent deleted');
    }
  };

  return (
    <table>
      <thead>
        <tr>
          <th>Name</th>
          <th>Status</th>
          <th>Actions</th>
        </tr>
      </thead>
      <tbody>
        {agents?.map(agent => (
          <tr key={agent.agent_id}>
            <td>{agent.agent_name}</td>
            <td>
              <StatusSelect
                value={agent.status}
                onChange={(status) => handleStatusChange(agent.agent_id, status)}
              />
            </td>
            <td>
              <button onClick={() => handleDelete(agent.agent_id)}>
                Delete
              </button>
            </td>
          </tr>
        ))}
      </tbody>
    </table>
  );
}
```

## Related Documentation

- [API Integration Architecture](./api-integration-architecture.md) - System architecture and design
- [React Query Documentation](https://tanstack.com/query/latest/docs/react/overview) - Official docs
- [Backend API Reference](../../api/docs/API_USAGE_EXAMPLES.md) - Complete API spec
