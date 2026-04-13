# AWS Setup For First-Time Testing

This file is a deliberately naive step-by-step guide for getting Meaning-Mesh into a **first dev deployment on AWS**.

It assumes:

- you have **never used AWS before**
- you want the **simplest path** to a dev test
- you are okay doing a few things manually in the AWS console first
- after the manual setup, we will use the repo scripts and Terraform as much as possible

This is **not** a production guide.
This is a **first dev environment guide**.

---

## 1. What You Are Trying To Build

For `dev`, Meaning-Mesh has 4 parts:

1. `meaning-mesh-main-service`
   This will run as an AWS Lambda behind API Gateway.
2. `meaning-mesh-url-fetcher`
   This will run as another AWS Lambda triggered by SQS.
3. `meaning-mesh-url-categorizer`
   This will run as an ECS Fargate service.
4. `meaning-mesh-infra`
   This will create the AWS resources with Terraform.

In plain English:

- API Gateway receives the request
- Lambda checks DynamoDB and sends work to SQS
- Fetcher Lambda fetches the page
- ECS categorizer reads from another queue and writes the final answer

---

## 2. Big Picture Order

Follow this order exactly:

1. Create an AWS account
2. Secure the root account
3. Create an admin IAM user for daily work
4. Install local tools on your machine
5. Configure the AWS CLI
6. Create a budget so you do not get surprised by charges
7. Create an ECR repository for the categorizer image
8. Find the subnet IDs and security group ID you will use for `dev`
9. Build the Lambda zip files and Docker image
10. Run Terraform for the `dev` environment
11. Test the API

Do not skip ahead.

---

## 3. Create Your AWS Account

1. Go to AWS and create an account.
2. Use a credit card you control.
3. Choose a personal or business account. Either is fine for dev.
4. Complete phone verification.
5. Log in as the **root user** once the account is ready.

Important:

- The root user is the owner of the AWS account.
- You should **not** use the root user for normal development work.

---

## 4. Secure The Root User Immediately

Do this before anything else.

1. While logged in as root, enable **MFA** on the root account.
2. Save the recovery codes or backup method somewhere safe.
3. Make sure the root email is an address you control long term.

You should treat the root user like an emergency account only.

---

## 5. Create An Admin IAM User For Yourself

You need a normal AWS user for daily work.

In the AWS console:

1. Search for `IAM`.
2. Open `IAM`.
3. Go to `Users`.
4. Click `Create user`.
5. Choose a username like `yourname-admin`.
6. Give that user console access.
7. Attach administrator permissions for now.

For this first dev environment, the simplest choice is:

- attach `AdministratorAccess`

This is not ideal for production, but it is the easiest way to get unstuck while learning AWS.

After the user is created:

1. Sign out of the root user.
2. Sign in as the new IAM user.
3. Enable MFA for this IAM user too.

---

## 6. Set AWS Region To `us-east-1`

Meaning-Mesh is currently built around:

```text
us-east-1
```

In the AWS console:

1. Look at the top-right region selector.
2. Change it to `N. Virginia (us-east-1)`.

Keep using `us-east-1` everywhere unless we intentionally change the code and infra later.

---

## 7. Create A Budget First

Do this before deploying anything.

In the AWS console:

1. Search for `Budgets`.
2. Create a monthly cost budget.
3. Start with something small like:
   - `$10`
   - or `$25`
4. Add email alerts at:
   - 50%
   - 80%
   - 100%

This is especially important because:

- ECS
- Lambda
- API Gateway
- DynamoDB
- SQS
- data transfer

all cost money in different ways.

---

## 8. Install Local Tools On Your Machine

You will need these installed locally:

1. `aws`
2. `docker`
3. `terraform`
4. `git`

Check them:

```bash
aws --version
docker --version
terraform version
git --version
```

If one of them is missing, install it before continuing.

---

## 9. Create AWS Access Keys For CLI Use

You need CLI credentials for Terraform, Docker-to-ECR login, and AWS commands.

In the AWS console:

1. Open `IAM`
2. Open `Users`
3. Click your admin user
4. Open `Security credentials`
5. Create an access key
6. Choose CLI usage
7. Copy:
   - `AWS_ACCESS_KEY_ID`
   - `AWS_SECRET_ACCESS_KEY`

Store them safely.

Do not commit them anywhere.

---

## 10. Configure The AWS CLI

Run:

```bash
aws configure
```

Enter:

- AWS Access Key ID
- AWS Secret Access Key
- Default region: `us-east-1`
- Default output format: `json`

Then confirm:

```bash
aws sts get-caller-identity
```

If that works, your local machine can talk to AWS.

---

## 11. Create An ECR Repository Manually

The categorizer Docker image needs a place to live.

In the AWS console:

1. Search for `ECR`
2. Open `Elastic Container Registry`
3. Go to `Repositories`
4. Click `Create repository`
5. Create a private repository named:

```text
meaning-mesh-url-categorizer
```

After it is created, note the image URI.

It will look like:

```text
<account-id>.dkr.ecr.us-east-1.amazonaws.com/meaning-mesh-url-categorizer
```

You will use that later.

---

## 12. Choose Network Inputs For Dev

The Terraform `dev` deployment needs:

- subnet IDs
- security group IDs

