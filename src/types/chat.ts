// Type definitions for chat application

export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant";
  timestamp: Date;
  validation_response?: string | null;
}

export interface ChatSession {
  id: string;
  title: string;
  messages: Message[];
  createdAt: Date;
  updatedAt: Date;
}

export type MessageRole = "user" | "assistant";
