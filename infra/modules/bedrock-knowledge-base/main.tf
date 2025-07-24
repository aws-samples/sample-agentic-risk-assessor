# Bedrock Knowledge Base Module for Risk Agent Security Framework Mapping

# Data source for current region
data "aws_region" "current" {}
data "aws_caller_identity" "current" {}

# OpenSearch Serverless Collection for vector storage
resource "aws_opensearchserverless_collection" "knowledge_base" {
  name = "${var.project_name}-kb-collection"
  type = "VECTORSEARCH"

  tags = var.tags

  depends_on = [
    aws_opensearchserverless_security_policy.knowledge_base_encryption,
    aws_opensearchserverless_security_policy.knowledge_base_network,
    aws_opensearchserverless_vpc_endpoint.knowledge_base
  ]
}

# OpenSearch Serverless Security Policy
resource "aws_opensearchserverless_security_policy" "knowledge_base_encryption" {
  name = "${var.project_name}-kb-encryption-policy"
  type = "encryption"
  policy = jsonencode({
    Rules = [
      {
        Resource = [
          "collection/${var.project_name}-kb-collection"
        ]
        ResourceType = "collection"
      }
    ]
    AWSOwnedKey = true
  })
}

resource "aws_opensearchserverless_security_policy" "knowledge_base_network" {
  name = "${var.project_name}-kb-network-policy"
  type = "network"
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-kb-collection"
          ]
          ResourceType = "collection"
        }
      ]
      AllowFromPublic = false
      SourceVPCEs     = [aws_opensearchserverless_vpc_endpoint.knowledge_base.id]
    }
  ])
}

# VPC Endpoint for OpenSearch Serverless (restricts access to VPC only)
resource "aws_opensearchserverless_vpc_endpoint" "knowledge_base" {
  name               = "${var.project_name}-kb-vpce"
  vpc_id             = var.vpc_id
  subnet_ids         = var.private_subnet_ids
  security_group_ids = [aws_security_group.opensearch_vpce.id]
}

# Security group for OpenSearch Serverless VPC endpoint
resource "aws_security_group" "opensearch_vpce" {
  name_prefix = "${var.project_name}-opensearch-vpce-"
  vpc_id      = var.vpc_id
  description = "Allow HTTPS access to OpenSearch Serverless VPC endpoint"

  ingress {
    from_port   = 443
    to_port     = 443
    protocol    = "tcp"
    cidr_blocks = ["10.0.0.0/16"]
    description = "HTTPS from VPC"
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }

  tags = merge(var.tags, {
    Name = "${var.project_name}-opensearch-vpce-sg"
  })
}

# Data Access Policy
resource "aws_opensearchserverless_access_policy" "knowledge_base" {
  name = "${var.project_name}-kb-access-policy"
  type = "data"
  policy = jsonencode([
    {
      Rules = [
        {
          Resource = [
            "collection/${var.project_name}-kb-collection"
          ]
          Permission = [
            "aoss:CreateCollectionItems",
            "aoss:DeleteCollectionItems",
            "aoss:UpdateCollectionItems",
            "aoss:DescribeCollectionItems"
          ]
          ResourceType = "collection"
        },
        {
          Resource = [
            "index/${var.project_name}-kb-collection/*"
          ]
          Permission = [
            "aoss:CreateIndex",
            "aoss:DeleteIndex",
            "aoss:UpdateIndex",
            "aoss:DescribeIndex",
            "aoss:ReadDocument",
            "aoss:WriteDocument"
          ]
          ResourceType = "index"
        }
      ]
      Principal = [
        aws_iam_role.knowledge_base.arn,
        "arn:aws:iam::${data.aws_caller_identity.current.account_id}:root"
      ]
    }
  ])
}

# IAM Role for Knowledge Base
resource "aws_iam_role" "knowledge_base" {
  name = "${var.project_name}-bedrock-kb-role"

  assume_role_policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Action = "sts:AssumeRole"
        Effect = "Allow"
        Principal = {
          Service = "bedrock.amazonaws.com"
        }
      }
    ]
  })

  tags = var.tags
}

# IAM Policy for Knowledge Base
resource "aws_iam_role_policy" "knowledge_base" {
  name = "${var.project_name}-bedrock-kb-policy"
  role = aws_iam_role.knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "aoss:APIAccessAll"
        ]
        Resource = [
          aws_opensearchserverless_collection.knowledge_base.arn
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "bedrock:InvokeModel"
        ]
        Resource = [
          "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "aoss:CreateIndex",
          "aoss:DeleteIndex",
          "aoss:UpdateIndex",
          "aoss:DescribeIndex"
        ]
        Resource = [
          "${aws_opensearchserverless_collection.knowledge_base.arn}/*"
        ]
      },
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.framework_docs.arn,
          "${aws_s3_bucket.framework_docs.arn}/*"
        ]
      },
      {
        Effect   = "Allow"
        Action   = [
          "kms:Decrypt",
          "kms:GenerateDataKey"
        ]
        Resource = [
          var.s3_kms_key_arn
        ]
      }
    ]
  })
}

