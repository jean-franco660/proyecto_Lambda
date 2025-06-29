import json
import boto3
import csv
import io
import os
import statistics
import uuid
from datetime import datetime

# Clientes AWS
s3 = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

# Variables de entorno
OUTPUT_BUCKET = os.environ['OUTPUT_BUCKET_NAME']
DYNAMODB_TABLE = os.environ['DYNAMODB_TABLE']

def lambda_handler(event, context):
    # 📥 Datos del archivo CSV subido a S3
    bucket_input = event['Records'][0]['s3']['bucket']['name']
    key_input = event['Records'][0]['s3']['object']['key']
    filename = key_input.split('/')[-1]

    try:
        # 📄 Leer contenido del CSV
        obj = s3.get_object(Bucket=bucket_input, Key=key_input)
        body = obj['Body'].read()

        try:
            contenido = body.decode('utf-8')
        except UnicodeDecodeError:
            print("⚠️ Error al decodificar con UTF-8. Usando latin-1.")
            contenido = body.decode('latin-1')

        reader = csv.DictReader(io.StringIO(contenido))
        filas = list(reader)
        columnas = reader.fieldnames or []

        # 📊 Generar resumen estadístico
        resumen = {
            "archivo": key_input,
            "total_filas": len(filas),
            "columnas": columnas,
            "columnas_numericas": [],
            "estadisticas": {}
        }

        for col in columnas:
            try:
                valores = [float(f[col]) for f in filas if f[col].strip() != ""]
                if valores:
                    resumen["columnas_numericas"].append(col)
                    resumen["estadisticas"][col] = {
                        "media": statistics.mean(valores),
                        "desviacion_estandar": statistics.stdev(valores) if len(valores) > 1 else 0.0,
                        "nulos": sum(1 for f in filas if f[col].strip() == "")
                    }
            except ValueError:
                continue

        # 📝 Guardar reporte JSON en bucket de salida
        key_output = f"reportes/{filename.replace('.csv', '.json')}"
        json_bytes = json.dumps(resumen, indent=2).encode('utf-8')
        json_buffer = io.BytesIO(json_bytes)

        s3.upload_fileobj(json_buffer, OUTPUT_BUCKET, key_output)
        print(f"✅ Reporte subido: {key_output}")

        # 🧾 Registrar en DynamoDB
        tabla = dynamodb.Table(DYNAMODB_TABLE) # type: ignore
        report_id = str(uuid.uuid4())
        timestamp = datetime.utcnow().isoformat()

        tabla.put_item(Item={
            "report_id": report_id,
            "filename": filename,
            "bucket": bucket_input,
            "s3_key": key_input,
            "output_key": key_output,
            "timestamp": timestamp,
            "total_filas": len(filas),
            "columnas_numericas": resumen["columnas_numericas"]
        })

        return {
            "status": "ok",
            "archivo": key_input,
            "reporte": key_output,
            "report_id": report_id
        }

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
