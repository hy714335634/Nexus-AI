/**
 * Nexus AI v2 Hooks - 统一导出
 */

// Projects
export {
  projectKeys,
  useProjectsV2,
  useProjectDetailV2,
  useProjectStagesV2,
  useBuildDashboardV2,
  useCreateProjectV2,
  useControlProjectV2,
  useDeleteProjectV2,
} from './use-projects-v2';

// Agents
export {
  agentKeys,
  useAgentsV2,
  useAgentDetailV2,
  useInvokeAgentV2,
  useDeleteAgentV2,
} from './use-agents-v2';

// Sessions
export {
  sessionKeys,
  useAgentSessionsV2,
  useSessionDetailV2,
  useSessionMessagesV2,
  useCreateSessionV2,
  useSendMessageV2,
  useDeleteSessionV2,
  useStreamingChatV2,
  type StreamingState,
} from './use-sessions-v2';

// Statistics
export {
  statisticsKeys,
  useStatisticsOverviewV2,
  useBuildStatisticsV2,
  useInvocationStatisticsV2,
} from './use-statistics-v2';
