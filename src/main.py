import boto3
import csv
import json
import os
import io
import time
import matplotlib.pyplot as plt
import statistics

def lambda_handler(event, context):
    s3 = boto3.client('s3')

    input_bucket = event['Records'][0]['s3']['bucket']['name']
    file_key = event['Records'][0]['s3']['object']['key']
    output_bucket = os.environ['OUTPUT_BUCKET_NAME']

    print(f"Procesando archivo: {file_key} desde bucket: {input_bucket}")

    # 🔽 Leer el archivo CSV desde S3
    try:
        response = s3.get_object(Bucket=input_bucket, Key=file_key)
        content = response['Body'].read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"Error al leer el archivo: {e}")
        raise

    # 🧹 Limpieza de datos
    try:
        reader = list(csv.DictReader(content))
        registros_limpios = limpiar_datos(reader)
        columnas = list(registros_limpios[0].keys()) if registros_limpios else []
        total_rows = len(registros_limpios)
        valores_numericos = [
            float(row["SALES"]) for row in registros_limpios if row.get("SALES")
        ]
        print(f"{total_rows} registros limpios procesados")
    except Exception as e:
        print(f"Error durante la limpieza de datos: {e}")
        raise

    # 📊 Calcular estadísticas
    estadisticas = calcular_estadisticas(valores_numericos)

    # 📝 Generar y subir reporte JSON
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

    # 📈 Generar y subir gráfico
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
        print("No se encontraron valores numéricos para graficar.")
        graph_key = "No disponible"

    # 📤 Subir CSV limpio
    try:
        cleaned_key = f"limpio_{file_key}"
        cleaned_csv = io.StringIO()
        writer = csv.DictWriter(cleaned_csv, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(registros_limpios)

        s3.put_object(
            Bucket=output_bucket,
            Key=cleaned_key,
            Body=cleaned_csv.getvalue().encode('utf-8'),
            ContentType='text/csv'
        )
        print(f"Archivo limpio subido a {output_bucket}/{cleaned_key}")
    except Exception as e:
        print(f"Error al subir archivo limpio: {e}")

    # 🧾 Registrar en DynamoDB
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

# 🔍 Reglas de limpieza
def limpiar_datos(rows):
    registros_limpios = []
    vistos = set()

    for row in rows:
        try:
            # 1. QUANTITYORDERED vacío o cero
            if not row["QUANTITYORDERED"] or int(row["QUANTITYORDERED"]) == 0:
                continue

            # 2. PRICEEACH negativo
            price = float(row["PRICEEACH"])
            if price < 0:
                continue

            # 3. STATUS mal escrito o nulo
            if row["STATUS"] == "DLEIVERED":
                row["STATUS"] = "DELIVERED"
            elif not row["STATUS"]:
                row["STATUS"] = "UNKNOWN"

            # 4. Fecha válida
            try:
                time.strptime(row["ORDERDATE"], "%Y-%m-%d")
            except:
                continue

            # 5. SALES debe ser numérico
            try:
                float(row["SALES"])
            except:
                continue

            # 6. Duplicados
            clave = (row["ORDERNUMBER"], row["ORDERLINENUMBER"])
            if clave in vistos:
                continue
            vistos.add(clave)

            # 7. PRODUCTCODE truncado
            row["PRODUCTCODE"] = row["PRODUCTCODE"][:15]

            # 8, 9, 17, 18: Validaciones numéricas
            if not row["ORDERNUMBER"].isdigit() or not row["ORDERLINENUMBER"].isdigit():
                continue

            # 13. PRODUCTLINE truncado
            row["PRODUCTLINE"] = row["PRODUCTLINE"][:30]

            # 14. NUMERICCODE debe ser numérico
            if not row["NUMERICCODE"].isdigit():
                continue

            # 19. Limpiar emojis de COUNTRY
            row["COUNTRY"] = ''.join(c for c in row["COUNTRY"] if c.isalpha() or c.isspace())

            # 20. CITY vacío
            if not row["CITY"]:
                row["CITY"] = "SIN CIUDAD"

            registros_limpios.append(row)
        except Exception as e:
            print(f"Error limpiando fila: {e}")
            continue

    return registros_limpios

# 📈 Estadísticas
def calcular_estadisticas(valores):
    if not valores:
        return {}
    return {
        "conteo": len(valores),
        "min": min(valores),
        "max": max(valores),
        "promedio": statistics.mean(valores)
    }

# 📝 Reporte JSON
def generar_reporte_json(nombre_archivo, columnas, total_filas, estadisticas):
    return {
        "archivo": nombre_archivo,
        "total_filas": total_filas,
        "columnas_detectadas": columnas,
        "estadisticas": estadisticas
    }

# 📊 Histograma
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