import { apiRequest } from "./api";

export interface AssistantCitation {
  source_id: number;
  title: string | null;
  url: string;
  document_title: string | null;
  chunk_index: number | null;
  last_verified_at: string | null;
  verification_status: string;
}

export interface AssistantMessage {
  id: number;
  role: "user" | "assistant";
  content: string;
  citations: AssistantCitation[];
  feedback: "helpful" | "not_helpful" | null;
  created_at: string;
}

export interface AssistantConversationSummary {
  id: number;
  title: string | null;
  updated_at: string;
}

export interface AssistantConversation extends AssistantConversationSummary {
  messages: AssistantMessage[];
}

export interface AssistantChatResponse {
  conversation_id: number;
  intent: string;
  user_message: AssistantMessage;
  assistant_message: AssistantMessage;
  suggested_questions: string[];
  validation_flags: string[];
  retrieval_warning: string | null;
}

export const assistantService = {
  createConversation: () =>
    apiRequest<AssistantConversation>("/api/v1/assistant/conversations", {
      method: "POST",
    }),
  listConversations: () =>
    apiRequest<AssistantConversationSummary[]>("/api/v1/assistant/conversations"),
  getConversation: (conversationId: number) =>
    apiRequest<AssistantConversation>(
      `/api/v1/assistant/conversations/${conversationId}`,
    ),
  sendMessage: (conversationId: number, message: string) =>
    apiRequest<AssistantChatResponse>(
      `/api/v1/assistant/conversations/${conversationId}/messages`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ message }),
      },
    ),
  sendFeedback: (
    conversationId: number,
    messageId: number,
    feedback: "helpful" | "not_helpful",
  ) =>
    apiRequest<AssistantMessage>(
      `/api/v1/assistant/conversations/${conversationId}/messages/${messageId}/feedback`,
      {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ feedback }),
      },
    ),
};
