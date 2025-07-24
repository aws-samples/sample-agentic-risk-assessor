# Step Functions State Machine for Service Controls Mapping with Dynamic Branching
# checkov:skip=CKV_AWS_284: X-Ray tracing not required for demo
# checkov:skip=CKV_AWS_285: Execution history logging not required for demo
resource "aws_sfn_state_machine" "service_controls_mapping" {
  name     = "${var.project_name}-service-controls-mapping"
  role_arn = var.step_functions_role_arn

  definition = jsonencode({
    Comment = "Process AWS services with dynamic control family branching"
    StartAt = "CheckProcessingType"
    States = {
      CheckProcessingType = {
        Type = "Choice"
        Choices = [
          {
            And = [
              { Variable = "$.services", IsPresent = true },
              { Variable = "$.services[0]", IsPresent = true }
            ]
            Next = "IndividualProcessing"
          }
        ]
        Default = "BulkProcessing"
      }
      IndividualProcessing = {
        Type = "Pass"
        Parameters = {
          "services.$" = "$.services"
          "framework.$" = "$.framework"
          batchSize = 3
          currentBatch = 0
        }
        Next = "ProcessBatch"
      }
      BulkProcessing = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-read_services"
          "Payload.$" = "$"
        }
        ResultPath = "$.servicesResult"
        Next = "InitializeBatching"
      }
      InitializeBatching = {
        Type = "Pass"
        Parameters = {
          "services.$" = "$.servicesResult.Payload.services"
          "framework.$" = "$.servicesResult.Payload.framework"
          batchSize = 3
          currentBatch = 0
        }
        Next = "ProcessBatch"
      }
      ProcessBatch = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-get_batch_services"
          Payload = {
            "services.$" = "$.services"
            "framework.$" = "$.framework"
            "batchSize.$" = "$.batchSize"
            "currentBatch.$" = "$.currentBatch"
          }
        }
        ResultPath = "$.batchInfo"
        Next = "ProcessCurrentBatch"
      }
      ProcessCurrentBatch = {
        Type = "Map"
        ItemsPath = "$.batchInfo.Payload.currentBatchServices"
        MaxConcurrency = 3
        Parameters = {
          "service.$" = "$$.Map.Item.Value"
          "framework.$" = "$.batchInfo.Payload.framework"
        }
        Iterator = {
          StartAt = "DiscoverFrameworkControls"
          States = {
            DiscoverFrameworkControls = {
              Type = "Task"
              Resource = "arn:aws:states:::lambda:invoke"
              Parameters = {
                FunctionName = "${var.project_name}-discover_framework_controls"
                Payload = {
                  "framework.$" = "$.framework"
                  "service.$" = "$.service"
                }
              }
              ResultPath = "$.frameworkResult"
              Next = "ParseFrameworkResult"
            }
            ParseFrameworkResult = {
              Type = "Pass"
              Parameters = {
                "service.$" = "$.service"
                "framework.$" = "$.framework"
                "parsedFrameworkBody.$" = "States.StringToJson($.frameworkResult.Payload.body)"
              }
              Next = "CheckS3Storage"
            }

            CheckS3Storage = {
              Type = "Choice"
              Choices = [
                {
                  Variable = "$.parsedFrameworkBody.stored_in_s3"
                  IsPresent = true
                  Next = "RetrieveFromS3"
                }
              ]
              Default = "ProcessControlFamilies"
            }

            RetrieveFromS3 = {
              Type = "Task"
              Resource = "arn:aws:states:::lambda:invoke"
              Parameters = {
                FunctionName = "${var.project_name}-retrieve_framework_s3_data"
                Payload = {
                  "s3_bucket.$" = "$.parsedFrameworkBody.s3_bucket"
                  "s3_key.$" = "$.parsedFrameworkBody.s3_key"
                }
              }
              ResultPath = "$.s3RetrievalResult"
              Next = "ParseS3Result"
            }

            ParseS3Result = {
              Type = "Pass"
              Parameters = {
                "service.$" = "$.service"
                "framework.$" = "$.framework"
                "parsedFrameworkBody.$" = "States.StringToJson($.s3RetrievalResult.Payload.body)"
              }
              Next = "ProcessControlFamilies"
            }

            ProcessControlFamilies = {
              Type = "Map"
              ItemsPath = "$.parsedFrameworkBody.control_families"
              MaxConcurrency = 3
              Parameters = {
                "service.$" = "$.service"
                "framework.$" = "$.framework"
                "control_family.$" = "$$.Map.Item.Value"
              }
              ResultPath = null
              Iterator = {
                StartAt = "DiscoverServiceCapabilities"
                States = {
                  DiscoverServiceCapabilities = {
                    Type = "Task"
                    Resource = "arn:aws:states:::lambda:invoke"
                    Parameters = {
                      FunctionName = "${var.project_name}-discover_service_capabilities"
                      Payload = {
                        "service.$" = "$.service"
                        "control_family.$" = "$.control_family.family_name"
                        "family_code.$" = "$.control_family.family_code"
                        "family_summary.$" = "$.control_family.family_summary"
                      }
                    }
                    ResultPath = "$.capabilitiesResult"
                    Next = "ParseCapabilitiesResult"
                  }
                  ParseCapabilitiesResult = {
                    Type = "Pass"
                    Parameters = {
                      "framework.$" = "$.framework"
                      "control_family.$" = "$.control_family"
                      "service.$" = "$.service"
                      "parsedCapabilitiesBody.$" = "States.StringToJson($.capabilitiesResult.Payload.body)"
                      "capabilitiesS3Data.$" = "$.capabilitiesResult.Payload"
                    }
                    Next = "ProcessIndividualControls"
                  }

                  ProcessIndividualControls = {
                    Type = "Map"
                    ItemsPath = "$.control_family.individual_controls"
                    MaxConcurrency = 3
                    Parameters = {
                      "service.$" = "$.service"
                      "framework.$" = "$.framework"
                      "control_id.$" = "$$.Map.Item.Value"
                      "control_family.$" = "$.capabilitiesS3Data"
                      "family_capabilities.$" = "$.capabilitiesS3Data"
                    }
                    ResultPath = null
                    Iterator = {
                      StartAt = "ResolveControlDetails"
                      States = {
                        ResolveControlDetails = {
                          Type = "Task"
                          Resource = "arn:aws:states:::lambda:invoke"
                          Parameters = {
                            FunctionName = "${var.project_name}-resolve_control_details"
                            Payload = {
                              "control_id.$" = "$.control_id"
                              "framework.$" = "$.framework"
                            }
                          }
                          ResultPath = "$.resolvedControl"
                          Retry = [
                            {
                              ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                              IntervalSeconds = 2
                              MaxAttempts = 2
                              BackoffRate = 2.0
                            }
                          ]
                          Next = "ParseResolvedControl"
                        }
                        ParseResolvedControl = {
                          Type = "Pass"
                          Parameters = {
                            "service.$" = "$.service"
                            "framework.$" = "$.framework"
                            "control_id.$" = "$.control_id"
                            "control_family.$" = "$.control_family"
                            "family_capabilities.$" = "$.family_capabilities"
                            "resolvedBody.$" = "States.StringToJson($.resolvedControl.Payload.body)"
                          }
                          Next = "ProcessSingleControl"
                        }
                        ProcessSingleControl = {
                          Type = "Task"
                          Resource = "arn:aws:states:::lambda:invoke"
                          Parameters = {
                            FunctionName = "${var.project_name}-process_single_control"
                            Payload = {
                              "service.$" = "$.service"
                              "framework.$" = "$.framework"
                              "control_id.$" = "$.control_id"
                              "control_name.$" = "$.resolvedBody.control_name"
                              "diagnostic_statement.$" = "$.resolvedBody.diagnostic_statement"
                              "control_family.$" = "$.control_family"
                              "family_capabilities.$" = "$.family_capabilities"
                            }
                          }
                          Retry = [
                            {
                              ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                              IntervalSeconds = 2
                              MaxAttempts = 3
                              BackoffRate = 2.0
                            }
                          ]
                          ResultPath = null
                          End = true
                        }
                      }
                    }
                    End = true
                  }
                }
              }
              ResultPath = "$.familyResults"
              Next = "MarkServiceComplete"
            }
            
            MarkServiceComplete = {
              Type = "Task"
              Resource = "arn:aws:states:::lambda:invoke"
              Parameters = {
                FunctionName = "${var.project_name}-mark_service_complete"
                Payload = {
                  "service.$" = "$.service"
                  "framework.$" = "$.framework"
                }
              }
              ResultPath = null
              Next = "GenerateControlReference"
            }
            GenerateControlReference = {
              Type = "Task"
              Resource = "arn:aws:states:::lambda:invoke"
              Parameters = {
                FunctionName = "${var.project_name}-generate_control_reference"
                Payload = {
                  "service.$" = "$.service"
                  "framework.$" = "$.framework"
                }
              }
              ResultPath = null
              End = true
            }
          }
        }
        ResultPath = "$.batchResults"
        Next = "WaitForBatchCompletion"
      }
      WaitForBatchCompletion = {
        Type = "Wait"
        Seconds = 30
        Next = "CheckBatchCompletion"
      }
      CheckBatchCompletion = {
        Type = "Task"
        Resource = "arn:aws:states:::lambda:invoke"
        Parameters = {
          FunctionName = "${var.project_name}-check_batch_completion"
          Payload = {
            "services.$" = "$.batchInfo.Payload.currentBatchServices"
            "framework.$" = "$.batchInfo.Payload.framework"
          }
        }
        ResultPath = "$.completionCheck"
        Next = "IsBatchComplete"
      }
      IsBatchComplete = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.completionCheck.Payload.batchStatus"
            StringEquals = "COMPLETE"
            Next = "HasMoreBatches"
          }
        ]
        Default = "WaitForBatchCompletion"
      }
      HasMoreBatches = {
        Type = "Choice"
        Choices = [
          {
            Variable = "$.batchInfo.Payload.hasMoreBatches"
            BooleanEquals = true
            Next = "IncrementBatch"
          }
        ]
        Default = "AllBatchesComplete"
      }
      IncrementBatch = {
        Type = "Pass"
        Parameters = {
          "services.$" = "$.batchInfo.Payload.services"
          "framework.$" = "$.batchInfo.Payload.framework"
          "batchSize.$" = "$.batchInfo.Payload.batchSize"
          "currentBatch.$" = "States.MathAdd($.batchInfo.Payload.currentBatch, 1)"
        }
        Next = "ProcessBatch"
      }
      AllBatchesComplete = {
        Type = "Succeed"
      }
    }
  })

  tags = var.tags
}

