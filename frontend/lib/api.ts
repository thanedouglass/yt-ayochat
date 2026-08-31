const API_BASE_URL = typeof window !== 'undefined' 
  ? window.location.origin 
  : process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000';

export interface HITLQueueItem {
  id: string;
  comment_id: string;
  video_id: string;
  video_title: string;
  author_name: string;
  input_comment: string;
  language: string;
  category: string;
  semiotic_intent: string;
  energy_level: number;
  polarity: number;
  model_draft_reply: string;
  applied_vectors: {
    code_switch_alpha: number;
    sovereignty_beta: string;
    frequency_gamma: number;
    token_economy_tau: string;
  };
  cultural_alignment_flag: boolean;
  rationale: string | null;
  status: string;
  telegram_message_id: number | null;
  human_verdict: string | null;
  human_score: number | null;
  final_dispatched_reply: string | null;
  diff_json: any;
  alignment_delta: number | null;
  created_at: string;
  updated_at: string;
}

export interface PWAResolveRequest {
  record_id: string;
  action: 'approve' | 'skip' | 'edit';
  edited_reply?: string;
  target_alpha?: number;
  notes?: string;
}

export interface PWAResolveResponse {
  status: string;
  action: string;
  record_id: string;
  comment_id: string;
  reply_text: string | null;
  alignment_delta: number;
  dispatched: boolean;
  message: string;
}

class APIError extends Error {
  constructor(
    message: string,
    public status?: number,
    public details?: any
  ) {
    super(message);
    this.name = 'APIError';
  }
}

async function fetchAPI<T>(
  endpoint: string,
  options: RequestInit = {}
): Promise<T> {
  const url = `${API_BASE_URL}${endpoint}`;
  
  const defaultOptions: RequestInit = {
    headers: {
      'Content-Type': 'application/json',
      ...options.headers,
    },
    ...options,
  };

  try {
    const response = await fetch(url, defaultOptions);
    
    if (!response.ok) {
      const errorData = await response.json().catch(() => ({}));
      throw new APIError(
        errorData.detail || `HTTP ${response.status}: ${response.statusText}`,
        response.status,
        errorData
      );
    }
    
    return await response.json();
  } catch (error) {
    if (error instanceof APIError) {
      throw error;
    }
    throw new APIError(`Network error: ${error instanceof Error ? error.message : 'Unknown error'}`);
  }
}

export const api = {
  // Queue endpoints
  getQueue: async (limit: number = 20, videoId?: string): Promise<HITLQueueItem[]> => {
    const params = new URLSearchParams();
    params.append('limit', limit.toString());
    if (videoId) {
      params.append('video_id', videoId);
    }
    
    return fetchAPI<HITLQueueItem[]>(`/api/queue?${params.toString()}`);
  },

  // Resolve endpoint
  resolveComment: async (request: PWAResolveRequest): Promise<PWAResolveResponse> => {
    return fetchAPI<PWAResolveResponse>('/api/resolve', {
      method: 'POST',
      body: JSON.stringify(request),
    });
  },

  // Health check
  healthCheck: async () => {
    return fetchAPI('/api/health');
  },
};