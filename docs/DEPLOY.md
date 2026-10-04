# Deploying dynavec

Three things: publish to PyPI (pip/uv), deploy the landing page to GitHub Pages,
and give the library AWS credentials with least-privilege IAM.

---

## 1. Publish to PyPI (pip + uv)

`pip` and `uv` both install from PyPI — publish once, both work.

### a. Register the Trusted Publisher on PyPI (one time, no token)

At <https://pypi.org/manage/account/publishing/>, add a **GitHub** publisher with
**exactly** these values (they must match the committed workflow):

| Field | Value |
|-------|-------|
| PyPI Project Name | `dynavec` |
| Owner | `codeforstartups` |
| Repository name | `dynavec` |
| **Workflow name** | **`publish.yml`**  ← not `workflow.yml` |
| **Environment name** | **`pypi`** |

> The two bold fields are the ones people miss. The committed workflow is
> `.github/workflows/publish.yml` and it declares `environment: pypi`, so both
> must match or PyPI will reject the OIDC token.

### b. Create the `pypi` environment on GitHub (one time)

Repo → **Settings → Environments → New environment → `pypi`**. (Optional but
recommended; add required reviewers here if you want a manual approval gate.)

### c. Release

Bump the version in **both** `pyproject.toml` and `src/dynavec/__init__.py`, then:

```bash
git tag v0.2.0
git push origin v0.2.0
```

Then create a **GitHub Release** for that tag (UI, or `gh release create v0.2.0
--generate-notes`). Publishing the release triggers `publish.yml`, which builds
and uploads via OIDC. Done — `pip install dynavec` / `uv add dynavec` now work.

### Manual fallback (from your machine, with a token)

```bash
uv build
UV_PUBLISH_TOKEN=pypi-XXXX uv publish
# or: python -m twine upload dist/*
```

Tip: test on TestPyPI first with `uv publish --publish-url https://test.pypi.org/legacy/`.

## 2. Deploy Web Console & Landing Page

The `dashboard/` directory contains a unified Next.js web application encompassing both the marketing landing page and the enterprise console.

### Option A: Vercel (Fastest & Zero-Maintenance)

The project includes a pre-configured `dashboard/vercel.json`.

