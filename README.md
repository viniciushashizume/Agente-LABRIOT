# Agente LABRIOT: Aplicação de Chat RAG 

Este repositório contém um aplicativo de bate-papo completo projetado para responder a perguntas sobre documentos específicos. Ele apresenta um frontend React/Vite e um backend Python/FastAPI que utiliza Geração Aumentada por Recuperação (RAG) com o modelo Gemini do Google.


O backend API indexa documentos PDF locais e os utiliza como uma 
base de conhecimento para fornecer respostas contextuais a consultas de 
usuários e gerar desafios baseados em áreas de aprendizado. 

 ## Tecnologia Utilizada 

 ### Frontend 
 * **Framework:** [React](https://react.dev/) 
 * **Build Tool:** [Vite](https://vitejs.dev/) 
 * **Language:** [TypeScript](https://www.typescriptlang.org/) 
 * **UI:** [shadcn/ui](https://ui.shadcn.com/) 
 * **Styling:** [Tailwind CSS](https://tailwindcss.com/) 
 * **Routing:** [React Router](https://reactrouter.com/) 

 ### Backend (API RAG) 
 * **Framework:** [FastAPI](https://fastapi.tiangolo.com/) 
 * **Server:** [Uvicorn](https://www.uvicorn.org/) 
 * **Orchestration:** [LangChain](https://www.langchain.com/) 

 * **LLM:** [Google Gemini (via 
`langchain-google-genai`)](https://python.langchain.com/docs/integrations/chat/google_generative_ai)
 
 * **Embeddings:** [Sentence-Transformers (`all-MiniLM-L6-v2`)](https://huggingface.co/sentence-transformers/all-MiniLM-L6-v2) 
 * **Vector Store:** [FAISS (faiss-cpu)](https://faiss.ai/) 
 * **Document Loading:** [PyPDFLoader](https://python.langchain.com/docs/integrations/document_loaders/pdf) 

 ## Pré-requisitos 

 Antes de começar, certifique-se de ter o seguinte instalado: 
 * [Node.js](https://nodejs.org/) (v18 ou posterior recomendado) & npm 
 * [Python](https://www.python.org/) (v3.9 ou posterior recomendado) & pip 
 * Uma **Chave de API do Google** para o modelo Gemini. Você pode obter uma em [Google AI Studio](https://aistudio.google.com/app/apikey). 

 ## Como Executar 


 Este projeto consiste em duas partes: a **API de Backend** e a 
**Aplicação Frontend**. Você precisará executá-las em dois terminais 
separados. 

 ### 1. Configuração do Backend (API RAG) 

 Primeiro, configure e execute o backend Python. 

 1.  **Navegue até o diretório da API:**
 2.  ```sh 
     cd rag-api 
     ``` 

 3.  **Crie um ambiente virtual** (recomendado): 
     ```sh 
     python -m venv venv 
     source venv/bin/activate  # No Windows, use: venv\Scripts\activate 
     ``` 

 4.  **Instale as dependências do Python:**
 5.  ```sh 
     pip install -r requirements.txt 
     ``` 

 6.  **Adicione seus documentos:**     A API está configurada para carregar PDFs específicos. Certifique-se de que os seguintes arquivos estejam presentes no diretório `rag-api/`: 
     * `Documentação Syna.pdf` 
     * `Python do ZERO à Programação Orientada a Objetos (Fernando Belomé Feltrin).pdf` 

 7.  **Crie um arquivo de ambiente:**     Crie um arquivo chamado `.env` no diretório `rag-api/`. Você precisará adicionar sua chave de API do Google aqui. 
     ``` 
     # rag-api/.env 
     GOOGLE_API_KEY="SUA_CHAVE_API_GOOGLE_AQUI" 
     ``` 
     *Nota: A aplicação usa `dotenv` para carregar esta chave.* 6.  **Execute o servidor da API:**
     ```sh 
     uvicorn main:app --reload --port 8000 
     ``` 
     A API será iniciada, carregará os documentos PDF, criará o armazenamento vetorial e estará disponível em `http://localhost:8000`. 

     Para o agente de criação de desafios, execute: 
     ```sh
     uvicorn challenge_agent:app --reload --port 8001 
     ``` 
     Para o agente de validação de respostas, execute: 
     ```sh 
     uvicorn validation_agent:app --reload --port 8002 
     ``` 

 ### 2. Configuração do Frontend 

 Em um **novo terminal**, configure e execute o frontend React. 

 1.  **Navegue até o diretório raiz do projeto** (se você estiver em `rag-api`, volte): 
     ```sh 
     cd .. 
     ``` 

 2.  **Instale as dependências do Node.js:**
 3.  ```sh 
     npm i 
     ``` 

 4.  **Crie um arquivo de ambiente:**     Crie um arquivo chamado `.env` no diretório raiz. Isso informa ao frontend onde encontrar a API. 
     ``` 
     # /.env 
     VITE_API_URL=http://localhost:8000 
     ``` 

 5.  **Execute o servidor de desenvolvimento:**     ```sh 
     npm run dev 
     ``` 
     A aplicação React será iniciada e estará acessível no seu navegador (geralmente em `http://localhost:8080`). 

 Agora você pode interagir com a interface de chat, que enviará requisições para a sua API RAG local. 

 Este projeto ainda está em desenvolvimento.
