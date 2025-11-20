# Imagem base
FROM python:3.11-slim

# Evita buffer no log
ENV PYTHONUNBUFFERED=1

# Diretório da aplicação
WORKDIR /app

# Copia requirements
COPY requirements.txt .

# Instala dependências
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código
COPY . .

# Expõe a porta usada pelo Streamlit
EXPOSE 8501

# Comando para iniciar o Streamlit (importante: não usar 0.0.0.0)
CMD ["streamlit", "run", "app.py", "--server.port=8501", "--server.address=0.0.0.0"]
