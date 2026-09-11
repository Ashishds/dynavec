output "aws_region" {
  value       = var.aws_region
  description = "AWS Region"
}

output "dynamodb_table" {
  value       = aws_dynamodb_table.dynavec_docs.name
  description = "DynamoDB table name"
}

output "vector_bucket" {
  value       = aws_s3_bucket.vector_bucket.bucket
  description = "S3 Vector bucket name"
}

output "index_name" {
  value       = var.index_name
  description = "Vector index name"
}
