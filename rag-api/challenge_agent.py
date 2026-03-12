# Nome sugerido para este arquivo: challenge_agent.py

import os
import requests
import json
from io import BytesIO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from typing import Any, List
from operator import itemgetter # <<< ADICIONADO

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

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.8) # Temperatura um pouco mais alta

# --- Lógica de carregamento de múltiplos documentos ---
lista_de_documentos_pdf = [
    "Documentação Syna-2.pdf",
    "Documentação APS.pdf",
    "Documentação Alimentadores.pdf",
    "Documentação NEXA.pdf",
]
documentos_totais = []
print("Iniciando o carregamento dos documentos locais (Agente de Desafios)...")
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
    
    retriever = vector_db.as_retriever(
        search_type="mmr",
        search_kwargs={"k": 10, "fetch_k": 30}
    )
    print("Vector DB (MMR) criado com sucesso!")
else:
    print("Nenhum documento foi carregado. A API não pode iniciar o RAG.")
    retriever = None

# --- DEFINIÇÃO DA API COM FASTAPI ---
app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    message: str
    num_questions: int = 3 # <<< MODIFICADO: Adicionado com padrão 3

class ChallengeResponse(BaseModel):
    challenges: List[Any] 

# <<< INÍCIO DA MODIFICAÇÃO DO PROMPT >>>
prompt_template_desafio = ChatPromptTemplate.from_template("""
    Você é um "Mestre de Desafios" e sua especialidade é criar desafios de múltipla escolha com base em documentações técnicas, formatando a saída como um array JSON.

    Baseado no CONTEXTO (documentação) abaixo, crie {num_questions} DESAFIOS ESPECÍFICOS sobre a ÁREA DE APRENDIZADO (TÓPICO) fornecida.

    ÁREA DE APRENDIZADO (TÓPICO):
    {question}

    DOCUMENTAÇÃO (CONTEXTO):
    {context}

    === REGRAS OBRIGATÓRIAS ===
    1.  **Base no Contexto:** Os desafios DEVEM ser 100% baseados no contexto fornecido.
    2.  **Formato JSON OBRIGATÓRIO:** Sua resposta DEVE ser um único ARRAY JSON válido, contendo {num_questions} objetos de desafio. NÃO inclua ```json ```.
    3.  **SEMPRE CRIE {num_questions} DESAFIOS.**
    4.  **TIPO OBRIGATÓRIO: "multiple-choice"**: Todos os {num_questions} desafios criados DEVEM ser do tipo "multiple-choice".
    5.  **NÃO REPITA PERGUNTAS:** Garanta que os desafios sejam diferentes entre si.
    6.  **ESPECIFICIDADE (MUITO IMPORTANTE):**
        * Os desafios devem ser específicos sobre o TÓPICO ({question}).
        * Evite perguntas genéricas (ex: "O que é...?").
        * Crie perguntas sobre componentes, arquitetura, funcionalidades ou dados específicos descritos no contexto.
    7.  **REGRAS DE "multiple-choice":** Cada desafio deve ter 3 ou 4 opções em "options" e um "correctOptionId" válido.

    === ESTRUTURA JSON ESPERADA (ARRAY DE {num_questions} OBJETOS) ===
    [
      {{
        "id": "string",
        "title": "string",
        "description": "string",
        "type": "multiple-choice",
        "difficulty": "string (easy, medium, ou hard)",
        "options": [
            {{"id": "1", "text": "Texto da Opção 1"}},
            {{"id": "2", "text": "Texto da Opção 2"}},
            {{"id": "3", "text": "Texto da Opção 3"}}
        ],
        "correctOptionId": "string (ex: '2')",
        "codeTemplate": null,
        "expectedOutput": null
      }},
      {{ ... etc, até {num_questions} desafios ... }}
    ]
    
    Se não for possível gerar desafios com o contexto, retorne um array com um objeto de erro:
    [
      {{"id": "error", "title": "Erro de Contexto", "description": "Não foi possível criar desafios sobre '{question}' com a documentação atual.", "type": "error", "difficulty": "none"}}
    ]

    ARRAY JSON DE {num_questions} DESAFIOS GERADOS:
""")
# <<< FIM DA MODIFICAÇÃO DO PROMPT >>>