# Wait for OpenSearch Serverless collection to be fully ready
resource "time_sleep" "opensearch_propagation" {
  depends_on = [
    aws_opensearchserverless_collection.knowledge_base,
    aws_opensearchserverless_access_policy.knowledge_base
  ]
  create_duration = "2m"
}

# Vector index "risk-agent-kb-index" exists in the OpenSearch Serverless collection.
# Cannot be managed by Terraform after VPC endpoint restriction (no public access).
# Index was created prior to VPC restriction and remains functional.
locals {
  opensearch_index_name = "risk-agent-kb-index"
}

# Bedrock Knowledge Base
resource "aws_bedrockagent_knowledge_base" "security_frameworks" {
  name     = "${var.project_name}-security-frameworks-kb"
  role_arn = aws_iam_role.knowledge_base.arn

  knowledge_base_configuration {
    vector_knowledge_base_configuration {
      embedding_model_arn = "arn:aws:bedrock:${var.aws_region}::foundation-model/amazon.titan-embed-text-v2:0"
    }
    type = "VECTOR"
  }

  storage_configuration {
    opensearch_serverless_configuration {
      collection_arn    = aws_opensearchserverless_collection.knowledge_base.arn
      vector_index_name = local.opensearch_index_name
      field_mapping {
        vector_field   = "bedrock-knowledge-base-default-vector"
        text_field     = "AMAZON_BEDROCK_TEXT_CHUNK"
        metadata_field = "AMAZON_BEDROCK_METADATA"
      }
    }
    type = "OPENSEARCH_SERVERLESS"
  }

  tags = var.tags

  depends_on = [
    aws_opensearchserverless_access_policy.knowledge_base,
    aws_iam_role_policy.knowledge_base
  ]
}

# S3 Bucket for Framework Documents
resource "aws_s3_bucket" "framework_docs" {
  bucket = "${var.project_name}-framework-docs"
  tags   = var.tags
}

resource "aws_s3_bucket_public_access_block" "framework_docs" {
  bucket = aws_s3_bucket.framework_docs.id

  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

# Framework Prefixes (Folders) in S3 Bucket
resource "aws_s3_object" "nist_800_53_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "nist-800-53/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "iso_27001_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "iso-27001/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "cis_controls_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "cis-controls/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "ci_profile_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "ci-profile/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "cps234_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "cps234/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "pci_dss_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "pci-dss/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "sox_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "sox/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "fedramp_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "fedramp/"
  content_type = "application/x-directory"
}

resource "aws_s3_object" "cri_prefix" {
  bucket       = aws_s3_bucket.framework_docs.id
  key          = "cri/"
  content_type = "application/x-directory"
}

resource "aws_s3_bucket_versioning" "framework_docs" {
  bucket = aws_s3_bucket.framework_docs.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "framework_docs" {
  bucket = aws_s3_bucket.framework_docs.id

  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm     = "aws:kms"
      kms_master_key_id = var.s3_kms_key_arn
    }
    bucket_key_enabled = true
  }
}

# IAM policy for Knowledge Base to access S3 bucket
resource "aws_iam_role_policy" "knowledge_base_s3" {
  name = "${var.project_name}-bedrock-kb-s3-policy"
  role = aws_iam_role.knowledge_base.id

  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [
      {
        Effect = "Allow"
        Action = [
          "s3:GetObject",
          "s3:ListBucket"
        ]
        Resource = [
          aws_s3_bucket.framework_docs.arn,
          "${aws_s3_bucket.framework_docs.arn}/*"
        ]
      }
    ]
  })
}

# Data Source: S3-based Framework Documents
resource "aws_bedrockagent_data_source" "frameworks_s3" {
  knowledge_base_id = aws_bedrockagent_knowledge_base.security_frameworks.id
  name              = "security-frameworks-s3"

  data_source_configuration {
    type = "S3"
    s3_configuration {
      bucket_arn = aws_s3_bucket.framework_docs.arn
    }
  }

  vector_ingestion_configuration {
    chunking_configuration {
      chunking_strategy = "HIERARCHICAL"
      hierarchical_chunking_configuration {
        level_configuration {
          max_tokens = var.parent_chunk_size
        }
        level_configuration {
          max_tokens = var.chunk_size
        }
        overlap_tokens = var.chunk_overlap
      }
    }
  }

  depends_on = [
    aws_iam_role_policy.knowledge_base_s3
  ]
}
