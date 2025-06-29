import json
import boto3
import csv
import io
import os
import statistics

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    dynamodb = boto3.resource('dynamodb')

    # 📥 Datos del evento de S3
    bucket_input = event['Records'][0]['s3']['bucket']['name']
    key_input = event['Records'][0]['s3']['object']['key']

    bucket_output = os.environ['OUTPUT_BUCKET_NAME']
    dynamodb_table = os.environ['DYNAMODB_TABLE']

    try:
        # 📄 Leer CSV desde S3
        obj = s3.get_object(Bucket=bucket_input, Key=key_input)
        contenido = obj['Body'].read().decode('utf-8')
        reader = csv.DictReader(io.StringIO(contenido))

        filas = list(reader)
        columnas = reader.fieldnames

        resumen = {
            "archivo": key_input,
            "total_filas": len(filas),
            "columnas": columnas,
            "columnas_numericas": [],
            "estadisticas": {}
        }

        for col in columnas:  # type: ignore
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

        # 📝 Guardar reporte JSON en S3
        json_bytes = json.dumps(resumen, indent=2).encode('utf-8')
        json_buffer = io.BytesIO(json_bytes)
        key_json = key_input.replace('.csv', '.json')
        s3.upload_fileobj(json_buffer, bucket_output, f"reportes/{key_json}")
        print(f"✅ Reporte subido: reportes/{key_json}")

        # 🗃️ Guardar resumen en DynamoDB
        table = dynamodb.Table(dynamodb_table) # type: ignore

        # Clave primaria: nombre del archivo
        item = {
            "id": key_json,
            "total_filas": resumen["total_filas"],
            "columnas": resumen["columnas"],
            "columnas_numericas": resumen["columnas_numericas"],
            "estadisticas": resumen["estadisticas"]
        }

        table.put_item(Item=item)
        print(f"✅ Reporte insertado en DynamoDB: {key_json}")

        return {"status": "ok", "archivo": key_input}

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
