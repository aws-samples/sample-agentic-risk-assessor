locals {
  dynamodb_tables = {
    projects = {
      hash_key = "id"
      attributes = [
        {
          name = "id"
          type = "S"
        }
      ]
    }
    node_controls = {
      hash_key = "project_id"
      range_key = "node_id"
      attributes = [
        {
          name = "project_id"
          type = "S"
        },
        {
          name = "node_id"
          type = "S"
        }
      ]
    }
    services = {
      hash_key = "ServiceName"
      attributes = [
        {
          name = "ServiceName"
          type = "S"
        }
      ]
    }
    service_controls = {
      hash_key = "ServiceName"
      range_key = "Framework"
      attributes = [
        {
          name = "ServiceName"
          type = "S"
        },
        {
          name = "Framework"
          type = "S"
        }
      ]
    }
    diagram_analysis = {
      hash_key = "project_id"
      attributes = [
        {
          name = "project_id"
          type = "S"
        }
      ]
    }
    sessions = {
      hash_key = "session_id"
      range_key = "sort_key"
      attributes = [
        {
          name = "session_id"
          type = "S"
        },
        {
          name = "sort_key"
          type = "S"
        },
        {
          name = "user_id"
          type = "S"
        },
        {
          name = "agent_id"
          type = "S"
        }
      ]
      ttl_attribute = "ttl"
      global_secondary_indexes = [
        {
          name = "UserAgentIndex"
          hash_key = "user_id"
          range_key = "agent_id"
          projection_type = "ALL"
        }
      ]
    }
    search_cache = {
      hash_key = "cache_key"
      attributes = [
        {
          name = "cache_key"
          type = "S"
        }
      ]
      ttl_attribute = "ttl"
    }
    profiles = {
      hash_key = "profile_id"
      attributes = [
        {
          name = "profile_id"
          type = "S"
        },
        {
          name = "user_id"
          type = "S"
        }
      ]
      global_secondary_indexes = [
        {
          name = "UserIdIndex"
          hash_key = "user_id"
          projection_type = "ALL"
        }
      ]
    }
  }
}

resource "aws_dynamodb_table" "this" {
  for_each = local.dynamodb_tables

  name           = "${var.project_name}-${each.key}"
  billing_mode   = "PAY_PER_REQUEST"
  hash_key       = each.value.hash_key
  range_key      = lookup(each.value, "range_key", null)

  dynamic "attribute" {
    for_each = each.value.attributes
    content {
      name = attribute.value.name
      type = attribute.value.type
    }
  }

  server_side_encryption {
    enabled     = true
    kms_key_arn = var.dynamodb_kms_key_arn
  }

  point_in_time_recovery {
    enabled = true
  }

  dynamic "ttl" {
    for_each = lookup(each.value, "ttl_attribute", null) != null ? [1] : []
    content {
      attribute_name = each.value.ttl_attribute
      enabled        = true
    }
  }

  dynamic "global_secondary_index" {
    for_each = lookup(each.value, "global_secondary_indexes", [])
    content {
      name     = global_secondary_index.value.name
      hash_key = global_secondary_index.value.hash_key
      range_key = lookup(global_secondary_index.value, "range_key", null)
      projection_type = lookup(global_secondary_index.value, "projection_type", "ALL")
    }
  }

  tags = var.tags
}