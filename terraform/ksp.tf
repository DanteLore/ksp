provider "aws" {
  region = "eu-west-1"
}

variable "function_name" {
  default = "ksp_repair_docking_ports"
}

variable "bucket_name" {
  default = "dantelore.ksp"
}

variable "handler" {
  default = "lambda_function.handler"
}

variable "runtime" {
  default = "python3.9"
}

resource "aws_s3_bucket" "ksp_bucket" {
  bucket = var.bucket_name
}

resource "aws_s3_bucket_acl" "ksp_bucket" {
  bucket = aws_s3_bucket.ksp_bucket.id
  acl    = "private"
}

resource "aws_s3_bucket_public_access_block" "ksp_bucket" {
  bucket = aws_s3_bucket.ksp_bucket.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_cors_configuration" "example" {
  bucket = aws_s3_bucket.ksp_bucket.id

  cors_rule {
    allowed_headers = ["*"]
    allowed_methods = ["PUT"]
    allowed_origins = ["*"]
    expose_headers  = ["ETag"]
    max_age_seconds = 3000
  }

  cors_rule {
    allowed_methods = ["GET"]
    allowed_origins = ["*"]
  }
}

resource "aws_cloudwatch_log_group" "log_group" {
  name              = "/aws/lambda/${var.function_name}"
  retention_in_days = 3
}

resource "aws_lambda_function" "ksp_lambda_function" {
  role             = aws_iam_role.lambda_exec_role.arn
  handler          = var.handler
  runtime          = var.runtime
  filename         = "lambda.zip"
  function_name    = var.function_name
  source_code_hash = filebase64sha256("lambda.zip")
  timeout          = 60
  memory_size      = 1024
}

resource "aws_iam_role" "lambda_exec_role" {
  name        = "execute_ksp_lambda"
  path        = "/"
  description = "IAM role for the KSP lambda function"

  assume_role_policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Effect": "Allow",
      "Principal": {
        "Service": "lambda.amazonaws.com"
      },
      "Action": "sts:AssumeRole"
    }
  ]
}
EOF
}

resource "aws_iam_policy" "lambda_policy" {
  name        = "ksp_policy"
  path        = "/"

  policy = <<EOF
{
  "Version": "2012-10-17",
  "Statement": [
    {
      "Action": [
        "logs:CreateLogStream",
        "logs:PutLogEvents"
      ],
      "Resource": [
          "*"
      ]
      ,
      "Effect": "Allow",
      "Sid": ""
    },
    {
      "Action": [
        "s3:GetObject*",
        "s3:ListBucket*",
        "s3:PutObject*",
        "s3:GetBucketLocation",
        "s3:ListMultipartUploadParts",
        "s3:AbortMultipartUpload",
        "s3:CreateBucket",
        "s3:PutObject"
      ],
      "Resource": [
          "arn:aws:s3:::${var.bucket_name}",
          "arn:aws:s3:::${var.bucket_name}/*"
      ]
      ,
      "Effect": "Allow",
      "Sid": ""
    }
  ]
}
EOF
}

resource "aws_iam_role_policy_attachment" "server_policy" {
  role       = aws_iam_role.lambda_exec_role.name
  policy_arn = aws_iam_policy.lambda_policy.arn
}

resource "aws_iam_instance_profile" "server" {
  name = "ksp_lambda_profile"
  role = aws_iam_role.lambda_exec_role.name
}

# REST API


resource "aws_api_gateway_rest_api" "ksp_rest_api" {
  name        = "KSP REST API"
  description = "Tye REST API for the KSP save file fixer"
}

resource "aws_api_gateway_resource" "proxy" {
  rest_api_id = aws_api_gateway_rest_api.ksp_rest_api.id
  parent_id   = aws_api_gateway_rest_api.ksp_rest_api.root_resource_id
  path_part   = "{proxy+}"
}

resource "aws_api_gateway_method" "proxy" {
  rest_api_id   = aws_api_gateway_rest_api.ksp_rest_api.id
  resource_id   = aws_api_gateway_resource.proxy.id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda" {
  rest_api_id = aws_api_gateway_rest_api.ksp_rest_api.id
  resource_id = aws_api_gateway_method.proxy.resource_id
  http_method = aws_api_gateway_method.proxy.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ksp_lambda_function.invoke_arn
}

resource "aws_api_gateway_method" "proxy_root" {
  rest_api_id   = aws_api_gateway_rest_api.ksp_rest_api.id
  resource_id   = aws_api_gateway_rest_api.ksp_rest_api.root_resource_id
  http_method   = "POST"
  authorization = "NONE"
}

resource "aws_api_gateway_integration" "lambda_root" {
  rest_api_id = aws_api_gateway_rest_api.ksp_rest_api.id
  resource_id = aws_api_gateway_method.proxy_root.resource_id
  http_method = aws_api_gateway_method.proxy_root.http_method

  integration_http_method = "POST"
  type                    = "AWS_PROXY"
  uri                     = aws_lambda_function.ksp_lambda_function.invoke_arn
}

resource "aws_api_gateway_deployment" "ksp_api_deployment" {
  depends_on = [
    aws_api_gateway_integration.lambda,
    aws_api_gateway_integration.lambda_root,
  ]

  rest_api_id = aws_api_gateway_rest_api.ksp_rest_api.id
  stage_name  = "prod"
}

resource "aws_lambda_permission" "apigw" {
  statement_id  = "AllowAPIGatewayInvoke"
  action        = "lambda:InvokeFunction"
  function_name = aws_lambda_function.ksp_lambda_function.function_name
  principal     = "apigateway.amazonaws.com"
  source_arn = "${aws_api_gateway_rest_api.ksp_rest_api.execution_arn}/*/*"
}

output "base_url" {
  value = aws_api_gateway_deployment.ksp_api_deployment.invoke_url
}

module "cors" {
  source = "squidfunk/api-gateway-enable-cors/aws"
  version = "0.3.3"
  api_id            = aws_api_gateway_rest_api.ksp_rest_api.id
  api_resource_id   = aws_api_gateway_resource.proxy.id
  allow_headers = ["*"]
  allow_methods = ["POST", "OPTIONS"]
  allow_origin = "*"
}

