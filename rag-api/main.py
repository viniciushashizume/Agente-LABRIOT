import os
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# Importações do LangChain
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.embeddings import HuggingFaceEmbeddings 
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.runnables import RunnablePassthrough
from langchain_core.output_parsers import StrOutputParser

# Carregue sua chave de API a partir de um arquivo .env (recomendado localmente)
from dotenv import load_dotenv
load_dotenv()

from challenge_agent import invoke_challenge_agent 
from validation_agent import invoke_validation_agent

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

llm = ChatGoogleGenerativeAI(model="gemini-2.5-flash", temperature=0.3) 

# --- CONEXÃO COM MONGODB E INICIALIZAÇÃO DO VECTOR STORE ---

MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "rag_db"
COLLECTION_NAME = "documentos"
INDEX_NAME = "vector_index"

client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

# Apenas inicializa a conexão com o banco que já tem os dados (Sem Scraping/Leitura de PDFs)
vector_db = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX_NAME
)

# Habilitando o retriever do banco
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# --- DEFINIÇÃO DA API COM FASTAPI ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:8080",
        "http://localhost:5173",   # Porta padrão do Vite (React)
        "http://127.0.0.1:5173",   # Variação comum do Vite
        "http://localhost:3000"    # Caso esteja usando React scripts
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

if __name__ == "__main__":
    import uvicorn
    print("Iniciando a API em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)