FROM python:3.11-slim

# Evita prompts interativos e bufferização de logs
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

WORKDIR /app

# Instala dependências primeiro (camada de cache do Docker)
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copia todo o código do bot
COPY . .

# Porta que o HF Spaces espera
EXPOSE 7860

# Executa o bot
CMD ["python", "main.py"]
