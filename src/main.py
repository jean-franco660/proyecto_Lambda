import json
import boto3
import pandas as pd
import matplotlib.pyplot as plt
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

        # 📈 Histograma (columna numérica 1°)
        if resumen["columnas_numericas"]:
            col = resumen["columnas_numericas"][0]
            plt.figure()
            df[col].hist(bins=20)
            plt.title(f'Distribución de {col}')
            plt.xlabel(col)
            plt.ylabel('Frecuencia')

            img_buffer = io.BytesIO()
            plt.savefig(img_buffer, format='png')
            img_buffer.seek(0)

            key_png = key_input.replace('.csv', '.png')
            s3.upload_fileobj(img_buffer, bucket_output, f"reportes/{key_png}")
            print(f"✅ Imagen subida: reportes/{key_png}")

        # 📝 Guardar reporte JSON
        json_bytes = json.dumps(resumen, indent=2).encode('utf-8')
        json_buffer = io.BytesIO(json_bytes)
        key_json = key_input.replace('.csv', '.json')
        s3.upload_fileobj(json_buffer, bucket_output, f"reportes/{key_json}")
        print(f"✅ Reporte subido: reportes/{key_json}")

        return {"status": "ok", "archivo": key_input}

    except Exception as e:
        print(f"❌ Error: {str(e)}")
        raise
