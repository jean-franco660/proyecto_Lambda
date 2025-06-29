output "lambda_function_name" {
  description = "Nombre de la función Lambda"
  value       = aws_lambda_function.process_csv.function_name
}
output "lambda_function_name" {
  value = aws_lambda_function.csv_processor.function_name
}

output "lambda_function_arn" {
  value = aws_lambda_function.csv_processor.arn
}

output "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB"
  value       = aws_dynamodb_table.reportes.name
}

output "dynamodb_table_arn" {
  description = "ARN de la tabla DynamoDB"
  value       = aws_dynamodb_table.reportes.arn
}

