import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# Importações do LangChain
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_google_genai import ChatGoogleGenerativeAI, GoogleGenerativeAIEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

from dotenv import load_dotenv
load_dotenv()

from challenge_agent import invoke_challenge_agent 
from validation_agent import invoke_validation_agent

# --- CONFIGURAÇÃO INICIAL E CARREGAMENTO DO MODELO ---

def get_embeddings():
    """Usa a API do Google para Embeddings. Zero consumo de memória local."""
    # O modelo 'text-embedding-004' é o padrão atual do Google para RAG
    return GoogleGenerativeAIEmbeddings(model="models/text-embedding-004")

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3) 

# --- CONEXÃO COM MONGODB E INICIALIZAÇÃO DO VECTOR STORE ---

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "rag_db"
COLLECTION_NAME = "documentos"
INDEX_NAME = "vector_index"

client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

vector_db = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=get_embeddings(),
    index_name=INDEX_NAME
)

retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# --- DEFINIÇÃO DA API COM FASTAPI ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",   
        "http://127.0.0.1:5173",   
        "http://localhost:3000"    
    ], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ChatRequest(BaseModel):
    user_question: str

class ChatResponse(BaseModel):
    id: str = "default-id"
    sender: str = "agent"
    content: str = ""
    validation_response: str | None = None
    response: str | None = None 

prompt_template = ChatPromptTemplate.from_template("""
    Você é um assistente técnico especializado e um tutor de programação.
    Sua base de conhecimento principal contém documentações de projetos internos e linguagens.

    REGRAS:
    1.  **Priorize o Contexto:** Responda com base no CONTEXTO fornecido sempre que possível (especialmente para os projetos Syna, NEXA, etc).
    2.  **Seja Didático:** Explique passo a passo e mostre exemplos de código.
    3.  **Flexibilidade para Programação Básica:** Se a pergunta for sobre SINTAXE BÁSICA (ex: como declarar uma variável, loops) e isso não estiver no CONTEXTO, você PODE usar seu conhecimento prévio de C++, Python ou JavaScript para ensinar o usuário.
    4.  **Projetos Internos:** Se a pergunta for sobre um projeto interno e não estiver no contexto, diga que não sabe.
    CONTEXTO:
    {context}

    PERGUNTA DO USUÁRIO:
    {question}

    RESPOSTA DO ASSISTENTE:
""")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    labriot_response_text = invoke_challenge_agent(request.user_question)
    validation_explanation = invoke_validation_agent(
        question=request.user_question,
        response=labriot_response_text
    )

    return ChatResponse(
        id="some-unique-id", 
        sender="agent",
        content=labriot_response_text,
        validation_response=validation_explanation
    )

@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not retriever:
        return ChatResponse(response="Desculpe, o sistema de busca (RAG) não foi inicializado corretamente.")

    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    
    bot_response = rag_chain.invoke(request.user_question)
    return ChatResponse(response=bot_response)