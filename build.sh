#!/bin/bash
set -e

echo "🛠️ Construyendo paquete Lambda sin dependencias externas"

# Elimina ZIP anterior si existe
rm -f function.zip

# Crea carpeta de build temporal
mkdir -p build

# Solo copiar tu archivo main.py
cp src/main.py build/

# Comprimir en ZIP
cd build
zip -r ../function.zip .
cd ..

# Limpieza
rm -rf build

echo "✅ Paquete Lambda creado: function.zip"
