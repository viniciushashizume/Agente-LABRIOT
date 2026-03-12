// src/lib/api.ts

import { Challenge } from "@/types/challenge"; // Importe o tipo Challenge

const API_BASE_URL = import.meta.env.VITE_API_URL || "http://localhost:8000";
const CHALLENGE_API_BASE_URL = import.meta.env.VITE_CHALLENGE_API_URL || "http://localhost:8001";
// +++ ADICIONADO: URL do Agente de Validação (porta 8002) +++
const VALIDATION_API_BASE_URL = import.meta.env.VITE_VALIDATION_API_URL || "http://localhost:8002";


// Endpoints específicos
export const CHAT_ENDPOINT = `${API_BASE_URL}/api/chat`;
export const CHALLENGE_ENDPOINT = `${CHALLENGE_API_BASE_URL}/api/challenge`;
// +++ ADICIONADO: Endpoint de Validação +++
export const VALIDATION_ENDPOINT = `${VALIDATION_API_BASE_URL}/api/validate`;

export interface ChatApiRequest {
  message: string;
  num_questions?: number; // <<< ADICIONADO
}

export interface ChatApiResponse {
  response: string;
}

export interface ChallengeApiResponse {
  challenges: Challenge[];
}

// +++ ADICIONADO: Interfaces para a API de Validação +++
export interface ValidationApiRequest {
  challenge: Challenge;
  user_answer: string;
}

export interface ValidationApiResponse {
  is_correct: boolean;
  feedback: string;
}


/**
 * Send a message to the RAG API and get a response
 */
/**
 * Send a message to the RAG API and get a response
 */
export async function sendChatMessage(message: string): Promise<string> {
  try {
    const response = await fetch(CHAT_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // CORREÇÃO: Enviando 'user_question' para bater com o modelo do main.py
      body: JSON.stringify({ user_question: message }), 
    });

    if (!response.ok) {
      throw new Error(`Chat API error: ${response.status} ${response.statusText}`);
    }

    const data: ChatApiResponse = await response.json();
    return data.response;
  } catch (error) {
    console.error("Error calling chat API:", error);
    throw error;
  }
}
/**
 * Sends a topic to the Challenge Agent API and gets a challenge object.
 */
// <<< MODIFICADA A ASSINATURA DA FUNÇÃO >>>
export async function generateChallenges(topic: string, numQuestions?: number): Promise<ChallengeApiResponse> {
  try {
    const response = await fetch(CHALLENGE_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      // <<< MODIFICADO O CORPO DA REQUISIÇÃO >>>
      body: JSON.stringify({ message: topic, num_questions: numQuestions } as ChatApiRequest),
    });

    if (!response.ok) {
      let errorDetail = `Challenge API error: ${response.status} ${response.statusText}`;
      try {
          const errorJson = await response.json();
          errorDetail = errorJson.detail || errorDetail;
      } catch (e) { /* Ignora se não for JSON */ }
      throw new Error(errorDetail);
    }

    const data: ChallengeApiResponse = await response.json();
    return data; // Retorna o objeto { challenges: [...] }
  } catch (error) {
    console.error("Error calling challenge API:", error);
    return {
      challenges: [{
        id: "error-fetch",
        title: "Erro de Rede",
        description: error instanceof Error ? error.message : "Não foi possível conectar à API de desafios.",
        type: "error",
        difficulty: "none"
      }]
    };
  }
}

// +++ ADICIONADO: Nova função para validar a resposta +++
/**
 * Sends a challenge and the user's answer to the Validation Agent.
 *
 * @param challenge - The full challenge object
 * @param user_answer - The user's submitted answer
 * @returns Promise with the validation result (is_correct and feedback)
 */
export async function validateChallengeAnswer(
  challenge: Challenge,
  user_answer: string
): Promise<ValidationApiResponse> {
  try {
    const response = await fetch(VALIDATION_ENDPOINT, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ challenge, user_answer } as ValidationApiRequest),
    });

    if (!response.ok) {
      let errorDetail = `Validation API error: ${response.status} ${response.statusText}`;
      try {
          const errorJson = await response.json();
          errorDetail = errorJson.detail || errorDetail;
      } catch (e) { /* Ignora se não for JSON */ }
      throw new Error(errorDetail);
    }

    const data: ValidationApiResponse = await response.json();
    return data;
  } catch (error) {
    console.error("Error calling validation API:", error);
    // Retorna uma resposta de erro estruturada
    return {
      is_correct: false,
      feedback: "Erro ao conectar com o agente de validação. Por favor, tente novamente."
    };
  }
}