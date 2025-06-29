terraform {
  required_providers {
    aws = {
      source = "hashicorp/aws"
    }
  }
}

# 📦 Empaquetar el código Lambda desde la carpeta `src/`
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/function.zip"
}

# 🔐 Usar un rol IAM existente con permisos adecuados
data "aws_iam_role" "lambda_existing_role" {
  name = "lambda_role_csv_to_reportes" 
}

# 🧾 Crear tabla DynamoDB para guardar metadatos de reportes
resource "aws_dynamodb_table" "reportes" {
  name         = "reportes_csv"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "reporte_id"

  attribute {
    name = "reporte_id"
    type = "S"
  }

  lifecycle {
    prevent_destroy = true
  }
}

# 🧠 Crear función Lambda
resource "aws_lambda_function" "my_lambda" {
  function_name = "lambda_reportes_csv"

  role    = data.aws_iam_role.lambda_existing_role.arn
  handler = "main.lambda_handler"
  runtime = "python3.11"

  filename         = "${path.module}/function.zip"
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      OUTPUT_BUCKET_NAME = var.output_bucket_name
      DYNAMODB_TABLE     = aws_dynamodb_table.reportes.name
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [filename, source_code_hash]
  }
}


# 🔔 Permitir que S3 invoque Lambda
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.input_bucket_name}"
}

# 🔄 Configurar notificación desde S3 para disparar Lambda
resource "aws_s3_bucket_notification" "s3_to_lambda" {
  bucket = var.input_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.my_lambda.arn
    events              = ["s3:ObjectCreated:*"]
    filter_prefix       = "archivos/"
    filter_suffix       = ".csv"
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}
