import streamlit as st
from langchain_core.messages import AIMessage, HumanMessage
import requests
from enums import MessageType

API_URL = "http://localhost:8000"

# Configurações do Streamlit
st.set_page_config(page_title="Seu assistente virtual YOUVISA 🤖", page_icon="🤖")
st.title("Seu assistente virtual YOUVISA 🤖")

def request_agent(user_query: str):
    history = []
    for message in st.session_state.chat_history:
        if isinstance(message, AIMessage):
            history.append({
                "type": MessageType.AI.value,
                "message": message.content
            })
        elif isinstance(message, HumanMessage):
            history.append({
                "type": MessageType.HUMAN.value,
                "message": message.content
            })
            
    payload = {
        "input": user_query,
        "chat_history": history
    }
    response = requests.post(f"{API_URL}/chatbot", json=payload)
    response.raise_for_status()
    
    data = response.json()
    
    return data["response"]

if "chat_history" not in st.session_state:
    st.session_state.chat_history = [AIMessage(content="Olá, sou o seu assistente virtual! Como posso ajudar você? :)")]

# Renderização do histórico de mensagens
for message in st.session_state.chat_history:
    if isinstance(message, AIMessage):
        with st.chat_message("ai"):
            st.write(message.content)
    elif isinstance(message, HumanMessage):
        with st.chat_message("human"):
            st.write(message.content)

# Input para o usuário escrever            
user_query = st.chat_input("Digite sua mensagem aqui...")

# Adiciona o input ao chat
if user_query is not None and len(user_query) != 0:
    st.session_state.chat_history.append(HumanMessage(content=user_query))
    
    with st.chat_message("human"):
        st.markdown(user_query)
    
    with st.chat_message("ai"):
        with st.spinner("Gerando resposta..."):
            resp = request_agent(user_query)
        st.write(resp)
    st.session_state.chat_history.append(AIMessage(content=resp))