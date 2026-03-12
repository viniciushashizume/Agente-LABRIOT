# Nome sugerido para este arquivo: validation_agent.py
# VERSÃO COM CORREÇÃO DEFINITIVA (AGORA USANDO RAG/LLM PARA FEEDBACK)

import os
import requests
import json
from io import BytesIO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List
from operator import itemgetter # Importe itemgetter

# Importações do LangChain
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser


# Carregue sua chave de API a partir de um arquivo .env (recomendado)
from dotenv import load_dotenv
load_dotenv()

from collections import Counter
import re

# --- CONFIGURAÇÃO INICIAL E CARREGAMENTO DO MODELO ---
model_name = "sentence-transformers/all-MiniLM-L6-v2"
model_kwargs = {'device': 'cpu'}
encode_kwargs = {'normalize_embeddings': False}

try:
    embeddings = HuggingFaceEmbeddings(
        model_name=model_name,
        model_kwargs=model_kwargs,
        encode_kwargs=encode_kwargs
    )
except Exception as e:
    print(f"Erro ao carregar o modelo de embedding: {e}")
    exit()

# LLM para validação (temperatura baixa para ser um "juiz" rigoroso)
llm = ChatGoogleGenerativeAI(model="gemini-2.5-pro", temperature=0.1) 

lista_de_documentos_pdf = [
    "Documentação Syna-2.pdf",
    "Documentação APS.pdf",
    "Documentação Alimentadores.pdf",
    "Documentação NEXA.pdf",
    ]
documentos_totais = []
print("Iniciando o carregamento dos documentos locais (Agente de Validação)...")
for caminho_do_pdf in lista_de_documentos_pdf:
    try:
        if not os.path.exists(caminho_do_pdf):
            print(f"Erro: Arquivo não encontrado no caminho: {caminho_do_pdf}")
            print(f"Pulando o arquivo '{caminho_do_pdf}'...")
            continue
        loader = PyPDFLoader(caminho_do_pdf)
        paginas = loader.load()
        documentos_totais.extend(paginas)
        print(f"Documento '{caminho_do_pdf}' carregado com sucesso ({len(paginas)} páginas).")
    except Exception as e:
        print(f"Erro ao processar o PDF '{caminho_do_pdf}': {e}")
        print(f"Pulando o arquivo '{caminho_do_pdf}'...")
print(f"\nCarregamento concluído. Total de páginas de todos os documentos: {len(documentos_totais)}")

# --- Dividir os documentos e criar o Vector DB ---
vector_db = None
if documentos_totais:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documentos_totais)
    print(f"Criando Vector DB com {len(chunks)} chunks de {len(lista_de_documentos_pdf)} documento(s)...")
    vector_db = FAISS.from_documents(chunks, embeddings)
    
    # Retriever padrão focado em relevância (k=5)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})
    print("Vector DB (Validação) criado com sucesso!")
else:
    print("Nenhum documento foi carregado. A API não pode iniciar o RAG.")
    retriever = None

# --- DEFINIÇÃO DA API COM FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Permite todas as origens (ajuste para produção)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Modelos Pydantic para Validação ---

