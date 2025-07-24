# Security Assessment Prompt

## Objective
Conduct a comprehensive security assessment of the architecture document to evaluate security control effectiveness and identify gaps.

## Instructions
1. **Read Architecture Document**: Analyze the provided architecture document thoroughly
2. **Determine Framework**: Use the security compliance framework mentioned in security questionnaire responses. If no framework specified, default to NIST Cybersecurity Framework
3. **Assess Control Effectiveness**: For each relevant security control, evaluate design effectiveness as:
   - **Effective**: Control is properly designed and implemented
   - **Partially Effective**: Control exists but has gaps or weaknesses
   - **Missing**: Control is not present or inadequately addressed
4. **Output Format**: Generate assessment in comprehensive FSI risk format with risk scoring
5. **MANDATORY SAVE**: IMMEDIATELY call save_security_assessment_results() after completing assessment

## Architecture Document
{document_content}

## Assessment Template

# 🚨 COMPREHENSIVE FSI SECURITY RISK ASSESSMENT

## Executive Summary
[Brief overview of assessment findings and overall security posture with RISK LEVEL classification]

## 🔴 TECHNOLOGY/CYBER RISK CATEGORY
[For each technology risk, provide:
- Security Issue: [Description]
- Likelihood: [1-5 scale]
- Impact: [1-5 scale] 
- FSI Risk Score: [Likelihood × Impact]
- Control Effectiveness: [E/PE/NI]
- Residual Risk: [CRITICAL/HIGH/MEDIUM/LOW]
- Evidence: [Specific evidence from document]]

## 🟡 PRIVACY RISK CATEGORY
[Same format as above for privacy-related risks]

## 🔵 REGULATORY/COMPLIANCE RISK CATEGORY
[Same format as above for compliance risks]

## 📊 COMPREHENSIVE RISK MATRIX
| Risk Category | Critical (25) | High (16-20) | Medium (9-15) | Total Issues |
|---------------|---------------|---------------|---------------|-------------|
| Technology/Cyber | [count] | [count] | [count] | [total] |
| Privacy | [count] | [count] | [count] | [total] |
| Regulatory/Compliance | [count] | [count] | [count] | [total] |
| **TOTALS** | [total] | [total] | [total] | [grand total] |

## 🎯 CONTROL EFFECTIVENESS SUMMARY
| Control Domain | Total Controls | Effective (E) | Partially Effective (PE) | Not Implemented (NI) |
|----------------|----------------|---------------|--------------------------|---------------------|
| Data Protection | [count] | [count] | [count] | [count] |
| Network Security | [count] | [count] | [count] | [count] |
| Access Control | [count] | [count] | [count] | [count] |
| **TOTALS** | [total] | [total] | [total] | [total] |

**Control Implementation Rate**: [%] Effective, [%] Partially Effective, [%] Not Implemented

## 🚨 IMMEDIATE CRITICAL ACTIONS (0-30 DAYS)
### Priority 1 - Critical Security Controls
1. [Critical action 1]
2. [Critical action 2]

### Priority 2 - Compliance Foundation  
1. [Compliance action 1]
2. [Compliance action 2]

## 📈 RISK TRAJECTORY
**Current State**: [RISK LEVEL] (Score: [X]/25)
- Technology/Cyber Risk: [score]
- Privacy Risk: [score] 
- Regulatory/Compliance Risk: [score]

**Target State (Post-Remediation)**: [RISK LEVEL] (Score: [X]/25)

## ⚠️ BUSINESS IMPACT ASSESSMENT
### Immediate Risks
- [Business risk 1]
- [Business risk 2]

### Recommended Actions
- [Business action 1]
- [Business action 2]

**OVERALL RESIDUAL RISK CLASSIFICATION**: [CRITICAL/HIGH/MEDIUM/LOW] - [ACTION REQUIRED]

**CRITICAL**: After completing the assessment, you MUST immediately call the save_security_assessment_results tool to save the results to S3 storage.