AGENT_CARD = {
  "a2a_version": "0.1.0",
  "id": "agent-challenge-generator-v1",
  "name": "Mestre de Desafios",
  "description": "Um agente especialista em criar desafios de múltipla escolha a partir de documentação técnica.",
  "capabilities": [
    {
      "id": "generate-multiple-choice",
      "description": "Gera N desafios de múltipla escolha sobre um tópico.", # MODIFICADO
      "type": "http",
      "endpoint": "/api/challenge", 
      "method": "POST",
      "request_schema": {
        "type": "object",
        "properties": {
          "message": { "type": "string", "description": "O tópico (ex: 'Python', 'Syna')" },
          "num_questions": { "type": "integer", "description": "Número de desafios a gerar (default: 3)" } # MODIFICADO
        },
        "required": ["message"]
      },
      "response_schema": {
        "type": "object",
        "properties": {
          "challenges": { "type": "array", "items": { "type": "object" } }
        }
      }
    }
  ]
}

@app.get("/.well-known/agent.json", response_model=None)
async def get_agent_card():
    return AGENT_CARD

# <<< INÍCIO DA MODIFICAÇÃO DA FUNÇÃO >>>
@app.post("/api/challenge", response_model=ChallengeResponse)
async def generate_challenge(request: ChatRequest) -> ChallengeResponse:
    error_challenge = {
        "id": "error-default", "title": "Erro Interno",
        "description": "Ocorreu um erro ao processar a solicitação.",
        "type": "error", "difficulty": "none"
    }

    if not retriever:
        error_challenge["description"] = "O sistema de busca (RAG) não foi inicializado."
        return ChallengeResponse(challenges=[error_challenge]) 

    # MODIFICADO: A chain agora espera um dicionário com "message" e "num_questions"
    rag_chain = (
        {
            "context": itemgetter("message") | retriever,
            "question": itemgetter("message"),
            "num_questions": itemgetter("num_questions")
        }
        | prompt_template_desafio
        | llm
        | StrOutputParser()
    )

    try:
        # MODIFICADO: Passa o dicionário para o invoke
        bot_response_string = rag_chain.invoke({
            "message": request.message,
            "num_questions": request.num_questions
        })
        
        try:
            # Limpeza
            clean_response_string = bot_response_string.strip().lstrip("```json").rstrip("```").strip()
            
            json_start = clean_response_string.find('[')
            json_end = clean_response_string.rfind(']')
            
            if json_start == -1 or json_end == -1 or json_end < json_start:
                 raise json.JSONDecodeError("Nenhum array JSON válido encontrado.", clean_response_string, 0)
                 
            json_string = clean_response_string[json_start:json_end+1]
            
            challenge_data = json.loads(json_string)
            
            if not isinstance(challenge_data, list):
                 raise ValueError("JSON retornado pelo LLM não é um array (lista).")

            if not challenge_data:
                raise ValueError("LLM retornou um array vazio.")

            return ChallengeResponse(challenges=challenge_data) 
        
        except json.JSONDecodeError as e:
            print(f"Erro: LLM não retornou ARRAY JSON válido. Erro: {e}. Resposta:\n{bot_response_string}")
            error_challenge["description"] = "O assistente não conseguiu formatar os desafios (JSON). Tente gerar novamente."
            return ChallengeResponse(challenges=[error_challenge])
        except ValueError as ve:
             print(f"Erro: {ve}. Resposta:\n{bot_response_string}")
             error_challenge["description"] = "O assistente não retornou a estrutura de array esperada. Tente gerar novamente."
             return ChallengeResponse(challenges=[error_challenge])

    except Exception as e:
        print(f"Erro inesperado na chain RAG: {e}")
        error_challenge["description"] = f"Erro interno no servidor: {e}"
        return ChallengeResponse(challenges=[error_challenge])
# <<< FIM DA MODIFICAÇÃO DA FUNÇÃO >>>

if __name__ == "__main__":
    import uvicorn
    print("Iniciando a API de DESAFIOS (v2 - Apenas Múltipla Escolha) em http://localhost:8001")
    uvicorn.run(app, host="0.0.0.0", port=8001)