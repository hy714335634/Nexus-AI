output "lambda_sg_id" {
  value = aws_security_group.lambda.id
}

output "efs_sg_id" {
  value = aws_security_group.efs.id
}
