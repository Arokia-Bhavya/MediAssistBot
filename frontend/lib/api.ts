// frontend/lib/api.ts

import axios from "axios";

const BASE_URL = "http://localhost:8000";

export interface LoginResponse {
  token: string;
  username: string;
  role: string;
  accessible_collections: string[];
}

export interface Source {
  source_document: string;
  section_title: string;
  collection: string;
}

export interface ChatResponse {
  answer: string;
  sources: Source[];
  retrieval_type: "hybrid_rag" | "sql_rag";
  role: string;
  sql?: string;
}

export async function login(
  username: string,
  password: string
): Promise<LoginResponse> {
  const res = await axios.post(`${BASE_URL}/login`, { username, password });
  return res.data;
}

export async function chat(
  question: string,
  token: string
): Promise<ChatResponse> {
  const res = await axios.post(
    `${BASE_URL}/chat`,
    { question },
    { headers: { Authorization: `Bearer ${token}` } }
  );
  return res.data;
}