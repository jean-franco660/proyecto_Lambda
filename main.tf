provider "aws" {
  region = var.aws_region
}

# 🧩 Empaquetar Lambda desde la raíz del submódulo
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/.."               # carpeta raíz del proyecto_lambda
  output_path = "${path.module}/../function.zip"
}

# Rol de ejecución para Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role_jf_2025"

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Effect = "Allow",
      Sid    = ""
    }]
  })
}

# Adjuntar permisos de logs
resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# Función Lambda principal
resource "aws_lambda_function" "my_lambda" {
  function_name = "proyecto_lambda_reportes"
  description   = "Función Lambda para procesar CSV desde S3"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "main.lambda_handler"               # Asegúrate que coincida con tu archivo
  runtime       = "python3.13"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      ENV = "dev"
    }
  }
}
