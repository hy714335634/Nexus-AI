import { apiFetch } from '@/lib/api-client';
import type { CreateAgentRequest, CreateAgentResponse } from '@/types/api';

export async function createAgent(request: CreateAgentRequest) {
  const response = await apiFetch<CreateAgentResponse>(
    '/api/v1/agents/create',
    {
      method: 'POST',
      body: JSON.stringify(request),
    },
  );

  if (!response.success) {
    throw new Error('Failed to submit agent build request');
  }

  return response.data;
}