# Step Functions State Machine for Node Controls Mapping
# checkov:skip=CKV_AWS_284: X-Ray tracing not required for demo
# checkov:skip=CKV_AWS_285: Execution history logging not required for demo
resource "aws_sfn_state_machine" "node_controls_mapping" {
  name     = "${var.project_name}-node-controls-mapping"
  role_arn = var.step_functions_role_arn

  definition = jsonencode({
    Comment = "Process node control mappings individually"
    StartAt = "ProcessNodes"
    States = {
      ProcessNodes = {
        Type = "Map"
        ItemsPath = "$.nodes"
        MaxConcurrency = 1
        Iterator = {
          StartAt = "ProcessSingleNode"
          States = {
            ProcessSingleNode = {
              Type = "Task"
              Resource = "arn:aws:states:::lambda:invoke"
              Parameters = {
                FunctionName = "${var.project_name}-process_node_controls"
                Payload = {
                  "project_id.$" = "$$.Execution.Input.project_id"
                  "framework.$" = "$$.Execution.Input.framework"
                  "node.$" = "$"
                }
              }
              Retry = [
                {
                  ErrorEquals = ["Lambda.ServiceException", "Lambda.AWSLambdaException", "Lambda.SdkClientException"]
                  IntervalSeconds = 2
                  MaxAttempts = 3
                  BackoffRate = 2.0
                }
              ]
              Catch = [
                {
                  ErrorEquals = ["States.ALL"]
                  Next = "NodeProcessingFailed"
                  ResultPath = "$.error"
                }
              ]
              End = true
            }
            NodeProcessingFailed = {
              Type = "Pass"
              Result = {
                status = "failed"
              }
              End = true
            }
          }
        }
        Next = "ProcessingComplete"
      }
      ProcessingComplete = {
        Type = "Pass"
        Result = {
          status = "completed"
          message = "All nodes processed"
        }
        End = true
      }
    }
  })

  tags = var.tags
}