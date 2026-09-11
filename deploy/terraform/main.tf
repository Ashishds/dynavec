terraform {
  required_version = ">= 1.5.0"
  required_providers {
    aws = {
      source  = "hashicorp/aws"
      version = "~> 5.0"
    }
  }
}

provider "aws" {
  region = var.aws_region
}

# ------------------------------------------------------------------------------
# 1. DynamoDB Table (Pay-per-request / On-Demand = 0 cost when idle)
# ------------------------------------------------------------------------------
resource "aws_dynamodb_table" "dynavec_docs" {
  name         = var.table_name
  billing_mode = "PAY_PER_REQUEST"
  hash_key     = "pk"

  attribute {
    name = "pk"
    type = "S"
  }

  point_in_time_recovery {
    enabled = false
  }

  tags = {
    Project     = "dynavec"
    Environment = var.environment
  }
}

# ------------------------------------------------------------------------------
# 2. S3 Bucket for Vector Storage
# ------------------------------------------------------------------------------
resource "aws_s3_bucket" "vector_bucket" {
  bucket        = var.vector_bucket_name
  force_destroy = true # Allows clean 1-step deletion during teardown

  tags = {
    Project     = "dynavec"
    Environment = var.environment
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "bucket_encryption" {
  bucket = aws_s3_bucket.vector_bucket.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}
