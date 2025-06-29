#!/bin/bash
set -e

echo "🛠️ Construyendo paquete Lambda desde ./src"

# Elimina ZIP anterior si existe
rm -f function.zip

# Crea carpeta de build temporal
mkdir -p build

# Instala dependencias en la carpeta build/
pip install -r src/requirements.txt -t build/

# Copia tu código fuente (main.py) a build/
cp src/main.py build/

# Comprimir todo en function.zip
cd build
zip -r ../function.zip .
cd ..

# Limpieza
rm -rf build

echo "✅ Paquete Lambda creado: function.zip"
