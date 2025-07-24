# Financial Services Sample Documents

This directory contains comprehensive sample documents for testing the document processing and extraction capabilities of the Organization Profile Agent for the Financial Services industry.

## Documents

### 1. security_policy.md
**Type:** Information Security Policy  
**Format:** Markdown (can be converted to PDF)  
**Size:** ~15,000 words  
**Content Coverage:**
- Organization information (name, industry, size, regions)
- Regulatory compliance (PCI DSS, SOX, GLBA, GDPR, CCPA, FINRA)
- Risk profile and threat landscape
- Security maturity assessment (AWS Security Pillars)
- Technology environment (AWS infrastructure)
- Business context and stakeholder requirements
- Third-party risk management
- Security governance structure

**Key Extractable Fields:**
- Organization Name: Global Financial Services Corporation
- Industry: Financial Services
- Size: Enterprise (5,000+ employees)
- Primary Regions: North America, Europe, APAC
- Primary Regulations: PCI DSS v4.0, SOX, GLBA, GDPR, CCPA, FINRA
- Compliance Frameworks: NIST CSF, ISO 27001:2022, CIS Controls v8
- Cloud Platforms: AWS (80%), Azure (20%)
- RTO: 15 minutes (trading), 1 hour (customer portal)
- RPO: 0 seconds (trading), 5 minutes (customer portal)
- Security Tools: Okta, CyberArk, Splunk, CrowdStrike, AWS services
- Risk Tolerance: Low to Moderate
- Annual Security Budget: $15 million

### 2. compliance_report.md
**Type:** Annual Compliance Assessment Report  
**Format:** Markdown (can be converted to PDF)  
**Size:** ~12,000 words  
**Content Coverage:**
- PCI DSS v4.0 compliance assessment (all 12 requirements)
- SOX IT controls assessment
- GDPR compliance status
- ISO 27001:2022 certification
- Additional regulatory compliance (GLBA, CCPA, FINRA, FFIEC)
- Risk assessment summary
- Compliance metrics and KPIs

**Key Extractable Fields:**
- PCI DSS Status: Compliant (Level 1 Merchant)
- SOX Status: Effective (no material weaknesses)
- ISO 27001 Status: Certified (valid through Jan 2026)
- GDPR Status: Compliant
- Transaction Volume: 12.5 million annually
- Data Subject Requests: 145 access, 23 rectification, 12 erasure
- Security Incidents: 12 (0 breaches)
- Compliance Rate: 98.5%

### 3. audit_findings.md
**Type:** Internal Audit Findings Report  
**Format:** Markdown (can be converted to PDF)  
**Size:** ~8,000 words  
**Content Coverage:**
- Q4 2024 internal security audit results
- High/Medium/Low risk findings
- Detailed findings with recommendations
- Management responses and action plans
- Positive findings and strengths
- Audit opinion and follow-up plans

**Key Extractable Fields:**
- Overall Rating: Satisfactory
- High-Risk Findings: 0
- Medium-Risk Findings: 3 (MFA enforcement, vulnerability patching, container monitoring)
- Low-Risk Findings: 5
- Audit Scope: AWS infrastructure, applications, access management, incident response
- Follow-up Audit: Q2 2025

## Usage

These documents are designed to test the PageIndex document processing system's ability to:

1. **Extract structured information** from unstructured documents
2. **Identify key fields** relevant to organization profiles
3. **Handle industry-specific terminology** (PCI DSS, SOX, FINRA, etc.)
4. **Process multi-page documents** with complex hierarchies
5. **Generate accurate citations** with page numbers and sections
6. **Detect and resolve conflicts** across multiple documents
7. **Pre-populate profile fields** with high confidence

## Expected Profile Output

See `expected_profile.json` for the ground truth profile that should be extracted from these documents.

## Testing Scenarios

### Scenario 1: Single Document Upload
Upload `security_policy.md` and verify extraction of:
- Basic organization information
- Regulatory requirements
- Security maturity levels
- Technology environment

### Scenario 2: Multiple Document Upload
Upload all three documents and verify:
- Information synthesis across documents
- Conflict detection (if any)
- Citation accuracy
- Completeness of extracted profile

### Scenario 3: Incremental Upload
Upload documents one at a time and verify:
- Progressive profile completion
- No duplicate information
- Proper source attribution

## Conversion to PDF/DOCX

To convert these markdown files to PDF or DOCX format:

```bash
# Using pandoc
pandoc security_policy.md -o security_policy.pdf
pandoc compliance_report.md -o compliance_report.pdf
pandoc audit_findings.md -o audit_findings.pdf

# Or to DOCX
pandoc security_policy.md -o security_policy.docx
pandoc compliance_report.md -o compliance_report.docx
pandoc audit_findings.md -o audit_findings.docx
```

## Document Characteristics

- **Realistic content**: Based on actual financial services security practices
- **Comprehensive coverage**: Addresses all profile fields for financial industry
- **Industry-specific**: Uses proper terminology and regulatory references
- **Well-structured**: Clear hierarchies for PageIndex tree generation
- **Cross-referenced**: Information appears in multiple documents for testing synthesis

## Validation Criteria

When testing with these documents, the system should achieve:
- **Extraction Accuracy**: >95% for clearly stated facts
- **Citation Accuracy**: 100% for page numbers and sections
- **Confidence Scores**: >0.8 for primary fields, >0.6 for derived fields
- **Processing Time**: <60 seconds per document
- **Conflict Detection**: Identify any contradictory information

---

**Last Updated:** January 2025  
**Maintained by:** Organization Profile Agent Development Team
