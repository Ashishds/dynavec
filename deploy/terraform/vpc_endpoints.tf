# ------------------------------------------------------------------------------
# VPC Gateway Endpoints for DynamoDB & S3 ($0 AWS cost, Sub-5ms Private Routing)
# ------------------------------------------------------------------------------

variable "vpc_id" {
  type        = string
  default     = ""
  description = "Optional VPC ID to attach DynamoDB & S3 Gateway Endpoints for sub-5ms latency"
}

variable "route_table_ids" {
  type        = list(string)
  default     = []
  description = "Route table IDs in the VPC to associate with Gateway Endpoints"
}

# DynamoDB Gateway Endpoint (Eliminates internet hops, routes over AWS private fiber)
resource "aws_vpc_endpoint" "dynamodb" {
  count             = var.vpc_id != "" ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.dynamodb"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.route_table_ids

  tags = {
    Name        = "dynavec-dynamodb-endpoint-${var.environment}"
    Project     = "dynavec"
    Environment = var.environment
  }
}

# S3 Gateway Endpoint (Zero data transfer fees, high-throughput vector reads)
resource "aws_vpc_endpoint" "s3" {
  count             = var.vpc_id != "" ? 1 : 0
  vpc_id            = var.vpc_id
  service_name      = "com.amazonaws.${var.aws_region}.s3"
  vpc_endpoint_type = "Gateway"
  route_table_ids   = var.route_table_ids

  tags = {
    Name        = "dynavec-s3-endpoint-${var.environment}"
    Project     = "dynavec"
    Environment = var.environment
  }
}
