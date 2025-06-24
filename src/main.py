import boto3
import csv
import json
import os
import matplotlib.pyplot as plt
import io

def lambda_handler(event, context):
    s3 = boto3.client('s3')

    input_bucket = event['Records'][0]['s3']['bucket']['name']
    file_key     = event['Records'][0]['s3']['object']['key']
    output_bucket = os.environ['OUTPUT_BUCKET_NAME']

    print(f"Procesando archivo: {file_key} del bucket: {input_bucket}")

    try:
        response = s3.get_object(Bucket=input_bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8').splitlines()
        reader = csv.DictReader(content)
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        raise

    total_rows = 0
    columnas = []
    valores_numericos = []

    for row in reader:
        total_rows += 1
        if not columnas:
            columnas = list(row.keys())
        # Intentar graficar la primera columna numérica
        for col in columnas:
            try:
                val = float(row[col])
                valores_numericos.append(val)
                break  # usar solo la primera columna válida
            except:
                continue

    reporte = {
        "archivo_original": file_key,
        "total_filas": total_rows,
        "columnas": columnas
    }

    report_key = f"reporte_{file_key.replace('.csv', '.json')}"
    graph_key = f"grafico_{file_key.replace('.csv', '.png')}"

    # Subir reporte JSON
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

    # Generar gráfico
    if valores_numericos:
        try:
            plt.figure()
            plt.hist(valores_numericos, bins=10, color='skyblue')
            plt.title('Distribución de valores')
            plt.xlabel('Valor')
            plt.ylabel('Frecuencia')

            # Guardar imagen en memoria
            buf = io.BytesIO()
            plt.savefig(buf, format='png')
            buf.seek(0)

            s3.put_object(
                Bucket=output_bucket,
                Key=graph_key,
                Body=buf,
                ContentType='image/png'
            )
            print(f"Gráfico subido a {output_bucket}/{graph_key}")
        except Exception as e:
            print(f"Error al generar gráfico: {e}")
    else:
        print("No se encontraron columnas numéricas para graficar.")

    return {
        'statusCode': 200,
        'body': f"Reporte generado: {report_key}, Gráfico: {graph_key if valores_numericos else 'No disponible'}"
    }
