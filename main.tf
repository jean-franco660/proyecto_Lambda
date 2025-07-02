# ✅ Empaquetar el código desde /src/
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/lambda_package.zip"
}

# ✅ Rol IAM ya existente en AWS (¡este es el cambio principal!)
data "aws_iam_role" "lambda_role" {
  name = "lambda_role_csv_to_reportes"  # Cambia si tu rol tiene otro nombre real
}

# ✅ Crear tabla DynamoDB para registrar reportes
resource "aws_dynamodb_table" "reportes" {
  name         = "reportes_csv"
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "report_id"

  attribute {
    name = "report_id"
    type = "S"
  }

  lifecycle {
    prevent_destroy = false
  }
}

# ✅ Función Lambda (Versión simplificada para depuración)
resource "aws_lambda_function" "process_csv" {
  function_name = "lambda_reportes_csv"
  role          = data.aws_iam_role.lambda_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.12"
  memory_size   = 512
  timeout       = 60

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      OUTPUT_BUCKET_NAME = var.output_bucket_name
      DYNAMODB_TABLE     = aws_dynamodb_table.reportes.name
    }
  }
}