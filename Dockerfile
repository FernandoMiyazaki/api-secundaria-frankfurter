# Define a imagem base
FROM python:3.11-slim

# Define o diretório de trabalho dentro do container
WORKDIR /app

# Copia os arquivos de requisitos para o diretório de trabalho
COPY requirements.txt .

# Instala as dependências do projeto
RUN pip install --no-cache-dir -r requirements.txt

# Copia o código-fonte para o diretório de trabalho
COPY . .

# Informa ao Docker que o container escutará na porta 5002
EXPOSE 5002

# Define o comando de execução da API
CMD ["python", "run.py"]