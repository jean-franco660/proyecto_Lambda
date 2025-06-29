#!/bin/bash
set -e

echo "🛠️ Construyendo paquete Lambda..."

# 1. Elimina el ZIP anterior
rm -f function.zip

# 2. Crea carpeta temporal para el build
mkdir -p build

# 3. Instala dependencias en build/
pip install -r requirements.txt -t build/

# 4. Copia el código fuente (main.py) a build/
cp main.py build/

# 5. Comprimir el contenido de build/ en function.zip
cd build
zip -r ../function.zip .
cd ..

# 6. Limpieza opcional
rm -rf build

echo "✅ Paquete Lambda creado: function.zip"
