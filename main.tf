provider "aws" {
  region = var.aws_region
}

# 🧩 Empaquetar el código Python
data "archive_file" "lambda_zip" {
  type        = "zip"
  source_dir  = "${path.module}/src"
  output_path = "${path.module}/function.zip"
}

# 🔐 Rol de ejecución para Lambda
resource "aws_iam_role" "lambda_exec_role" {
  name = "lambda_role_cloud"

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

# 📜 Políticas para permitir acceso a S3 y DynamoDB
resource "aws_iam_role_policy" "lambda_policy" {
  name = "lambda_s3_dynamodb_policy"
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
        Resource = "arn:aws:s3:::${var.input_bucket_name}/*"
      },
      {
        Effect = "Allow",
        Action = ["s3:PutObject"],
        Resource = "arn:aws:s3:::${var.output_bucket_name}/*"
      },
      {
        Effect = "Allow",
        Action = [
          "dynamodb:PutItem"
        ],
        Resource = aws_dynamodb_table.reportes.arn
      }
    ]
  })

  depends_on = [aws_dynamodb_table.reportes]
}


# 🧠 Función Lambda
resource "aws_lambda_function" "my_lambda" {
  function_name = "lambda_reportes"

  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "main.lambda_handler"
  runtime       = "python3.11"

  filename         = data.archive_file.lambda_zip.output_path
  source_code_hash = data.archive_file.lambda_zip.output_base64sha256

  environment {
    variables = {
      OUTPUT_BUCKET_NAME = var.output_bucket_name
    }
  }

  lifecycle {
    prevent_destroy = true
    ignore_changes  = [filename, source_code_hash]
  }
}

# 🔔 Permiso para invocación desde S3
resource "aws_lambda_permission" "allow_s3_invoke" {
  statement_id  = "AllowExecutionFromS3"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.my_lambda.function_name
  principal     = "s3.amazonaws.com"
  source_arn    = "arn:aws:s3:::${var.input_bucket_name}"
}

# 📩 Notificación desde S3 al cargar archivo
resource "aws_s3_bucket_notification" "s3_to_lambda" {
  bucket = var.input_bucket_name

  lambda_function {
    lambda_function_arn = aws_lambda_function.my_lambda.arn
    events              = ["s3:ObjectCreated:*"]
  }

  depends_on = [aws_lambda_permission.allow_s3_invoke]
}

resource "aws_dynamodb_table" "reportes" {
  name         = "reportes"
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

