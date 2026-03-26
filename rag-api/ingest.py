import os
from bs4 import BeautifulSoup
from pymongo import MongoClient
import time
# Importações do LangChain
from langchain_community.vectorstores import MongoDBAtlasVectorSearch
from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders.recursive_url_loader import RecursiveUrlLoader
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_google_genai import GoogleGenerativeAIEmbeddings

from dotenv import load_dotenv
load_dotenv()

# --- CONFIGURAÇÃO INICIAL E CARREGAMENTO DO MODELO ---
# Usando a API do Google para Embeddings em vez do modelo local pesado.
# Isso vai gerar vetores de 768 dimensões.
embeddings = GoogleGenerativeAIEmbeddings(model="models/gemini-embedding-001")

# --- CONEXÃO COM MONGODB ---
MONGO_URI = os.getenv("MONGO_URI")
DB_NAME = "rag_db"
COLLECTION_NAME = "documentos"
INDEX_NAME = "vector_index"

client = MongoClient(MONGO_URI)
collection = client[DB_NAME][COLLECTION_NAME]

print("--- INICIANDO INGESTÃO DE DADOS ---")

# ATENÇÃO CRÍTICA: Como trocamos o modelo de embedding (de 384 para 768 dimensões),
# precisamos APAGAR os documentos antigos do banco para evitar conflitos na busca.
print("Limpando documentos antigos do banco de dados (Necessário devido à mudança de modelo)...")
collection.delete_many({})
print("Banco de dados limpo com sucesso!")

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
print("\n--- Carregando Documentação Web ---")

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
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"
                }
            )
            docs_web = loader.load()
            documentos_totais.extend(docs_web)
            print(f"Web Scraping concluído para {url}. {len(docs_web)} páginas extraídas.")
        except Exception as e:
            print(f"Erro ao realizar web scraping da URL {url}: {e}")
else:
    print("Web Scraping mantido no código, mas DESATIVADO (INSERIR_WEB_NO_BANCO = False).")

# 3. Processar e Inserir no Banco Vetorial
if documentos_totais:
    print(f"\nTotal combinado: {len(documentos_totais)} páginas/documentos.")
    text_splitter = RecursiveCharacterTextSplitter(chunk_size=1000, chunk_overlap=150)
    chunks = text_splitter.split_documents(documentos_totais)
    
    print(f"Dividido em {len(chunks)} chunks de texto.")
    print("Gerando Embeddings em lotes via API do Google...")
    
    # 1. Cria a conexão com o banco vetorial vazia
    from langchain_community.vectorstores import MongoDBAtlasVectorSearch
    vector_store = MongoDBAtlasVectorSearch(
        collection=collection,
        embedding=embeddings,
        index_name=INDEX_NAME
    )
    
    # 2. Divide em lotes de 200 blocos e envia com pausa
    tamanho_lote = 200
    for i in range(0, len(chunks), tamanho_lote):
        lote = chunks[i : i + tamanho_lote]
        print(f"Enviando lote {i} até {i + len(lote)} (de {len(chunks)})...")
        vector_store.add_documents(lote)
        
        # Pausa de 20 segundos para não irritar o Google
        print("Pausa de 20 segundos para respeitar o limite gratuito...")
        time.sleep(20)

    print("Vector DB populado e salvo com sucesso no MongoDB Atlas!")