1. Import the repository into [Vercel](https://vercel.com).
2. Set **Root Directory** to `dashboard`.
3. Framework Preset: **Next.js** (Auto-detected).
4. Build Command: `npm run build` (Static export to `out`).
5. (Optional) Set Environment Variable:
   - `NEXT_PUBLIC_DYNAVEC_API`: URL of your live Python Telemetry API (e.g., `https://api.yourdomain.com`).
6. Deploy.

Alternatively, via Vercel CLI:
```bash
cd dashboard
npx vercel --prod
```

### Option B: AWS S3 + CloudFront (Enterprise Serverless)

Exported static assets in `dashboard/out` can be hosted on Amazon S3 fronted by AWS CloudFront:

```bash
cd dashboard
npm ci
npm run build

# Sync static build output to S3 bucket
aws s3 sync out/ s3://dynavec-console-bucket --delete

# Invalidate CloudFront edge cache
aws cloudfront create-invalidation --distribution-id YOUR_DIST_ID --paths "/*"
```

Configure CloudFront with:
- Origin Access Control (OAC) to the S3 bucket.
- Custom Error Responses: Map HTTP 403 & 404 to `/index.html` with response code 200 for client-side navigation.

### Option C: GitHub Pages via Automated Workflow

The repository includes `.github/workflows/deploy-pages.yml` which automatically builds and publishes both the landing page and static dashboard:

1. Repo → **Settings → Pages → Build and deployment → Source: GitHub Actions**.
2. Push to `main` or trigger manually from the Actions tab.
3. The site goes live at `https://codeforstartups.github.io/dynavec/`.

---

## 3. Deploy Live Telemetry & Query API

The Python API serves live vector queries, cluster health, latency percentiles, and traces (`examples/aws_live_dashboard.py` / `dynavec.dashboard`).

### Option A: Containerized Deployment (Docker / AWS ECS / App Runner)

Use the root `Dockerfile` and `docker-compose.yml`:

```bash
# Build and run locally or on an EC2 instance
docker compose up -d

# Check running services
docker ps
```

To deploy on **AWS App Runner** or **AWS ECS Fargate**:
1. Push image to Amazon ECR:
   ```bash
   aws ecr get-login-password --region us-east-1 | docker login --username AWS --password-stdin <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com
   docker build -t dynavec-service:latest .
   docker tag dynavec-service:latest <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/dynavec-service:latest
   docker push <ACCOUNT_ID>.dkr.ecr.us-east-1.amazonaws.com/dynavec-service:latest
   ```
2. Create an App Runner Service or ECS Task Definition with task role granting DynamoDB and S3 Vectors access (see IAM policy below).

### Option B: Standalone Service with Token Security

Run directly on any Linux / Windows host:

```bash
export DYNAVEC_DASHBOARD_TOKEN="your-secure-bearer-token"
dynavec dashboard --port 8778 --host 0.0.0.0
```

---

## 4. Cloud Infrastructure via Terraform

Provision the AWS DynamoDB table and S3 Vector bucket using the checked-in Terraform configuration:

```bash
cd deploy/terraform
terraform init
terraform plan
terraform apply -auto-approve
```

This creates:
- **DynamoDB Table**: `dynavec_docs` (Mode: `PAY_PER_REQUEST` / ₹0 when idle)
- **S3 Vector Bucket**: Server-side encrypted with AES-256
- **S3 Vectors Index**: Cosine similarity index

---

## 5. AWS credentials (.env) + IAM permissions

### The `.env`

Copy `.env.example` → `.env` (already gitignored) and fill it in. dynavec uses
the standard boto3 credential chain, so exported env vars just work:

```bash
cp .env.example .env
# edit .env, then:
export $(grep -v '^#' .env | xargs)      # load into the shell
python examples/openai_1536_retrieval.py
```

Or load it in Python without exporting:

```python
from dotenv import load_dotenv          # pip install python-dotenv
load_dotenv()
from dynavec import Dynavec, DynavecConfig
db = Dynavec(DynavecConfig(..., region="us-east-1"))   # boto3 picks up the env creds
```

Or pass keys explicitly (e.g. multi-account) instead of the env chain:

```python
import os
from dynavec import Dynavec, DynavecConfig, AWSCredentials
creds = AWSCredentials(
    access_key_id=os.environ["AWS_ACCESS_KEY_ID"],
    secret_access_key=os.environ["AWS_SECRET_ACCESS_KEY"],
    region="us-east-1",
    # assume_role_arn="arn:aws:iam::OTHER_ACCOUNT:role/dynavec",  # cross-account
)
db = Dynavec(cfg, credentials=creds)
```

### The IAM policy

Create an IAM user (or role) and attach `docs/iam-policy.json` — replace
`REGION` and `ACCOUNT_ID`. It grants only what dynavec uses:

- **s3vectors**: create/get/list/delete vector buckets & indexes; put/get/list/query/delete vectors
- **dynamodb**: create/describe/delete table; batch + single-item read/write; `UpdateItem` (knowledge graph); `Query` (future access patterns)

Then create the access key for that user and put it in `.env`.

> **Tighten for production:** the s3vectors statement uses `Resource: "*"` because
> S3 Vectors ARN formats are new — scope it to your bucket/index ARNs once
> confirmed in the AWS console. The DynamoDB statement is already scoped to
> `dynavec_*` tables; rename to match your table if different. Drop `DeleteTable`
> / `Delete*` if you never run the cleanup scripts.

### Optional add-ons (only if you use them)

Add these statements to the policy if the corresponding feature is used:

```jsonc
// BedrockEmbedder (embeddings stay in-account)
{ "Effect": "Allow", "Action": ["bedrock:InvokeModel"],
  "Resource": "arn:aws:bedrock:REGION::foundation-model/amazon.titan-embed-text-v2:0" }

// LambdaTransform (transform vectors/metadata in your own Lambda)
{ "Effect": "Allow", "Action": ["lambda:InvokeFunction"],
  "Resource": "arn:aws:lambda:REGION:ACCOUNT_ID:function:YOUR_FUNCTION" }

// DynamoDB TTL cache housekeeping (only if enabling TTL via code)
{ "Effect": "Allow", "Action": ["dynamodb:UpdateTimeToLive","dynamodb:DescribeTimeToLive"],
  "Resource": "arn:aws:dynamodb:REGION:ACCOUNT_ID:table/dynavec_*" }
```

### Never commit secrets

`.env` is in `.gitignore`. For CI, put keys in **GitHub Secrets**, not the repo.
For production apps, prefer an **IAM role** (instance/task role, or OIDC) over
long-lived access keys entirely.

---

## 6. Post-Deployment Verification & Smoke Test

Once deployed, verify end-to-end cloud connectivity, dual-write consistency, and cache performance:

```bash
python scripts/production_smoke_test.py
```

Expected verification output:
```
CHECK                                  | STATUS   | LATENCY / DETAILS
Dual-Write Ingestion (DynamoDB + S3)   | [PASS]   | Dual-write confirmed
Cold AWS Cloud Search                  | [PASS]   | In-cluster vector match
Warm Semantic Cache Hit                | [PASS]   | < 1.0 ms response
>>> ALL PRODUCTION INVARIANTS VERIFIED SUCCESSFULLY! <<<
```

