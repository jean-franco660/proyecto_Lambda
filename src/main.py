import boto3
import csv
import json
import os
import io
import time
import matplotlib.pyplot as plt
import statistics

def analizar_csv(content_lines):
    reader = csv.DictReader(content_lines)
    total = 0
    columnas = []
    valores = []

    for row in reader:
        total += 1
        if not columnas:
            columnas = list(row.keys())
        for col in columnas:
            try:
                valor = float(row[col])
                valores.append(valor)
                break  # usar solo primera columna numérica válida
            except:
                continue
    return columnas, total, valores

def calcular_estadisticas(valores):
    if not valores:
        return {}
    return {
        "conteo": len(valores),
        "min": min(valores),
        "max": max(valores),
        "promedio": statistics.mean(valores)
    }

def generar_reporte_json(nombre_archivo, columnas, total_filas, estadisticas):
    return {
        "archivo": nombre_archivo,
        "total_filas": total_filas,
        "columnas_detectadas": columnas,
        "estadisticas": estadisticas
    }

def generar_grafico(valores):
    plt.figure()
    plt.hist(valores, bins=10, color='skyblue')
    plt.title("Distribución de valores")
    plt.xlabel("Valor")
    plt.ylabel("Frecuencia")
    buf = io.BytesIO()
    plt.savefig(buf, format='png')
    buf.seek(0)
    return buf

def lambda_handler(event, context):
    s3 = boto3.client('s3')

    input_bucket = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    output_bucket = os.environ['OUTPUT_BUCKET_NAME']

    print(f"Procesando archivo: {file_key} desde bucket: {input_bucket}")

    try:
        response = s3.get_object(Bucket=input_bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        raise

    columnas, total_rows, valores_numericos = analizar_csv(content)
    estadisticas = calcular_estadisticas(valores_numericos)

    report_key = f"reporte_{file_key.replace('.csv', '.json')}"
    reporte = generar_reporte_json(file_key, columnas, total_rows, estadisticas)

    try:
        s3.put_object(
            Bucket=output_bucket,
            Key=report_key,
            Body=json.dumps(reporte, indent=4).encode('utf-8'),
            ContentType='application/json'
        )
        print(f"Reporte JSON subido a {output_bucket}/{report_key}")
    except Exception as e:
        print(f"Error al subir el reporte: {e}")
        raise

    if valores_numericos:
        try:
            grafico = generar_grafico(valores_numericos)
            graph_key = f"grafico_{file_key.replace('.csv', '.png')}"
            s3.put_object(
                Bucket=output_bucket,
                Key=graph_key,
                Body=grafico,
                ContentType='image/png'
            )
            print(f"Gráfico subido a {output_bucket}/{graph_key}")
        except Exception as e:
            print(f"Error al generar o subir gráfico: {e}")
            graph_key = "No disponible"
    else:
        print("No se encontraron columnas numéricas para graficar.")
        graph_key = "No disponible"

    # 🔄 Guardar historial en DynamoDB
    try:
        dynamodb = boto3.resource('dynamodb')
        table = dynamodb.Table('historial_reportes')
        table.put_item(
            Item={
                'reporte_id': report_key,
                'archivo': file_key,
                'timestamp': int(time.time()),
                'filas': total_rows,
                'columnas': columnas,
                'grafico': graph_key
            }
        )
        print(f"Historial guardado en DynamoDB para {report_key}")
    except Exception as e:
        print(f"Error al guardar historial en DynamoDB: {e}")

    return {
        'statusCode': 200,
        'body': f"Reporte generado: {report_key}, Gráfico: {graph_key}"
    }
