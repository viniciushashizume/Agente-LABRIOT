# validation_agent.py

import os
import json
import re
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any
from operator import itemgetter
from pymongo import MongoClient

# Importações do LangChain
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURAÇÃO INICIAL E CARREGAMENTO DO MODELO ---

# Utilizando a API do Google para Embeddings em vez de modelo local
embeddings = GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.1) 

# --- CONEXÃO COM MONGODB ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "rag_db"
COLLECTION_NAME = "documentos"
INDEX_NAME = "vector_index"

client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

print("Conectando ao MongoDB Atlas (Agente de Validação)...")
vector_db = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX_NAME
)

# Retriever focado em relevância (k=5)
retriever = vector_db.as_retriever(search_kwargs={"k": 5})
print("Conexão com Vector DB estabelecida com sucesso!")

# --- DEFINIÇÃO DA API COM FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ValidationRequest(BaseModel):
    challenge: Any
    user_answer: str

class ValidationResponse(BaseModel):
    is_correct: bool
    feedback: str

prompt_template_validation = ChatPromptTemplate.from_template("""
    Você é um Agente Avaliador robótico e implacável. Sua única missão é
    determinar se a "RESPOSTA DO USUÁRIO" é factualmente correta,
    baseando-se EXCLUSIVAMENTE no "CONTEXTO DA DOCUMENTAÇÃO (GABARITO)".

    CONTEXTO DA DOCUMENTAÇÃO (GABARITO):
    {context}

    DESAFIO ORIGINAL (em JSON):
    {challenge_json}

    RESPOSTA DO USUÁRIO:
    {user_answer}

    === REGRAS DE AVALIAÇÃO IMPLACÁVEIS ===
    1.  **VERDADE ABSOLUTA:** O "CONTEXTO" é a única fonte da verdade.
    2.  **SEM CONTEXTO, SEM PONTOS:** Se a "RESPOSTA DO USUÁRIO" não tiver absolutamente NENHUMA semelhança semântica ou factual com o "CONTEXTO", ela está 100% INCORRETA.
    3.  **AVALIAÇÃO DE 'ESSAY' (MUITO IMPORTANTE):**
        * Para 'essay', a "RESPOSTA DO USUÁRIO" DEVE refletir os fatos, conceitos e informações presentes no "CONTEXTO".
        * Avalie se a resposta é completa e precisa.
    4.  **AVALIAÇÃO DE 'MULTIPLE-CHOICE':**
        * Verifique se a 'user_answer' (que deve ser um 'id' de opção) corresponde ao 'correctOptionId' no JSON do desafio.
    5.  **AVALIAÇÃO DE 'CODE':**
        * Avalie se o código na 'user_answer' resolve a 'description' corretamente.

    === FEEDBACK ===
    * Se CORRETO: Parabenize e reforce o porquê está correto ("Correto! A resposta está alinhada com a documentação que diz: ...").
    * Se INCORRETO: Explique educadamente o porquê está incorreto e qual seria a resposta correta, CITANDO o "CONTEXTO".

    === OBJETO JSON DE SAÍDA (Sua resposta DEVE ser apenas este JSON) ===
    {{
      "is_correct": boolean,
      "feedback": "string (Explique o porquê está correto ou incorreto, com base no CONTEXTO.)"
    }}

    OBJETO JSON DE AVALIAÇÃO:
""")

@app.post("/api/validate", response_model=ValidationResponse)
async def validate_answer(request: ValidationRequest) -> ValidationResponse:
    if not retriever:
        return ValidationResponse(is_correct=False, feedback="Sistema RAG não inicializado.")
        
    if not isinstance(request.challenge, dict):
        return ValidationResponse(is_correct=False, feedback="Desafio inválido: 'challenge' deve ser JSON.")

    challenge_json_string = json.dumps(request.challenge, ensure_ascii=False, indent=2)
    search_query = request.challenge.get("description", "") + " " + request.user_answer

    validation_chain = (
        {
            "context": itemgetter("search_query") | retriever,
            "challenge_json": itemgetter("challenge_json"),
            "user_answer": itemgetter("user_answer")
        }
        | prompt_template_validation
        | llm
        | StrOutputParser()
    )

    try:
        raw_response = validation_chain.invoke({
            "search_query": search_query,
            "challenge_json": challenge_json_string,
            "user_answer": request.user_answer
        })

        json_str = raw_response
        if "```json" in raw_response:
            json_str = re.search(r"```json\s*([\s\S]+?)\s*```", raw_response).group(1).strip()
        elif raw_response.strip().startswith("{") and raw_response.strip().endswith("}"):
             json_str = raw_response.strip()

        result_json = json.loads(json_str)

        return ValidationResponse(
            is_correct=result_json["is_correct"],
            feedback=result_json["feedback"]
        )

    except Exception as e:
        print(f"Erro inesperado: {e}")
        return ValidationResponse(is_correct=False, feedback="Erro ao processar a avaliação.")

def invoke_validation_agent(question: str, response: str) -> str:
    if not retriever:
        return "Erro: O sistema de busca (RAG) não foi inicializado."

    mock_challenge = {"description": question, "type": "essay"}
    challenge_json_string = json.dumps(mock_challenge, ensure_ascii=False)
    search_query = question + " " + response

    validation_chain = (
        {
            "context": itemgetter("search_query") | retriever,
            "challenge_json": itemgetter("challenge_json"),
            "user_answer": itemgetter("user_answer")
        }
        | prompt_template_validation
        | llm
        | StrOutputParser()
    )

    try:
        raw_response = validation_chain.invoke({
            "search_query": search_query,
            "challenge_json": challenge_json_string,
            "user_answer": response
        })

        json_str = raw_response
        if "```json" in raw_response:
            match = re.search(r"```json\s*([\s\S]+?)\s*```", raw_response)
            if match: json_str = match.group(1).strip()
        elif raw_response.strip().startswith("{") and raw_response.strip().endswith("}"):
             json_str = raw_response.strip()

        result_json = json.loads(json_str)
        status = "✅ CORRETO" if result_json.get("is_correct") else "❌ INCORRETO"
        return f"{status} - {result_json.get('feedback', '')}"
        
    except Exception as e:
        return f"Erro ao validar resposta: {e}"

if __name__ == "__main__":
    import uvicorn
    print("Iniciando a API de VALIDAÇÃO (v4) em http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)