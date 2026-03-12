import os
import requests
from io import BytesIO
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

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

from challenge_agent import invoke_challenge_agent 
from validation_agent import invoke_validation_agent
# --- CONFIGURAÇÃO INICIAL E CARREGAMENTO DO MODELO ---

# Modelo de embedding que será usado
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


lista_de_documentos_pdf = [
    "Documentação Syna-2.pdf",
    "Documentação APS.pdf",
    "Documentação Alimentadores.pdf",
    "Documentação NEXA.pdf",
]
# -------------------------------------

documentos_totais = []
print("Iniciando o carregamento dos documentos locais...")

# Itera sobre a lista de arquivos que você definiu
for caminho_do_pdf in lista_de_documentos_pdf:
    try:
        # Verifica se o arquivo existe antes de tentar carregar
        if not os.path.exists(caminho_do_pdf):
            print(f"Erro: Arquivo não encontrado no caminho: {caminho_do_pdf}")
            print(f"Pulando o arquivo '{caminho_do_pdf}'...")
            continue # Pula para o próximo arquivo da lista
            
        loader = PyPDFLoader(caminho_do_pdf)
        paginas = loader.load()
        documentos_totais.extend(paginas)
        print(f"Documento '{caminho_do_pdf}' carregado com sucesso ({len(paginas)} páginas).")

    except Exception as e:
        print(f"Erro ao processar o PDF '{caminho_do_pdf}': {e}")
        print(f"Pulando o arquivo '{caminho_do_pdf}'...")

print(f"\nCarregamento concluído. Total de páginas de todos os documentos: {len(documentos_totais)}")

# Dividir os documentos em chunks e criar o Vector DB
vector_db = None
if documentos_totais:
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documentos_totais)
    
    print(f"Criando Vector DB com {len(chunks)} chunks de {len(lista_de_documentos_pdf)} documento(s)...")
    vector_db = FAISS.from_documents(chunks, embeddings)
    retriever = vector_db.as_retriever(search_kwargs={"k": 5})
    print("Vector DB criado com sucesso!")
else:
    print("Nenhum documento foi carregado. A API não pode iniciar o RAG.")
    retriever = None

# --- DEFINIÇÃO DA API COM FASTAPI ---

app = FastAPI()

# Configuração do CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:8080"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Modelos Pydantic
class ChatRequest(BaseModel):
    user_question: str

class ChatResponse(BaseModel):
    id: str
    sender: str
    content: str
    validation_response: str | None

# Prompt Template (o mesmo de antes, focado na documentação)
prompt_template = ChatPromptTemplate.from_template("""
    Você é um assistente especializado em responder perguntas sobre documentações  ".
    Sua missão é ajudar o usuário a entender como os projetos funcionam, quais são suas regras, linguagens, frameworks, limitações e base de conhecimento, com base no documento fornecido.

    Baseado no CONTEXTO abaixo, extraídos das documentações, responda à PERGUNTA do usuário
    de forma clara, objetiva e precisa.

    REGRAS:
    1.  **Foque no Contexto:** Sua resposta DEVE ser baseada estritamente nas informações
        contidas no contexto fornecido (a documentação).
    2.  **Seja um Guia de Referência:** Aja como um guia. Se o usuário perguntar "Qual o prompt da Syna?",
        você deve extrair e apresentar o prompt exato do contexto.
    3.  **Cite Fatos:** Responda com os fatos da documentação. Não invente regras ou
        funcionalidades que não estão escritas no documento.
    4.  **Se a Resposta Não Estiver no Contexto:** Se a informação não estiver clara
        no documento, informe ao usuário que a documentação fornecida não detalha
        aquele tópico específico.
    5.  **Mantenha o Foco:** Responda apenas à pergunta feita, sem divagar.

    DOCUMENTAÇÃO (CONTEXTO):
    {context}

    PERGUNTA DO USUÁRIO SOBRE A DOCUMENTAÇÃO:
    {question}

    RESPOSTA DO ASSISTENTE:
""")

@app.post("/chat", response_model=ChatResponse)
async def chat_endpoint(request: ChatRequest):
    # Passo 1: Obter a resposta do agente principal (LABRIOT)
    # (Estou supondo os nomes das funções, ajuste conforme seu código)
    labriot_response_text = invoke_challenge_agent(request.user_question)

    # Passo 2: Obter a validação do agente validador
    validation_explanation = invoke_validation_agent(
        question=request.user_question,
        response=labriot_response_text
    )

    # Passo 3: Retornar ambas as respostas para o frontend
    return ChatResponse(
        id="some-unique-id", # Gere um ID
        sender="agent",
        content=labriot_response_text,
        validation_response=validation_explanation
    )

# Endpoint da API
@app.post("/api/chat", response_model=ChatResponse)
async def chat(request: ChatRequest) -> ChatResponse:
    if not retriever:
        return ChatResponse(response="Desculpe, o sistema de busca (RAG) não foi inicializado corretamente pois nenhum documento foi carregado.")

    # Monta a chain de RAG
    rag_chain = (
        {"context": retriever, "question": RunnablePassthrough()}
        | prompt_template
        | llm
        | StrOutputParser()
    )
    
    # Invoca a chain e obtém a resposta
    bot_response = rag_chain.invoke(request.message)
    
    return ChatResponse(response=bot_response)

# Comando para rodar a API
if __name__ == "__main__":
    import uvicorn
    print("Iniciando a API em http://localhost:8000")
    uvicorn.run(app, host="0.0.0.0", port=8000)