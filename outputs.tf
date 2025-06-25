output "lambda_function_arn" {
  description = "ARN de la función Lambda"
  value       = aws_lambda_function.my_lambda.arn
}

output "lambda_function_name" {
  description = "Nombre de la función Lambda"
  value       = aws_lambda_function.my_lambda.function_name
}

output "dynamo_table_name" {
  value = aws_dynamodb_table.reportes.name
}