// frontend/lib/types.ts

export interface User {
  token: string;
  username: string;
  role: string;
  accessible_collections: string[];
}

export interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  sources?: {
    source_document: string;
    section_title: string;
    collection: string;
  }[];
  retrieval_type?: "hybrid_rag" | "sql_rag";
  sql?: string;
  timestamp: Date;
}