For a first dev setup, the simplest path is:

1. Use the **default VPC**
2. Use two subnets in the default VPC
3. Use the default security group or a new permissive dev security group

In the AWS console:

1. Search for `VPC`
2. Open `Your VPCs`
3. Find the one marked as default
4. Open `Subnets`
5. Find 2 subnets that belong to the default VPC
6. Copy both subnet IDs
7. Open `Security Groups`
8. Copy the default security group ID

Write them down.

Example format:

```text
subnet-aaa111
subnet-bbb222
sg-ccc333
```

Important warning:

- The categorizer will need outbound internet access to download models and talk to external services.
- If networking does not work later, this is one of the first things to check.

---

## 13. Build The Deployable Artifacts

Go to the project root:

```bash
cd /path/to/meaning-mesh-project
```

Build the two Lambda zip files:

```bash
./meaning-mesh-main-service/scripts/build_lambda_package.sh
./meaning-mesh-url-fetcher/scripts/build_lambda_package.sh
```

Build and push the categorizer image:

```bash
./meaning-mesh-url-categorizer/scripts/build_and_push_image.sh \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/meaning-mesh-url-categorizer:dev
```

Or use the helper script from the infra repo:

```bash
./meaning-mesh-infra/scripts/build_dev_artifacts.sh \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/meaning-mesh-url-categorizer:dev
```

After this step you should have:

- `meaning-mesh-main-service/dist/lambda.zip`
- `meaning-mesh-url-fetcher/dist/lambda.zip`
- a pushed Docker image in ECR

---

## 14. Deploy The `dev` Infrastructure With Terraform

Go to the infra repo:

```bash
cd /path/to/meaning-mesh-project/meaning-mesh-infra
```

Use the helper script:

```bash
./scripts/deploy_dev.sh \
  /absolute/path/to/meaning-mesh-main-service/dist/lambda.zip \
  /absolute/path/to/meaning-mesh-url-fetcher/dist/lambda.zip \
  <account-id>.dkr.ecr.us-east-1.amazonaws.com/meaning-mesh-url-categorizer:dev \
  subnet-aaa111,subnet-bbb222 \
  sg-ccc333
```

This will:

1. run `terraform init`
2. run `terraform apply`
3. create the dev AWS resources

You will need to type:

```text
yes
```

when Terraform asks for confirmation.

---

## 15. Find The API Endpoint After Deploy

After Terraform finishes:

1. Look at the Terraform output
2. Copy the `api_endpoint`

It should look something like:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com
```

The route we created is:

```text
POST /categorize
```

So your full URL will be:

```text
https://abc123xyz.execute-api.us-east-1.amazonaws.com/categorize
```

---

## 16. Send Your First Test Request

Use `curl`:

```bash
curl -X POST "https://abc123xyz.execute-api.us-east-1.amazonaws.com/categorize" \
  -H "content-type: application/json" \
  -d '{
    "url": "https://example.com"
  }'
```

Expected first response is usually:

```json
{
  "status": "pending",
  "categories": []
}
```

That is normal.

Then:

1. wait a bit
2. send the same request again

If everything works, you should eventually get:

- `ready`
- or `unknown`

---

## 17. If Something Fails, Where To Look First

Check these services in the AWS console:

1. `Lambda`
   Look at both:
   - main service lambda
   - fetcher lambda

2. `CloudWatch`
   Open log groups and look for errors.

3. `SQS`
   Check whether messages are stuck in:
   - `url_fetcher_service_queue`
   - `url_categorizer_service_queue`
   - either DLQ

4. `ECS`
   Check whether the categorizer task started successfully.

5. `DynamoDB`
   Check whether these tables exist and are receiving items:
   - `url_categorization`
   - `url_wip`

---

## 18. Common Beginner Problems

### Problem: `aws sts get-caller-identity` fails

Possible causes:

- access keys are wrong
- wrong AWS profile
- AWS CLI not configured

### Problem: Docker push to ECR fails

Possible causes:

- you are not logged in to ECR
- the repo does not exist
- your AWS credentials are wrong

### Problem: Terraform fails immediately

Possible causes:

- Terraform is not installed
- AWS credentials are missing
- wrong subnet or security group IDs

### Problem: API returns `pending` forever

Possible causes:

- fetcher Lambda is failing
- categorizer ECS task is not running
- SQS messages are stuck
- networking is blocking the categorizer

### Problem: ECS categorizer will not start

Possible causes:

- image was not pushed correctly
- task role or execution role issue
- bad subnet/security group selection
- no outbound network access

---

## 19. What You Will Probably Do Manually In AWS

For the first dev run, expect to do these manually:

1. create AWS account
2. create IAM admin user
3. create access keys
4. set region to `us-east-1`
5. create a budget
6. create the ECR repository
7. copy subnet IDs
8. copy security group ID
9. inspect logs in CloudWatch when something fails

Everything else should move toward scripts/Terraform.

---

## 20. What To Ask For Help With Next

Once you complete the manual AWS setup above, the next good task is:

1. validate the exact subnet/security group choice
2. run the build scripts
3. run the dev Terraform deployment
4. test the first URL end-to-end

If you want, after you finish the manual console steps, we can do the actual deployment step together using the exact values from your AWS account.
