import os
import requests
from bs4 import BeautifulSoup
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
from pymongo import MongoClient

# Importações do LangChain
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.embeddings import HuggingFaceEmbeddings 
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain.text_splitter import RecursiveCharacterTextSplitter
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain.prompts import ChatPromptTemplate
from langchain.schema.runnable import RunnablePassthrough
from langchain.schema.output_parser import StrOutputParser

# Carregue sua chave de API a partir de um arquivo .env (recomendado)
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

vector_db = MongoDBAtlasVectorSearch(
    collection=collection,
    embedding=embeddings,
    index_name=INDEX_NAME
)
#collection.delete_many({})
# Verifica se o banco já foi populado anteriormente
if collection.count_documents({}) == 0:
    print("Coleção MongoDB vazia. Iniciando a leitura dos documentos...")
    documentos_totais = []

    # 1. Carregar Documentos Locais (PDFs)
    print("\n--- Carregando PDFs ---")
    lista_de_documentos_pdf = [
        "Documentação Syna-2.pdf",
        "Documentação APS.pdf",
        "Documentação Alimentadores.pdf",
        "Documentação NEXA.pdf",
    ]
    
    for caminho_do_pdf in lista_de_documentos_pdf:
        try:
            if not os.path.exists(caminho_do_pdf):
                print(f"Aviso: Arquivo não encontrado: {caminho_do_pdf}")
                continue
                
            loader = PyPDFLoader(caminho_do_pdf)
            paginas = loader.load()
            documentos_totais.extend(paginas)
            print(f"Documento '{caminho_do_pdf}' carregado com sucesso ({len(paginas)} páginas).")
        except Exception as e:
            print(f"Erro ao processar o PDF '{caminho_do_pdf}': {e}")

    # 2. Carregar Documentação Web (C++ e JavaScript)
    print("\n--- Carregando Documentação Web (C++ e JS) ---")
    
    urls_documentacao = [
        "https://developer.mozilla.org/pt-BR/docs/Web/JavaScript/Guide", 
        "https://pt.cppreference.com/w/cpp/language",
        "https://docs.python.org/3/tutorial/index.html"
    ]
    
    def extrair_texto_limpo(html_content):
        soup = BeautifulSoup(html_content, "html.parser")
        for script in soup(["script", "style", "nav", "footer", "header"]):
            script.extract()
        return soup.get_text(separator=" ", strip=True)

    # ---> CONTROLE DE INSERÇÃO WEB <---
    # Mude para True futuramente quando quiser processar os links e jogar no MongoDB
    INSERIR_WEB_NO_BANCO = True

    if INSERIR_WEB_NO_BANCO:
        for url in urls_documentacao:
            print(f"Iniciando extração de: {url}")
            try:
                loader = RecursiveUrlLoader(
                    url=url,
                    max_depth=2,
                    extractor=extrair_texto_limpo,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
                    }
                )
                docs_web = loader.load()
                documentos_totais.extend(docs_web)
                print(f"Web Scraping concluído para {url}. {len(docs_web)} páginas extraídas.")
            except Exception as e:
                print(f"Erro ao realizar web scraping da URL {url}: {e}")
    else:
        print("Web Scraping mantido no código, mas DESATIVADO para inserção no BD por agora (INSERIR_WEB_NO_BANCO = False).")

    # 3. Processar e Inserir no Banco Vetorial
    if documentos_totais:
        print(f"\nTotal combinado: {len(documentos_totais)} páginas/documentos.")
        text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
        chunks = text_splitter.split_documents(documentos_totais)
        
        print(f"Criando Vector DB com {len(chunks)} chunks de texto e enviando para o MongoDB...")
        MongoDBAtlasVectorSearch.from_documents(
            documents=chunks,
            embedding=embeddings,
            collection=collection,
            index_name=INDEX_NAME
        )
        print("Vector DB criado e salvo com sucesso no MongoDB Atlas!")
    else:
        print("Nenhum documento (PDF ou Web) foi carregado.")

else:
    print(f"Documentos já encontrados no MongoDB Atlas ({collection.count_documents({})} chunks). Pulando a leitura e inserção.")

# Habilitando o retriever do banco
retriever = vector_db.as_retriever(search_kwargs={"k": 5})

# --- DEFINIÇÃO DA API COM FASTAPI ---

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"], 
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