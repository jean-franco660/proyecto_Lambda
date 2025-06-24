import boto3
import csv
import json
import os

def lambda_handler(event, context):
    # Inicializar cliente S3
    s3 = boto3.client('s3')

    # Obtener información del archivo cargado
    input_bucket = event['Records'][0]['s3']['bucket']['name']
    file_key     = event['Records'][0]['s3']['object']['key']
    output_bucket = os.environ['OUTPUT_BUCKET_NAME']

    print(f"Procesando archivo: {file_key} del bucket: {input_bucket}")

    # Descargar el archivo CSV
    try:
        response = s3.get_object(Bucket=input_bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8').splitlines()
        reader = csv.DictReader(content)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        raise

    # Procesar contenido del CSV
    total_rows = 0
    columnas = []

    for row in reader:
        total_rows += 1
        if not columnas:
            columnas = list(row.keys())

    # Generar reporte
    reporte = {
        "archivo_original": file_key,
        "total_filas": total_rows,
        "columnas": columnas
    }

    # Nombre del archivo de salida
    report_key = f"reporte_{file_key.replace('.csv', '.json')}"

    # Subir el reporte al bucket de salida
    try:
        s3.put_object(
            Bucket=output_bucket,
            Key=report_key,
            Body=json.dumps(reporte, indent=4).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"Reporte subido a {output_bucket}/{report_key}")
    except Exception as e:
        print(f"Error al subir el reporte: {e}")
        raise

    return {
        'statusCode': 200,
        'body': f"Reporte generado: {report_key}"
    }
