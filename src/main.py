import boto3
import csv
import json
import os
import io
import time
import statistics

def lambda_handler(event, context):
    s3 = boto3.client("s3")
    dynamodb = boto3.resource("dynamodb")

    # 📥 Extraer datos del evento
    input_bucket = event["Records"][0]["s3"]["bucket"]["name"]
    file_key = event["Records"][0]["s3"]["object"]["key"]
    output_bucket = os.environ["OUTPUT_BUCKET_NAME"]
    table = dynamodb.Table("historial_reportes") # type: ignore

    print(f"Procesando {file_key} desde {input_bucket}")

    # 📄 Leer archivo CSV desde S3
    try:
        response = s3.get_object(Bucket=input_bucket, Key=file_key)
        contenido = response["Body"].read().decode("utf-8").splitlines()
        filas = list(csv.DictReader(contenido))
    except Exception as e:
        print(f"❌ Error al leer CSV: {e}")
        raise

    # 🧹 Limpiar datos
    datos_limpios = limpiar_datos(filas)
    columnas = list(datos_limpios[0].keys()) if datos_limpios else []
    total = len(datos_limpios)
    ventas = [float(r["SALES"]) for r in datos_limpios if r.get("SALES")]

    # 📊 Crear reporte JSON
    reporte_json = {
        "archivo": file_key,
        "filas": total,
        "columnas": columnas,
        "estadisticas": {
            "conteo": len(ventas),
            "min": min(ventas) if ventas else 0,
            "max": max(ventas) if ventas else 0,
            "promedio": statistics.mean(ventas) if ventas else 0
        }
    }

    json_key = f"reporte_{file_key.replace('.csv', '.json')}"
    csv_key = f"limpio_{file_key}"

    # 🚀 Subir JSON y CSV limpio
    try:
        s3.put_object(
            Bucket=output_bucket,
            Key=json_key,
            Body=json.dumps(reporte_json, indent=4).encode("utf-8"),
            ContentType="application/json"
        )

        buffer = io.StringIO()
        writer = csv.DictWriter(buffer, fieldnames=columnas)
        writer.writeheader()
        writer.writerows(datos_limpios)

        s3.put_object(
            Bucket=output_bucket,
            Key=csv_key,
            Body=buffer.getvalue().encode("utf-8"),
            ContentType="text/csv"
        )

        print(f"✅ Archivos subidos: {json_key}, {csv_key}")
    except Exception as e:
        print(f"❌ Error al subir archivos: {e}")
        raise

    # 🧾 Registrar en DynamoDB
    try:
        table.put_item(
            Item={
                "reporte_id": json_key,
                "archivo": file_key,
                "timestamp": int(time.time()),
                "filas": total,
                "columnas": columnas,
                "json_key": json_key,
                "csv_key": csv_key
            }
        )
        print(f"📦 Reporte registrado en DynamoDB")
    except Exception as e:
        print(f"❌ Error al guardar en DynamoDB: {e}")

    return {
        "statusCode": 200,
        "body": f"Procesado exitosamente: {json_key}"
    }

# 🔍 Limpieza básica
def limpiar_datos(rows):
    datos = []
    vistos = set()

    for row in rows:
        try:
            if not row.get("QUANTITYORDERED") or int(row["QUANTITYORDERED"]) == 0:
                continue
            if float(row.get("PRICEEACH", 0)) < 0:
                continue
            if row.get("STATUS") == "DLEIVERED":
                row["STATUS"] = "DELIVERED"
            elif not row.get("STATUS"):
                row["STATUS"] = "UNKNOWN"
            time.strptime(row["ORDERDATE"], "%Y-%m-%d")
            float(row["SALES"])
            clave = (row["ORDERNUMBER"], row["ORDERLINENUMBER"])
            if clave in vistos:
                continue
            vistos.add(clave)
            row["PRODUCTCODE"] = row["PRODUCTCODE"][:15]
            row["PRODUCTLINE"] = row["PRODUCTLINE"][:30]
            if not row["ORDERNUMBER"].isdigit() or not row["ORDERLINENUMBER"].isdigit():
                continue
            if not row["NUMERICCODE"].isdigit():
                continue
            row["COUNTRY"] = ''.join(c for c in row["COUNTRY"] if c.isalpha() or c.isspace())
            row["CITY"] = row.get("CITY") or "SIN CIUDAD"

            datos.append(row)
        except:
            continue

    return datos
