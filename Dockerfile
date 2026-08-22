FROM python:3.11-slim

# Establecer directorio de trabajo
WORKDIR /app

# Instalar herramientas básicas del sistema operativo que algunas librerías requieren
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    curl \
    && rm -rf /var/lib/apt/lists/*

# COPIAR SOLO EL REQUIREMENTS PRIMERO (El secreto de la velocidad)
# Docker congelará esta capa. Si solo cambias código, Docker se salta esta descarga pesada.
COPY requirements.txt .

# Instalar PyTorch versión CPU explícitamente para evitar descargar 4GB de drivers NVIDIA
RUN pip install --no-cache-dir torch --index-url https://download.pytorch.org/whl/cpu

# Instalar el resto de las librerías
RUN pip install --no-cache-dir -r requirements.txt

# Copiar el resto de tu código fuente a la imagen
COPY . .

# Exponer el puerto 8000
EXPOSE 8000

# Comando para encender Uvicorn
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
