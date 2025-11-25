output "vpc_id" {
  value = var.create_vpc ? aws_vpc.main[0].id : ""
}

output "subnet_ids" {
  value = var.create_vpc ? aws_subnet.private[*].id : []
}
