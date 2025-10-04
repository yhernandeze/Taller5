FROM python:3.10-slim

WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && \
    apt-get install -y curl && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Copiar requirements
COPY requirements.txt .

# Instalar dependencias de Python
RUN pip install --no-cache-dir -r requirements.txt

# Copiar aplicación
COPY app.py .

# Exponer puerto
EXPOSE 8503

# Comando para ejecutar Streamlit
CMD ["streamlit", "run", "app.py", "--server.port=8503", "--server.address=0.0.0.0"]
