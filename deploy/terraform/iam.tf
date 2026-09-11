# ------------------------------------------------------------------------------
# Production IAM Role & Least-Privilege Policies (Zero Static Access Keys)
# ------------------------------------------------------------------------------

# ECS / Application Task Role (assumed by container runtime)
resource "aws_iam_role" "dynavec_app_role" {
  name = "dynavec-app-${var.environment}-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = [
            "ecs-tasks.amazonaws.com",
            "lambda.amazonaws.com",
            "ec2.amazonaws.com"
          ]
        }
      }
    ]
  })

  tags = {
    Project     = "dynavec"
    Environment = var.environment
  }
}

# Least-Privilege Policy for DynamoDB Table
resource "aws_iam_policy" "dynavec_dynamodb_policy" {
  name        = "dynavec-dynamodb-${var.environment}-policy"
  description = "Scoped DynamoDB permissions for Dynavec document hydration"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "dynamodb:BatchGetItem",
          "dynamodb:BatchWriteItem",
          "dynamodb:GetItem",
          "dynamodb:PutItem",
          "dynamodb:UpdateItem",
          "dynamodb:DeleteItem",
          "dynamodb:Query",
          "dynamodb:Scan"
        ]
        Resource = aws_dynamodb_table.dynavec_docs.arn
      }
    ]
  })
}

# Least-Privilege Policy for S3 Vectors & Bucket
resource "aws_iam_policy" "dynavec_s3_policy" {
  name        = "dynavec-s3-${var.environment}-policy"
  description = "Scoped S3 and S3 Vectors permissions for vector index queries"

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:PutObject",
          "s3:DeleteObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.vector_bucket.arn,
          "${aws_s3_bucket.vector_bucket.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3vectors:*"
        ]
        Resource = "*"
      }
    ]
  })
}

# Attach policies to App Role
resource "aws_iam_role_policy_attachment" "attach_dynamodb" {
  role       = aws_iam_role.dynavec_app_role.name
  policy_arn = aws_iam_policy.dynavec_dynamodb_policy.arn
}

resource "aws_iam_role_policy_attachment" "attach_s3" {
  role       = aws_iam_role.dynavec_app_role.name
  policy_arn = aws_iam_policy.dynavec_s3_policy.arn
}
