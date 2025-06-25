provider "aws" {
  region     = var.aws_region
}

variable "env" {}
variable "input_bucket_name" {}
variable "output_bucket_name" {}

# 🧩 Empaquetar Lambda automáticamente
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/../function.zip"
}

# 🎯 Crear el rol de ejecución para Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_exec_role_cloud_2025"

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

# 🔐 Permisos: logs + acceso a ambos buckets
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_s3_policy"
  role = aws_iam_role.lambda_exec_role.id

  policy = jsonencode({
    Version = "2012-10-17",
    Statement = [
      {
        Effect = "Allow",
        Action = [
          "logs:CreateLogGroup",
          "logs:CreateLogStream",
          "logs:PutLogEvents"
        ],
        Resource = "*"
      },
      {
        Effect = "Allow",
        Action = ["s3:GetObject"],
        Resource = "${aws_s3_bucket.csv_input_bucket.arn}/*"
      },
      {
        Effect = "Allow",
        Action = ["s3:PutObject"],
        Resource = "${aws_s3_bucket.report_output_bucket.arn}/*"
      },
      {
        Effect = "Allow",
        Action = ["dynamodb:GetItem", "dynamodb:PutItem", "dynamodb:Scan"],
        Resource = aws_dynamodb_table.reportes.arn
      }
    ]
  })

  depends_on = [aws_dynamodb_table.reportes]
}


# 🧠 Función Lambda
resource "aws_lambda_function" "my_lambda" {
  function_name = "proyecto_lambda_reportes"
  
  lifecycle {
    prevent_destroy = true
    ignore_changes  = [filename, source_code_hash]
  }
  description   = "Procesa CSV y genera reporte JSON"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.13"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      OUTPUT_BUCKET_NAME = aws_s3_bucket.report_output_bucket.bucket
    }
  }
}

# 🔔 Permitir invocación desde S3
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = aws_s3_bucket.csv_input_bucket.arn
}

# 🔗 Configurar trigger de S3 → Lambda
resource "aws_s3_bucket_notification" "bucket_notification" {
  bucket = aws_s3_bucket.csv_input_bucket.id

  lambda_function {
    lambda_function_arn = aws_lambda_function.my_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [
    aws_lambda_function.my_lambda,
    aws_s3_bucket.csv_input_bucket,
    aws_lambda_permission.allow_s3_invoke
  ]
}

resource "aws_dynamodb_table" "reportes" {
  name           = "historial_reportes"

  lifecycle {
    prevent_destroy = true
    ignore_changes  = []
  }
  
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = "reporte_id"

  attribute {
    name = "reporte_id"
    type = "S"
  }
}
