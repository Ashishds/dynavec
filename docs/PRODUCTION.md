# Dynavec Production Hardening & Architecture Guide

This guide outlines architectural patterns, IAM security policies, networking, performance tuning, and operational runbooks for deploying **dynavec** in production environments.

---

## 1. Architecture Overview

Dynavec uses a dual-store hybrid architecture running entirely inside **your own AWS account**:
1. **Amazon S3 Vectors**: Scalable, serverless Approximate Nearest Neighbor (ANN) index.
2. **Amazon DynamoDB**: Sub-10ms document hydration, metadata filtering, knowledge-graph relationships, and transactional cache.

Because both components are managed AWS primitives, there are zero ec2/k8s vector clusters to patch, scale, or pay idle charges for.

---

## 2. Production Deployment Checklist

| Category | Item | Production Recommendation |
|:---|:---|:---|
| **Security** | IAM Least Privilege | Dedicated IAM Role attached to task/pod with minimal actions |
| **Security** | Encryption at Rest | AWS KMS customer managed key (CMK) for DynamoDB and S3 bucket |
| **Network** | VPC Gateway Endpoints | Route DynamoDB and S3 traffic via private AWS network (0 NAT cost) |
| **Availability**| DynamoDB PITR | Point-in-time recovery enabled for disaster recovery |
| **Scaling** | DynamoDB Billing | `PAY_PER_REQUEST` for unpredictable workloads, `PROVISIONED` for steady baseline |
| **Monitoring** | CloudWatch Alarms | Alarm on `UserErrors`, `ThrottledRequests`, and `SystemErrors` |
| **Dashboard** | Token Authentication | Set `DYNAVEC_DASHBOARD_TOKEN` or keep behind private VPC reverse proxy |

---

## 3. Least-Privilege IAM Policy

Attach the following policy to your application's IAM execution role (e.g. ECS task role, EKS ServiceAccount IRSA, or Lambda execution role):

```json
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Sid": "DynavecDynamoDBAccess",
      "Effect": "Allow",
      "Action": [
        "dynamodb:GetItem",
        "dynamodb:BatchGetItem",
        "dynamodb:PutItem",
        "dynamodb:BatchWriteItem",
        "dynamodb:UpdateItem",
        "dynamodb:DeleteItem",
        "dynamodb:Query",
        "dynamodb:DescribeTable"
      ],
      "Resource": [
        "arn:aws:dynamodb:*:*:table/dynavec_*",
        "arn:aws:dynamodb:*:*:table/dynavec_*/index/*"
      ]
    },
    {
      "Sid": "DynavecS3VectorsAccess",
      "Effect": "Allow",
      "Action": [
        "s3vectors:GetIndex",
        "s3vectors:Search",
        "s3vectors:PutVectors",
        "s3vectors:DeleteVectors",
        "s3vectors:ListVectors"
      ],
      "Resource": [
        "arn:aws:s3vectors:*:*:vector-bucket/*",
        "arn:aws:s3vectors:*:*:vector-bucket/*/index/*"
      ]
    }
  ]
}
```

> [!NOTE]
> If `auto_provision=True` is enabled in production, the role also requires `dynamodb:CreateTable` and `s3vectors:CreateVectorBucket`/`s3vectors:CreateIndex`. Alternatively, provision infrastructure in advance via Terraform/CDK and set `auto_provision=False`.

---

## 4. VPC Gateway Endpoints (Zero Egress Costs)

Ensure your AWS VPC has VPC Endpoints enabled for **DynamoDB** and **S3**. This routes traffic directly over the AWS private backbone:
- Eliminates NAT Gateway data processing fees (~$0.045/GB)
- Provides microsecond network latency improvements
- Completely prevents traffic from traversing the public internet

```bash
# Example AWS CLI creating S3 and DynamoDB Gateway Endpoints
aws ec2 create-vpc-endpoint \
    --vpc-id vpc-xxxxxxxxx \
    --service-name com.amazonaws.us-east-1.s3 \
    --route-table-ids rtb-xxxxxxxxx

aws ec2 create-vpc-endpoint \
    --vpc-id vpc-xxxxxxxxx \
    --service-name com.amazonaws.us-east-1.dynamodb \
    --route-table-ids rtb-xxxxxxxxx
```

---

## 5. Configuration Best Practices

Use `DynavecConfig.from_env()` to automatically source configuration from twelve-factor environment variables:

```python
import os
from dynavec import Dynavec, DynavecConfig

# Set production environment variables:
# export DYNAVEC_VECTOR_BUCKET="corp-vector-bucket"
# export DYNAVEC_INDEX="enterprise-search"
# export DYNAVEC_TABLE="dynavec_enterprise_docs"
# export DYNAVEC_DIMENSION="1536"
# export DYNAVEC_REGION="us-east-1"
# export DYNAVEC_MAX_WORKERS="16"

cfg = DynavecConfig.from_env()
cfg.validate()

db = Dynavec(cfg)
```

---

## 6. Performance & Cost Optimization

1. **Keep Filterable Metadata Focused**:
   S3 Vectors allows pre-filtering on metadata attributes. Only specify keys that you actually filter on (`filterable_keys=["tenant_id", "status"]`). Store extensive payloads in DynamoDB to minimize index memory overhead.

2. **Hot-Tier Caching**:
   Enable in-memory or DynamoDB semantic caching for repeat or near-duplicate queries:
   ```python
   from dynavec.cache import SemanticCache
   db = Dynavec(cfg, cache=SemanticCache(threshold=0.98, max_entries=50_000))
   ```

3. **int8 Scalar Quantization**:
   For memory-constrained environments or ultra-fast caching, use `ScalarQuantizer` for a 4x reduction in cache footprint with >98% accuracy retention.

---

## 7. CloudWatch Alarms & Monitoring Runbook

Set CloudWatch Alarms on the following DynamoDB metrics:

- **`ThrottledRequests` > 0**:
  - *Cause*: Exceeded provisioned throughput on partition keys.
  - *Mitigation*: Switch table to `PAY_PER_REQUEST` billing mode or verify key distribution across namespaces.
- **`SystemErrors` > 0**:
  - *Cause*: Transient AWS service degradation.
  - *Mitigation*: Built-in boto3 retries with exponential backoff handle this automatically.
