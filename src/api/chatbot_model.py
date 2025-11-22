from typing import List
from langchain_community.document_loaders import WebBaseLoader
from langchain_openai import ChatOpenAI
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.document_loaders import PyPDFLoader
from langchain_ollama import OllamaEmbeddings
from langchain_chroma import Chroma
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder, PromptTemplate
from langchain_core.output_parsers import StrOutputParser
from langchain_core.runnables import RunnablePassthrough, RunnableParallel
from langchain_core.messages import BaseMessage
import os
from datetime import datetime

file_paths = []
url_paths = (
    "https://youvisa.com.br", 
    "https://youvisa.com.br/vistos/estados-unidos",
    "https://youvisa.com.br/vistos/canada",
    "https://youvisa.com.br/vistos/mexico",
    "https://youvisa.com.br/cidadania-italiana",
    "https://youvisa.com.br/imigracao-estados-unidos",
    "https://blog.youvisa.com.br/"
    "https://blog.youvisa.com.br/posts/como-renovar-o-visto-americano",
    "https://blog.youvisa.com.br/posts/como-tirar-o-visto-americano-turismo",
    "https://blog.youvisa.com.br/posts/duvidas-frequentes-sobre-o-visto-americano",
    "https://blog.youvisa.com.br/posts/visto-negado-entenda",
    "https://blog.youvisa.com.br/posts/visto-canadense-turismo-passo-a-passo"
    )

OBJECTIVE = "vistos, imigração, serviços da YouVisa, requisitos de entrada em países, agendamento de consultas e informações sobre documentação"
WHATSAPP = "(11) 4200-2082"
qa_prompt_template = """
Você é o assistente virtual oficial da YouVisa.  
Seu papel é ajudar usuários com informações sobre vistos, imigração e serviços oferecidos pela YouVisa.

REGRAS GERAIS:
1. Você só pode responder perguntas relacionadas a:
   - Vistos e imigração.
   - Requisitos de entrada em países.
   - Serviços prestados pela YouVisa.
   - Informações gerais sobre a empresa (site, telefone, e-mail, como funciona, o que fazemos).
   - Orientações genéricas sobre documentação e procedimentos consulares.

2. Se a pergunta for **fora desse tema**, responda exatamente:
   "Desculpe, eu sou especializado apenas em vistos e imigração. Não posso ajudar com esse tema."

3. **Perguntas sobre informações pessoais ou específicas do cliente**, como:
   - "Como está meu processo?"
   - "Qual a situação do meu agendamento?"
   - "Vocês receberam meus documentos?"
   - "Podem verificar minha aplicação?"
   Devem ser respondidas **sempre** com:
   "Para verificar informações específicas do seu processo, por favor fale com nossos especialistas pelo WhatsApp: {whatsapp}"

4. Use sempre o contexto recuperado dos documentos.  
   - Se houver informações relevantes, utilize-as na resposta.  
   - Se não houver informações no contexto e você não souber, responda:  
     "Não consegui encontrar essa informação. Por favor, fale com nossos especialistas pelo WhatsApp: {whatsapp}"

5. Sempre responda em português.

6. Seja claro, educado e direto.

DADOS FIXOS:
- Hoje é {today}.
- Número do WhatsApp da YouVisa: {whatsapp}
- Tema permitido: {objective}

Pergunta: {input}
Contexto: {context}
"""

def model_openai(model_name = "gpt-4o-mini", temperature = 0):
    """
    Acessa o modelo do Chat GPT pela API.
    """
    llm = ChatOpenAI(model = model_name, temperature = temperature)
    return llm

def config_retriever(files: List[str] = file_paths,
                     urls: List[str] = url_paths,
                     emb_model_name: str = "bge-m3:latest"):
    docs = []
    if urls:
        loader = WebBaseLoader(web_paths= urls)
        docs.extend(loader.load())
    
    # Carregar documentos
    for file in files:
        if not os.path.exists(file):
            continue
        loader = PyPDFLoader(file)
        docs.extend(loader.load())
    
    # Divisão em pedaços de texto / split
    text_splitter = RecursiveCharacterTextSplitter(chunk_size = 1000, # Dividirá o texto em pedaços de 1000 caracteres
                                               chunk_overlap = 200,
                                               add_start_index = True) # Para o índice dos caracteres inicial seja preservado
    splits = text_splitter.split_documents(docs)
    
    # Embeddings
    ollama_embedding = OllamaEmbeddings(
        model=emb_model_name
    )
    
    # Armazenamento
    vectorstore = Chroma.from_documents(splits, ollama_embedding)
    
    # Configuração do retriever
    retriever = vectorstore.as_retriever(search_type = "mmr", # Maximum Marginal Relevance Retriever
                                         search_kwargs={"k": 3, "fetch_k": 4})
    
    return retriever

def config_rag_chain(retriever):
    llm = model_openai()
    
    context_q_system_prompt = "Given the following chat history and the follow-up question which might reference context in the chat history, formulate a standalone question which can be understood without the chat history. Do NOT answer the question, just reformulate it if needed and otherwise return it as is."
    
    context_q_prompt = ChatPromptTemplate([
        ("system", context_q_system_prompt),
        MessagesPlaceholder(variable_name="chat_history"),
        ("human", "Question: {input}")
    ])
    
    # 3. Chain para contextualização e reformular a pergunta
    rewrite_chain = context_q_prompt | llm | StrOutputParser()
    
    # 4. Pipeline de retrieval com LCEL
    # (input + histórico) -> pergunta reescrita -> retriever -> docs
    retrieval_chain = RunnableParallel({
        "input": RunnablePassthrough(),
        "rephrased_question": rewrite_chain
    }) | {
        "input": RunnablePassthrough(),
        "context": lambda x: retriever.invoke(x["rephrased_question"])
    }
    
    qa_prompt = PromptTemplate.from_template(qa_prompt_template, 
                                             partial_variables={
                                                "objective": OBJECTIVE,
                                                "whatsapp": WHATSAPP,
                                                "today": datetime.now().strftime('%d de %B de %Y')
                                             })
    
    # 6. Configurar LLM e Chain para perguntas e respostas (Q&A)
    qa_chain = qa_prompt | llm | StrOutputParser()
    
    # 7. RAG final combinado
    # Chain RAG que retorna com as fontes (contexto)
    rag_chain = (retrieval_chain
                 | RunnableParallel({
                    "answer": qa_chain,
                    "context": lambda x: x["context"]
                 }))
    
    return rag_chain

def model_response(user_query: str, chat_history: List[BaseMessage]):
    retriever = config_retriever()
    rag_chain = config_rag_chain(retriever)
    
    result = rag_chain.invoke({
        "input": user_query, 
        "chat_history": chat_history
    })
    return result['answer']