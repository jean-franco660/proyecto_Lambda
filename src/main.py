import boto3
import os
import json
import csv
import io
import time

# Inicializar cliente S3 y DynamoDB
s3_client = boto3.client('s3')
dynamodb = boto3.resource('dynamodb')

def lambda_handler(event, context):
    # 🔍 Extraer información del evento S3
    input_bucket = event['Records'][0]['s3']['bucket']['name']
    csv_key = event['Records'][0]['s3']['object']['key']
    output_bucket = os.environ['REPORTS_BUCKET']
    table_name = os.environ.get('DYNAMODB_TABLE', 'historial_reportes')
    table = dynamodb.Table(table_name)  # type: ignore

    print(f"📥 Procesando archivo {csv_key} desde {input_bucket}")

    # 📄 Leer CSV desde S3
    try:
        response = s3_client.get_object(Bucket=input_bucket, Key=csv_key)
        csv_lines = response['Body'].read().decode('utf-8').splitlines()
    except Exception as e:
        print(f"❌ Error al leer el archivo CSV: {e}")
        raise

    # 🧹 Procesar contenido
    data = process_csv(csv_lines)
    columnas = list(data[0].keys()) if data else []
    filas_totales = len(data)

    # 📊 Crear reportes
    json_report = generate_json_report(data)
    html_report = generate_html_report(data)

    # 📁 Construir claves para los archivos
    base_name = os.path.splitext(os.path.basename(csv_key))[0]
    json_key = f"{base_name}_report.json"
    html_key = f"{base_name}_report.html"

    try:
        # 📤 Subir JSON
        s3_client.put_object(
            Bucket=output_bucket,
            Key=json_key,
            Body=json.dumps(json_report, indent=4).encode("utf-8"),
            ContentType="application/json"
        )

        # 📤 Subir HTML
        s3_client.put_object(
            Bucket=output_bucket,
            Key=html_key,
            Body=html_report.encode("utf-8"),
            ContentType="text/html"
        )

        print(f"✅ Reportes subidos: {json_key}, {html_key}")
    except Exception as e:
        print(f"❌ Error al subir los reportes: {e}")
        raise

    # 🧾 Registrar en DynamoDB
    try:
        table.put_item(
            Item={
                "reporte_id": json_key,
                "archivo_origen": csv_key,
                "timestamp": int(time.time()),
                "filas": filas_totales,
                "columnas": columnas,
                "json_report": json_key,
                "html_report": html_key
            }
        )
        print("📦 Registro guardado en DynamoDB")
    except Exception as e:
        print(f"❌ Error al guardar en DynamoDB: {e}")

    return {
        "statusCode": 200,
        "body": f"Reportes generados para {csv_key}"
    }

# 🧹 Limpieza básica del CSV
def process_csv(csv_lines):
    reader = csv.DictReader(csv_lines)
    return list(reader)

# 📊 Reporte JSON simple
def generate_json_report(data):
    if not data:
        return {"mensaje": "Sin datos"}
    
    ventas = [float(r["SALES"]) for r in data if r.get("SALES") and is_number(r["SALES"])]
    return {
        "filas": len(data),
        "columnas": list(data[0].keys()),
        "ventas": {
            "conteo": len(ventas),
            "min": min(ventas) if ventas else 0,
            "max": max(ventas) if ventas else 0,
            "promedio": sum(ventas)/len(ventas) if ventas else 0
        }
    }

# 🖼️ Reporte HTML simple
def generate_html_report(data):
    html = "<html><body><h2>Vista previa del CSV</h2><table border='1'>"
    if data:
        html += "<tr>" + "".join(f"<th>{k}</th>" for k in data[0].keys()) + "</tr>"
        for row in data[:5]:
            html += "<tr>" + "".join(f"<td>{v}</td>" for v in row.values()) + "</tr>"
    html += "</table></body></html>"
    return html

# 🔢 Validación auxiliar
def is_number(value):
    try:
        float(value)
        return True
    except:
        return False
