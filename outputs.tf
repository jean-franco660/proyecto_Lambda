output "lambda_function_name" {
  description = "Nombre de la función Lambda"
  value       = aws_lambda_function.my_lambda.function_name
}

output "lambda_role_arn" {
  description = "ARN del rol IAM asignado a Lambda"
  value       = aws_iam_role.lambda_exec_role.arn
}

output "dynamodb_table_name" {
  description = "Nombre de la tabla DynamoDB"
  value       = aws_dynamodb_table.historial.name
}

output "dynamodb_table_arn" {
  description = "ARN de la tabla DynamoDB"
  value       = aws_dynamodb_table.historial.arn
}
