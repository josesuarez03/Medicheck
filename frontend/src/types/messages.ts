export interface Message {
  id: string;
  content: string;
  sender: "user" | "bot" | "system";
  status?: "pending" | "sent" | "error";
  timestamp: string;
}

export interface ConversationState {
  missing_questions?: string[];
  questions_selected?: string[];
  [key: string]: unknown;
}

export interface DecisionFlags {
  owner?: "llm_primary" | "combined_emergency" | "expert_primary" | "expert_fallback";
  expert_guard_applied?: boolean;
  expert_case_id?: string;
  expert_action?: "ask" | "advise" | "fallback_ai" | "escalate" | string;
  reasons?: string[];
  turn_number?: number;
  pain?: {
    reported?: boolean;
    asked_now?: boolean;
    must_ask?: boolean;
  };
}

export interface ChatResponsePayload {
  user_message?: string;
  ai_response?: string;
  response?: string;
  timestamp?: string;
  error?: string;
  error_code?: string;
  conversation_id?: string;
  triaje_level?: string;
  final_chat_summary?: string;
  final_chat_summary_title?: string;
  conversation_state?: ConversationState;
  decision_flags?: DecisionFlags;
  [key: string]: unknown;
}

export type LifecycleStatus = "active" | "archived" | "deleted";

export interface ConversationSummary {
  _id: string;
  timestamp?: string;
  triaje_level?: string;
  symptoms?: string[];
  lifecycle_status?: LifecycleStatus;
  archived_at?: string | null;
  deleted_at?: string | null;
  purge_after?: string | null;
  active?: boolean;
  messages?: Array<{
    role: string;
    content: string;
  }>;
}

export interface ConversationDetail extends ConversationSummary {
  medical_context?: Record<string, unknown>;
  pain_scale?: number;
  symptoms_pattern?: Record<string, unknown> | string;
  user_id?: string;
}
