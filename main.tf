provider "aws" {
  region     = var.aws_region
}

resource "aws_iam_role" "lambda_exec_role" {
  name = "nombre-lambda" # update

  assume_role_policy = jsonencode({
    Version = "2012-10-17",
    Statement = [{
      Action = "sts:AssumeRole",
      Principal = {
        Service = "lambda.amazonaws.com"
      },
      Effect = "Allow",
      Sid = ""
    }]
  })
}

resource "aws_iam_role_policy_attachment" "lambda_logs" {
  role = aws_iam_role.lambda_exec_role.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

resource "aws_lambda_function" "my_lambda" {
  function_name = "nombre_funcion-lambda" # update
  description   = "Mi función Lambda de ejemplo"
  role          = aws_iam_role.lambda_exec_role.arn
  handler       = "lambda_function.lambda_handler"
  runtime       = "python3.13"
  filename      = ""
  source_code_hash = filebase64sha256("")
 
  environment {
  
    variables = {
      ENV = "dev"
    }
  }
}