import json
import boto3
import pandas as pd
import io
import matplotlib.pyplot as plt
import base64
import uuid

s3 = boto3.client('s3')

def generate_base64_plot(fig):
    buffer = io.BytesIO()
    fig.savefig(buffer, format='png')
    buffer.seek(0)
    img_b64 = base64.b64encode(buffer.read()).decode('utf-8')
    plt.close(fig)
    return img_b64

def lambda_handler(event, context):
    try:
        # Leer evento del archivo CSV subido
        bucket_name = event['Records'][0]['s3']['bucket']['name']
        key = event['Records'][0]['s3']['object']['key']

        # Leer CSV desde S3
        response = s3.get_object(Bucket=bucket_name, Key=key)
        content = response['Body'].read().decode('utf-8')
        df = pd.read_csv(io.StringIO(content))

        # Procesamiento simple
        df.dropna(subset=['QUANTITYORDERED', 'PRICEEACH', 'STATUS'], inplace=True)
        df['TOTAL'] = df['QUANTITYORDERED'] * df['PRICEEACH']

        # Estadísticas resumen
        resumen = {
            "total_ventas": float(df['TOTAL'].sum()),
            "ventas_por_estado": df.groupby('STATUS')['TOTAL'].sum().round(2).to_dict()
        }

        # Gráfico de barras por estado
        fig, ax = plt.subplots()
        df.groupby('STATUS')['TOTAL'].sum().plot(kind='bar', ax=ax)
        ax.set_title("Ventas por Estado")
        img_base64 = generate_base64_plot(fig)

        # Armar reporte final
        reporte = {
            "id": str(uuid.uuid4()),
            "archivo_fuente": key,
            "resumen": resumen,
            "grafico_base64": img_base64
        }

        # Guardar reporte en S3
        report_key = f"reports/{key.replace('.csv', '')}_report.json"
        s3.put_object(
            Bucket=bucket_name,
            Key=report_key,
            Body=json.dumps(reporte),
            ContentType='application/json'
        )

        return {
            "statusCode": 200,
            "body": f"Reporte generado en: {report_key}"
        }

    except Exception as e:
        return {
            "statusCode": 500,
            "body": str(e)
        }