class ValidationRequest(BaseModel):
    challenge: Any   # O objeto JSON completo do desafio gerado
    user_answer: str # A resposta que o usuário forneceu

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
    2.  **SEM CONTEXTO, SEM PONTOS:** Se a "RESPOSTA DO USUÁRIO"
        (ex: "batata", "não sei", "asdfg") não tiver absolutamente NENHUMA semelhança
        semântica ou factual com o "CONTEXTO", ela está 100% INCORRETA.
    3.  **AVALIAÇÃO DE 'ESSAY' (MUITO IMPORTANTE):**
        * Para 'essay', a "RESPOSTA DO USUÁRIO" DEVE refletir os fatos,
          conceitos e informações presentes no "CONTEXTO".
        * Avalie se a resposta é completa e precisa.
        * Respostas genéricas, vagas ou factualmente incorretas (como "batata") DEVEM ser
          marcadas como `is_correct: false`.
    4.  **AVALIAÇÃO DE 'MULTIPLE-CHOICE':**
        * Verifique se a 'user_answer' (que deve ser um 'id' de opção)
          corresponde ao 'correctOptionId' no JSON do desafio.
    5.  **AVALIAÇÃO DE 'CODE':**
        * Avalie se o código na 'user_answer' resolve a 'description'
          corretamente, com base nos conceitos do "CONTEXTO". Verifique se
          cumpre o 'expectedOutput', se houver.

    === FEEDBACK ===
    * Se CORRETO: Parabenize e reforce o porquê está correto ("Correto! A
      resposta está alinhada com a documentação que diz: ...").
    * Se INCORRETO: Explique educadamente o porquê está incorreto e qual
      seria a resposta correta, CITANDO o "CONTEXTO".
      (ex: "Incorreto. A resposta 'batata' não tem relação com o
      assunto. A documentação indica que a resposta correta é...")

    === OBJETO JSON DE SAÍDA (Sua resposta DEVE ser apenas este JSON) ===
    {{
      "is_correct": boolean,
      "feedback": "string (Explique o porquê está correto ou incorreto,
                        com base no CONTEXTO.)"
    }}

    OBJETO JSON DE AVALIAÇÃO:
""")


AGENT_CARD = {
  "a2a_version": "0.1.0",
  "id": "agent-challenge-validator-v1",
  "name": "Avaliador Implacável",
  "description": "Um agente especialista em validar se uma resposta de usuário é correta, baseado em documentação.",
  "capabilities": [
    {
      "id": "validate-answer",
      "description": "Valida a resposta de um usuário para um desafio específico.",
      "type": "http",
      "endpoint": "/api/validate", # Endpoint existente
      "method": "POST",
      "request_schema": {
        "type": "object",
        "properties": {
          "challenge": { "type": "object", "description": "O objeto de desafio original" },
          "user_answer": { "type": "string", "description": "A resposta fornecida pelo usuário" }
        },
        "required": ["challenge", "user_answer"]
      },
      "response_schema": {
        "type": "object",
        "properties": {
          "is_correct": { "type": "boolean" },
          "feedback": { "type": "string" }
        }
      }
    }
  ]
}

@app.get("/.well-known/agent.json", response_model=None)
async def get_agent_card():
    """
    Endpoint de Descoberta do A2A Protocol.
    Retorna o Agent Card que descreve as capacidades deste agente.
    """
    return AGENT_CARD

# === FUNÇÃO MODIFICADA ===
@app.post("/api/validate", response_model=ValidationResponse)
async def validate_answer(request: ValidationRequest) -> ValidationResponse:
    """
    Validação RAG-based (LLM) para fornecer feedback explicativo.
    """

    print("\n--- DEBUG validate_answer (RAG-LLM): Entrada recebida ---")
    print(f"challenge (preview): {json.dumps(request.challenge, indent=2)[:1000]}")  # limita comprimento no log
    print(f"user_answer: {request.user_answer}")

    # Verifica se o RAG está pronto
    if not retriever:
        return ValidationResponse(
            is_correct=False,
            feedback="Desculpe, o sistema de RAG (Validação) não foi inicializado. Documentos não carregados."
        )
        
    # Segurança: campos obrigatórios
    if not isinstance(request.challenge, dict):
        return ValidationResponse(
            is_correct=False,
            feedback="Desafio inválido: 'challenge' deve ser um objeto JSON."
        )

    # Para o LLM, o objeto JSON do desafio deve ser uma string formatada
    challenge_json_string = json.dumps(request.challenge, ensure_ascii=False, indent=2)
    
    # O que o retriever deve buscar? O contexto do desafio + a resposta do usuário.
    # Isso ajuda a encontrar os trechos mais relevantes da documentação.
    search_query = request.challenge.get("description", "") + " " + request.user_answer

    # Definir a chain de validação
    # Usamos os componentes que já foram carregados (llm, retriever, prompt)
    validation_chain = (
        {
            "context": itemgetter("search_query") | retriever, # Usa a query para buscar
            "challenge_json": itemgetter("challenge_json"),   # Passa a string JSON
            "user_answer": itemgetter("user_answer")          # Passa a resposta do usuário
        }
        | prompt_template_validation
        | llm
        | StrOutputParser() # O LLM vai retornar uma string JSON
    )

    try:
        # Invocar a chain
        raw_response = validation_chain.invoke({
            "search_query": search_query,
            "challenge_json": challenge_json_string,
            "user_answer": request.user_answer
        })

        print(f"DEBUG: Resposta crua do LLM: {raw_response}")

        # O LLM deve retornar um JSON string. Vamos limpá-lo e carregá-lo.
        # Às vezes o LLM adiciona ```json ... ``` ao redor da resposta
        json_str = raw_response
        if "```json" in raw_response:
            json_str = re.search(r"```json\s*([\s\S]+?)\s*```", raw_response).group(1).strip()
        elif raw_response.strip().startswith("{") and raw_response.strip().endswith("}"):
             json_str = raw_response.strip()
        else:
             # Se não for um JSON claro, algo deu errado no prompt
             raise ValueError(f"A saída do LLM não foi um JSON esperado. Saída: {raw_response}")


        # Tentar carregar o JSON
        result_json = json.loads(json_str)

        # Garantir que os campos esperados estão lá
        if "is_correct" not in result_json or "feedback" not in result_json:
            raise ValueError("JSON de saída do LLM está mal formatado. Faltando chaves 'is_correct' ou 'feedback'.")

        # Retornar a resposta pydantic
        # O feedback agora conterá a explicação detalhada gerada pelo LLM
        return ValidationResponse(
            is_correct=result_json["is_correct"],
            feedback=result_json["feedback"]
        )

    except json.JSONDecodeError as e:
        print(f"Erro de JSONDecodeError: {e}")
        print(f"String com falha: {json_str}")
        return ValidationResponse(
            is_correct=False,
            feedback=f"Ocorreu um erro ao processar a avaliação. A resposta do avaliador não foi um JSON válido. (Raw: {raw_response})"
        )
    except Exception as e:
        print(f"Erro inesperado na chain de validação: {e}")
        return ValidationResponse(
            is_correct=False,
            feedback=f"Ocorreu um erro inesperado durante a validação: {str(e)}"
        )

# --- FUNÇÃO PARA INTEGRAÇÃO COM MAIN.PY ---
def invoke_validation_agent(question: str, response: str) -> str:
    """
    Função auxiliar para permitir que o main.py importe e chame o agente diretamente.
    """
    if not retriever:
        return "Erro: O sistema de busca (RAG) não foi inicializado no Agente de Validação."

    # Cria um desafio simulado ('mock') apenas para encaixar no formato que o prompt exige
    mock_challenge = {
        "description": question,
        "type": "essay"
    }
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

        # Limpar o retorno do LLM para pegar apenas o JSON
        json_str = raw_response
        if "```json" in raw_response:
            match = re.search(r"```json\s*([\s\S]+?)\s*```", raw_response)
            if match:
                json_str = match.group(1).strip()
        elif raw_response.strip().startswith("{") and raw_response.strip().endswith("}"):
             json_str = raw_response.strip()

        result_json = json.loads(json_str)
        
        # Retorna apenas o feedback formatado
        status = "✅ CORRETO" if result_json.get("is_correct") else "❌ INCORRETO"
        return f"{status} - {result_json.get('feedback', '')}"
        
    except Exception as e:
        print(f"Erro na execução do invoke_validation_agent: {e}")
        return f"Erro ao validar resposta: {e}"

if __name__ == "__main__":
    import uvicorn
    print("Iniciando a API de VALIDAÇÃO (v4 - Agora com RAG/LLM) em http://localhost:8002")
    uvicorn.run(app, host="0.0.0.0", port=8002)