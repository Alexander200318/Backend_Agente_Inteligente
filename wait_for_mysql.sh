#!/bin/bash

# Esperar a que MySQL esté listo
MYSQL_HOST=${MYSQL_HOST:-mysql}
MYSQL_PORT=${MYSQL_PORT:-3306}

echo "⏳ Esperando a que MySQL esté listo en $MYSQL_HOST:$MYSQL_PORT..."

max_attempts=30
attempt=0

# Usar nc (netcat) para verificar si el puerto está abierto
while [ $attempt -lt $max_attempts ]; do
    if nc -z "$MYSQL_HOST" "$MYSQL_PORT" 2>/dev/null; then
        echo "✅ MySQL está listo!"
        sleep 2
        break
    fi
    
    attempt=$((attempt + 1))
    echo "Intento $attempt/$max_attempts..."
    sleep 1
done

if [ $attempt -eq $max_attempts ]; then
    echo "❌ MySQL no está disponible después de $max_attempts intentos"
    exit 1
fi

echo "🚀 Iniciando aplicación..."
exec "$@"
