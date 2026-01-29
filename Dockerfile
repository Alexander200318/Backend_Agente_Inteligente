FROM python:3.11

WORKDIR /app

COPY requirements.txt .

RUN pip install --upgrade pip
RUN pip install --no-cache-dir -r requirements.txt

# Instalar herramientas para esperar a MySQL
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

COPY . .

# Dar permisos al script de entrada
COPY wait_for_mysql.sh /app/wait_for_mysql.sh
RUN chmod +x /app/wait_for_mysql.sh

EXPOSE 8000

ENTRYPOINT ["/app/wait_for_mysql.sh"]
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]