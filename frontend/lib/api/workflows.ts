/**
 * Workflow API client for LangOrch v0.4
 *
 * Provides methods for workflow execution, streaming, and session management.
 */
import apiClient from '../api-client';
import type {
  Workflow,
  WorkflowExecution,
  WorkflowExecuteRequest,
  WorkflowExecuteResponse,
  WorkflowResumeRequest,
  ConversationSession,
  ConversationSessionCreate,
  Message,
  MessageCreate,
  HITLApproval,
  HITLApprovalRespondRequest
} from '../types';

// ========== SSE Streaming Types & Helper ==========

export interface StreamEventHandler {
  onStart?: () => void;
  onUpdate?: (data: any) => void;
  onDone?: (data: any) => void;
  onError?: (error: string) => void;
}

/**
 * Stream workflow execution via Server-Sent Events
 * @deprecated workflow_config parameter will be removed. Backend now uses unified workflow.
 */
function streamWorkflow(
  request: WorkflowExecuteRequest,
  handlers: StreamEventHandler
): EventSource {
  // Get token for authentication
  const token = localStorage.getItem('access_token');

  // Build URL with query params
  const params = new URLSearchParams({
    user_input: request.user_input,
    ...(request.session_id && { session_id: request.session_id }),
    ...(request.workflow_id && { workflow_id: request.workflow_id }),
    ...(token && { token }),
    // workflow_config is deprecated but kept for backward compatibility
    ...(request.workflow_config && { workflow_config: JSON.stringify(request.workflow_config) })
  });

  const baseURL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
  const url = `${baseURL}/workflows/execute/stream?${params}`;

  const eventSource = new EventSource(url);

  eventSource.addEventListener('start', () => {
    handlers.onStart?.();
  });

  eventSource.addEventListener('update', (e) => {
    try {
      const data = JSON.parse(e.data);
      handlers.onUpdate?.(data);
    } catch (err) {
      console.error('Failed to parse update event:', err);
    }
  });

  eventSource.addEventListener('done', (e) => {
    try {
      const data = JSON.parse(e.data);
      handlers.onDone?.(data);
    } catch (err) {
      console.error('Failed to parse done event:', err);
    }
    eventSource.close();
  });

  eventSource.addEventListener('error', (e: any) => {
    const errorMsg = e.data ? JSON.parse(e.data).error : 'Stream error';
    handlers.onError?.(errorMsg);
    eventSource.close();
  });

  return eventSource;
}

export const workflowsApi = {
  // ========== Workflow Execution ==========

  /**
   * Execute workflow to completion (synchronous)
   */
  executeWorkflow: async (request: WorkflowExecuteRequest): Promise<WorkflowExecuteResponse> => {
    const response = await apiClient.post('/workflows/execute', request);
    return response.data;
  },

  /**
   * Resume interrupted workflow (HITL)
   */
  resumeWorkflow: async (request: WorkflowResumeRequest): Promise<any> => {
    const response = await apiClient.post('/workflows/resume', request);
    return response.data;
  },

  /**
   * Stream workflow execution via Server-Sent Events
   */
  streamWorkflow: (request: WorkflowExecuteRequest, handlers: StreamEventHandler): EventSource => {
    return streamWorkflow(request, handlers);
  },

  // ========== Session Management ==========

  /**
   * Create new conversation session
   */
  createSession: async (data: ConversationSessionCreate): Promise<ConversationSession> => {
    const response = await apiClient.post('/workflows/sessions', data);
    return response.data;
  },

  /**
   * List user's conversation sessions
   */
  listSessions: async (limit = 50, offset = 0): Promise<ConversationSession[]> => {
    const response = await apiClient.get('/workflows/sessions', {
      params: { limit, offset }
    });
    return response.data;
  },

  /**
   * Get session by ID
   */
  getSession: async (sessionId: string): Promise<ConversationSession> => {
    const response = await apiClient.get(`/workflows/sessions/${sessionId}`);
    return response.data;
  },

  // ========== Message Management ==========

  /**
   * Get messages for a session
   */
  getMessages: async (sessionId: string, limit = 100): Promise<Message[]> => {
    const response = await apiClient.get(`/workflows/sessions/${sessionId}/messages`, {
      params: { limit }
    });
    return response.data;
  },

  /**
   * Add message to session
   */
  addMessage: async (sessionId: string, message: MessageCreate): Promise<Message> => {
    const response = await apiClient.post(`/workflows/sessions/${sessionId}/messages`, message);
    return response.data;
  },
};

export const hitlApi = {
  // ========== HITL Approvals ==========

  /**
   * List pending approval requests
   */
  listPendingApprovals: async (): Promise<HITLApproval[]> => {
    const response = await apiClient.get('/hitl/approvals/pending');
    return response.data;
  },

  /**
   * Get approval by ID
   */
  getApproval: async (approvalId: string): Promise<HITLApproval> => {
    const response = await apiClient.get(`/hitl/approvals/${approvalId}`);
    return response.data;
  },

  /**
   * Respond to approval request
   */
  respondToApproval: async (
    approvalId: string,
    request: HITLApprovalRespondRequest
  ): Promise<HITLApproval> => {
    const response = await apiClient.post(`/hitl/approvals/${approvalId}/respond`, request);
    return response.data;
  },

  /**
   * List all approvals with optional status filter
   */
  listApprovals: async (
    statusFilter?: 'pending' | 'approved' | 'rejected',
    limit = 50,
    offset = 0
  ): Promise<HITLApproval[]> => {
    const response = await apiClient.get('/hitl/approvals', {
      params: {
        status_filter: statusFilter,
        limit,
        offset
      }
    });
    return response.data;
  },
};
