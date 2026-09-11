variable "aws_region" {
  type        = string
  default     = "us-east-1"
  description = "AWS Region for deployment"
}

variable "environment" {
  type        = string
  default     = "dev"
  description = "Environment tag"
}

variable "table_name" {
  type        = string
  default     = "dynavec_docs"
  description = "DynamoDB table name for document storage and metadata"
}

variable "vector_bucket_name" {
  type        = string
  default     = "dynavec-vectors-212919533030"
  description = "Globally unique S3 bucket name for vector storage"
}

variable "index_name" {
  type        = string
  default     = "docs-index"
  description = "S3 Vectors index name"
}
