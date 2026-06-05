terraform {
  required_providers {
    opensearch = {
      source  = "opensearch-project/opensearch"
      version = "= 2.2.0"
    }
    random = {
      source  = "hashicorp/random"
      version = ">= 3.0"
    }
  }
}