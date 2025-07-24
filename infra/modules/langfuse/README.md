# Langfuse Self-Hosted Observability Module

Self-hosted LLM tracing and observability platform for RiskAgent agents.

## Architecture

- **RDS PostgreSQL**: Database for trace storage (db.t3.micro, 20GB)
- **ECS Fargate**: Langfuse application (512 CPU, 1024 MB)
- **ALB Integration**: Accessible via `/langfuse` path on agents ALB
- **SSM Parameters**: Secure storage for API keys

## Deployment

### 1. Deploy Infrastructure

```bash
cd infra/environments/staging
bash terraform-wrapper.sh plan
bash terraform-wrapper.sh apply
```

### 2. Access Langfuse UI

```bash
# Get the URL
terraform output langfuse_url
# Example: http://<YOUR_INTERNAL_ALB_DNS>/langfuse
```

### 3. Initial Setup

1. Open Langfuse URL in browser
2. Create admin account (first user becomes admin)
3. Go to Settings → API Keys
4. Create a new API key pair

### 4. Store API Keys

```bash
# Store public key
aws ssm put-parameter \
  --name "/risk-agent/staging/langfuse/public-key" \
  --value "pk-lf-..." \
  --type String \
  --overwrite \
  --profile <YOUR_AWS_PROFILE>

# Store secret key
aws ssm put-parameter \
  --name "/risk-agent/staging/langfuse/secret-key" \
  --value "sk-lf-..." \
  --type SecureString \
  --overwrite \
  --profile <YOUR_AWS_PROFILE>
```

## Agent Integration

### Add to Agent Dependencies

```bash
# Add to dependencies/requirements.txt
langfuse==2.0.0
```

### Update Agent Code

```python
# agents/shared/observability.py
import os
from langfuse import Langfuse

def get_langfuse_client():
    return Langfuse(
        public_key=os.getenv("LANGFUSE_PUBLIC_KEY"),
        secret_key=os.getenv("LANGFUSE_SECRET_KEY"),
        host=os.getenv("LANGFUSE_HOST")
    )

# Decorator for tracing
def trace_agent_call(agent_name):
    def decorator(func):
        def wrapper(*args, **kwargs):
            client = get_langfuse_client()
            trace = client.trace(name=agent_name)
            span = trace.span(name=func.__name__)
            result = func(*args, **kwargs)
            span.end(output=str(result)[:1000])
            return result
        return wrapper
    return decorator
```

### Update ECS Task Environment Variables

Add to `infra/modules/ecs/main.tf`:

```hcl
{
  name  = "LANGFUSE_PUBLIC_KEY"
  value = data.aws_ssm_parameter.langfuse_public_key.value
},
{
  name  = "LANGFUSE_SECRET_KEY"
  value = data.aws_ssm_parameter.langfuse_secret_key.value
},
{
  name  = "LANGFUSE_HOST"
  value = var.langfuse_url
}
```

## Features

- **Trace Visualization**: See complete agent conversation flows
- **Token Tracking**: Monitor input/output tokens per call
- **Cost Analysis**: Calculate costs per project/user
- **Performance Metrics**: Latency p50/p95/p99
- **Error Tracking**: Identify failing agent calls
- **Prompt Versioning**: Compare different prompts

## Costs

- **RDS db.t3.micro**: ~$15/month
- **ECS Fargate (512/1024)**: ~$15/month
- **Total**: ~$30/month

## Monitoring

```bash
# Check service status
aws ecs describe-services \
  --cluster risk-agent-agents \
  --services risk-agent-langfuse \
  --profile <YOUR_AWS_PROFILE>

# View logs
aws logs tail /ecs/risk-agent-langfuse --follow --profile <YOUR_AWS_PROFILE>

# Check database
aws rds describe-db-instances \
  --db-instance-identifier risk-agent-langfuse-staging \
  --profile <YOUR_AWS_PROFILE>
```

## Troubleshooting

### Service won't start
- Check CloudWatch logs: `/ecs/risk-agent-langfuse`
- Verify database connectivity
- Check security group rules

### Can't access UI
- Verify ALB listener rule priority (100)
- Check path pattern: `/langfuse*`
- Ensure target group is healthy

### Database connection issues
- Verify DB security group allows ECS tasks
- Check DATABASE_URL format
- Ensure DB is in available state

## Cleanup

To remove Langfuse:

```bash
# Comment out module in main.tf
# Then apply
cd infra/environments/staging
bash terraform-wrapper.sh apply
```

## References

- [Langfuse Documentation](https://langfuse.com/docs)
- [Self-Hosting Guide](https://langfuse.com/docs/deployment/self-host)
- [Python SDK](https://langfuse.com/docs/sdk/python)
