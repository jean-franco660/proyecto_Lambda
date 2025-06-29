import json
import boto3
import pandas as pd
import io
import os

def lambda_handler(event, context):
    s3 = boto3.client('s3')
    
    # 📥 Datos del evento de S3
    bucket_input = event['Records'][0]['s3']['bucket']['name']
    key_input = event['Records'][0]['s3']['object']['key']
    
    bucket_output = os.environ['OUTPUT_BUCKET_NAME']
    
    try:
        # 📄 Leer CSV desde S3
        obj = s3.get_object(Bucket=bucket_input, Key=key_input)
        df = pd.read_csv(obj['Body'])
        
        # 📊 Generar resumen
        resumen = {
            "archivo": key_input,
            "total_filas": len(df),
            "columnas": list(df.columns),
            "columnas_numericas": [],
            "estadisticas": {}
        }

        for col in df.select_dtypes(include='number').columns:
            resumen["columnas_numericas"].append(col)
            resumen["estadisticas"][col] = {
                "media": df[col].mean(),
                "desviacion_estandar": df[col].std(),
                "nulos": int(df[col].isnull().sum())
            }

        # 📝 Guardar reporte JSON en S3
        json_bytes = json.dumps(resumen, indent=2).encode('utf-8')
        json_buffer = io.BytesIO(json_bytes)
        key_json = key_input.replace('.csv', '.json')
        s3.upload_fileobj(json_buffer, bucket_output, f"reportes/{key_json}")
        print(f"✅ Reporte subido: reportes/{key_json}")

        return {"status": "ok", "archivo": key_input}

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
