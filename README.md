# RiskAgent — Agentic Risk Assessment for Financial Services

A multi-agent AI system that performs shift-left security and risk assessment for AWS architectures. Built with [Strands Agents](https://github.com/strands-agents/strands-agents-python), Amazon Bedrock, and the Agent-to-Agent (A2A) protocol.

Each agent mirrors a role in the financial services three lines of defense model — an architect who thinks like a Head of Technology, a security specialist who thinks like a CISO, and a risk assessor who speaks the language of the CRO.

## Architecture

```
┌────────────────────────────────────────────────────────────────────────────────────┐
│                              Amazon Bedrock                                         │
│                    Claude Sonnet 4 · Knowledge Bases (RAG)                          │
└──────────────────────────────────┬─────────────────────────────────────────────────┘
                                   │
┌──────────────────────────────────┼─────────────────────────────────────────────────┐
│  ECS / Fargate                   │                                                 │
│                                  │                                                 │
│   ┌──────────────┐  ┌───────────┴────────┐  ┌──────────────┐  ┌──────────────┐   │
│   │  Architect   │  │ Security Architect  │  │    Risk      │  │   Auditor    │   │
│   │  (9002)      │  │ (9004)             │  │  Assessment  │  │   (9006)     │   │
│   │              │  │                    │  │  (9005)      │  │              │   │
│   │ 1st Line     │  │ 1st Line           │  │ 2nd Line     │  │ 3rd Line     │   │
│   │ Technology   │  │ InfoSec            │  │ Tech Risk    │  │ Audit        │   │
│   └──────────────┘  └────────────────────┘  └──────────────┘  └──────────────┘   │
│                                                                                    │
│   ┌─────────────────────┐                           A2A Protocol                   │
│   │ Organization Profile │◄─────── (agent-to-agent communication) ────────────────│
│   │ (9007)               │                                                         │
│   └─────────────────────┘                                                          │
└──────────────────────────────────┬─────────────────────────────────────────────────┘
                                   │ Internal ALB
                                   │
┌────────┐     ┌────────────┐      │      ┌─────────────┐     ┌───────────────────┐
│  User  │────▶│ CloudFront │──────┼─────▶│  Frontend   │     │  Lambda (68 tools)│
└────────┘     │ + WAF      │      │      │  Next.js    │     └────────┬──────────┘
               └─────┬──────┘      │      └─────────────┘              │
                     │             │                                    │
                     │             │      ┌─────────────┐    ┌─────────┼─────────┐
                     └─────────────┼─────▶│ API Gateway │    │         │         │
                                   │      └──────┬──────┘    ▼         ▼         ▼
                                   │             │       DynamoDB      S3    OpenSearch
                                   │             │                          Serverless
                                   │             └──────────────────┐
                                   │                                ▼
                                   │                          Lambda Functions
                                   │
                              Amazon Cognito
                         JWT + OAuth (agent auth)
```

### Agents

| Agent | Defense Line | Function |
|-------|-------------|----------|
| **Architect** | 1st — Technology | Analyzes architecture diagrams, identifies AWS components and data flows |
| **Security Architect** | 1st — InfoSec | Maps security controls from NIST 800-53, PCI-DSS, CPS 234, CRI to architecture components |
| **Risk Assessment** | 1st/2nd — Tech Risk | Quantifies risk with 5×5 matrices, generates FSI risk assessments |
| **Auditor** | 3rd — Internal Audit | Validates assessment completeness, consistency, and traceability |
| **Organization Profile** | Context | Captures organization context (industry, jurisdiction, risk appetite) to tailor assessments |

### Infrastructure

- **Compute**: Amazon ECS/Fargate (2 clusters: agents + frontend)
- **AI/ML**: Amazon Bedrock (Claude Sonnet 4), Bedrock Knowledge Bases with OpenSearch Serverless
- **Networking**: VPC, Application Load Balancers (internal + external), CloudFront
- **Auth**: Amazon Cognito (with optional Federated SSO)
- **Storage**: DynamoDB, S3
- **Security**: Per-agent IAM roles, KMS encryption, WAF
- **IaC**: Terraform (modular)

## Getting Started — End-to-End Process

To run a full risk assessment, follow this sequence:

```
1. Create Organization Profile (recommended)
       ↓
2. Create Project (upload design document)
       ↓
3. Review extracted architecture (nodes & flows)
       ↓
4. Run Risk Assessment
       ↓
5. Review structured FSI risk report
```

**Step 1** is recommended but not mandatory. An organization profile (industry, jurisdiction, risk appetite, frameworks) tailors the risk assessment to your institution's specific context. Without it, the assessment uses generic FSI defaults.

**Step 2** requires a design document containing an architecture diagram. Accepted formats:
- `.docx` — Word document with an embedded architecture diagram (preferred)
- `.png`, `.jpg`, `.svg` — Standalone architecture diagram image

**Step 3** is where you verify the Architect agent correctly identified all AWS services and data flows from your diagram. You can manually edit nodes and flows if needed.

**Step 4** is where the agents do the work — produces the full FSI report with 5×5 matrices, regulatory exposure, and recommendations.

**Optional — Security Control Mapping**: Before running a risk assessment, you can run control mapping to assign framework controls (NIST 800-53, PCI-DSS, CPS 234, CRI) to each AWS service. If control mapping has been completed, the risk assessment uses it as input, significantly improving the quality and traceability of security findings.

## Limitations

- **One diagram per document**: The design document should contain a single architecture diagram showing all nodes and data flows. Multiple diagrams in one document are not supported — only the first/primary image is analyzed.
- **AWS services only**: The Architect agent identifies AWS services. Non-AWS components (on-premises, third-party SaaS) appear as generic nodes without control mapping.
- **Framework coverage**: RAG-based control mapping requires framework documents to be uploaded to the Knowledge Base. Only indexed frameworks return authoritative references.
- **Assessment scope**: Each project represents one architecture. For multi-system assessments, create separate projects and link them to the same organization profile.
- **Agent context window**: Very large architectures (50+ nodes) may require multiple interactions. The agents use sliding-window conversation management.

## Main Flows

### 1. Organization Profile

An organization profile captures your institution's context — industry, size, jurisdictions, regulatory frameworks, risk appetite, security maturity, and crown jewels. This context tailors all subsequent assessments to your specific environment.

**How to use:**
1. Navigate to **Organization Profiles** → **New Profile**
2. Upload supporting documents (security policies, audit findings, compliance reports) — the agent extracts relevant context automatically
3. The agent asks clarifying questions via chat to build a comprehensive profile
4. Save the profile and link it to projects

### 2. Security Control Mapping

Control mapping assigns security controls from regulatory frameworks (NIST 800-53, PCI-DSS, CPS 234, CRI) to each AWS service in your architecture. It uses RAG against indexed framework documents for authoritative references.

**How to use:**
1. Open a project that has a completed architecture analysis
2. Navigate to the **Control Mapping** view
3. Select a framework (NIST, PCI-DSS, etc.)
4. The Security Architect agent maps controls to each service using Bedrock Knowledge Bases
5. Review and approve control assignments per node

### 3. Project Creation

A project represents an AWS architecture to be assessed. You provide a solution design document (Word or image) and the system extracts the architecture automatically.

**How to use:**
1. Navigate to **Projects** → **New Project**
2. Enter project name and description
3. Upload an architecture diagram (.docx with embedded diagram, or image)
4. The Architect agent analyzes the diagram, extracting nodes (AWS services) and data flows
5. Review the extracted architecture — edit nodes/flows if needed

### 4. Risk Assessment

The risk assessment workflow runs multiple agents in sequence to produce a structured FSI risk report with full traceability from business risk through security controls to architecture components.

**How to use:**
1. Open a project with a completed architecture analysis
2. Click **Run Risk Assessment**
3. The system runs the full workflow:
   - Risk Assessment agent gathers architecture and security context via A2A
   - Generates risk scenarios with 5×5 likelihood/impact matrices
   - Maps each risk to regulatory exposure (DORA, CRI, NIST CSF)
   - Auditor agent validates the output
4. View the structured assessment with risk categories, scores, and recommendations

### 5. Agent Chat

Each agent can be interacted with directly via chat. Ask questions, request analysis, or get explanations in the language of that agent's domain.

**Examples:**
- Ask the **Architect** agent: "What are the single points of failure in this architecture?"
- Ask the **Security Architect** agent: "Which controls are missing for the payment API?"
- Ask the **Risk Assessment** agent: "What is the regulatory exposure for this project under DORA?"

## Deployment

For complete deployment instructions, see **[DEPLOYMENT.md](DEPLOYMENT.md)**.

Quick overview:
```bash
# 1. Bootstrap terraform backend
# 2. Build Lambda packages
# 3. Deploy infrastructure (terraform)
# 4. Deploy Lambda code
# 5. Deploy agents (ECS)
# 6. Deploy frontend
# 7. Create first user
# 8. Upload framework docs to Knowledge Base
```

## Technology Stack

- **Agent Framework**: [Strands Agents](https://github.com/strands-agents/strands-agents-python) 1.4.0
- **Agent Communication**: A2A protocol (Agent-to-Agent)
- **Foundation Model**: Anthropic Claude Sonnet 4 via Amazon Bedrock
- **RAG**: Amazon Bedrock Knowledge Bases + OpenSearch Serverless
- **Frontend**: React.js / Next.js
- **Infrastructure**: Terraform, AWS ECS/Fargate, DynamoDB, S3, CloudFront, Cognito
- **Auth**: JWT (Cognito) + OAuth client credentials for inter-agent auth

## License

This project is licensed under the MIT-0 License. See the [LICENSE](LICENSE) file.
