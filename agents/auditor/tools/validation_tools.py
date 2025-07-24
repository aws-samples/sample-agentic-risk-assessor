"""
Auditor Agent Validation Tools
Comprehensive validation for all agent outputs
"""

import re
from typing import Dict, List, Optional
from strands.tools import tool

@tool
def validate_risk_assessment(assessment_content: str) -> Dict[str, any]:
    """
    Validates FSI risk assessment for completeness and consistency.
    
    Args:
        assessment_content: Complete risk assessment markdown content
        
    Returns:
        Dict with validation results and specific issues found
    """
    
    validation_results = {
        "status": "PENDING",
        "is_valid": False,
        "critical_issues": [],
        "warnings": [],
        "summary": ""
    }
    
    try:
        # Extract risk counts from executive summary
        exec_counts = _extract_executive_summary_counts(assessment_content)
        
        # Count detailed risk scenarios
        detailed_scenarios = _count_detailed_scenarios(assessment_content)
        
        # Count risks in summary matrix
        matrix_risks = _count_matrix_risks(assessment_content)
        
        # Validate risk count consistency
        count_issues = _validate_risk_counts(exec_counts, detailed_scenarios, matrix_risks)
        
        # Check scenario completeness
        completeness_issues = _validate_scenario_completeness(assessment_content, detailed_scenarios)
        
        # Validate business language
        language_issues = _validate_business_language(assessment_content)
        
        # Check technical evidence
        evidence_issues = _validate_technical_evidence(assessment_content, detailed_scenarios)
        
        # Check risk categorization (Solution vs Enterprise)
        categorization_issues = _validate_risk_categorization(assessment_content)
        
        # Check traceability (risk → component → control → framework)
        traceability_issues = _validate_traceability(assessment_content)
        
        # Check timeline factuality (no arbitrary timelines)
        timeline_issues = _validate_timeline_factuality(assessment_content)
        
        # Check framework citation specificity
        citation_issues = _validate_framework_citations(assessment_content)
        
        # Compile all issues
        all_critical = []
        all_warnings = []
        
        for issue_list in [count_issues, completeness_issues, evidence_issues, categorization_issues, traceability_issues]:
            all_critical.extend([i for i in issue_list if i.get("severity") == "critical"])
            all_warnings.extend([i for i in issue_list if i.get("severity") == "warning"])
        
        all_warnings.extend(language_issues)
        all_warnings.extend(timeline_issues)
        all_warnings.extend(citation_issues)
        
        validation_results["critical_issues"] = all_critical
        validation_results["warnings"] = all_warnings
        validation_results["is_valid"] = len(all_critical) == 0
        
        # Set status and summary
        if len(all_critical) > 0:
            validation_results["status"] = "REJECTED"
            validation_results["summary"] = f"Critical validation failures found: {len(all_critical)} issues must be resolved"
        elif len(all_warnings) > 0:
            validation_results["status"] = "CONDITIONAL"
            validation_results["summary"] = f"Assessment acceptable with {len(all_warnings)} minor improvements recommended"
        else:
            validation_results["status"] = "APPROVED"
            validation_results["summary"] = "Assessment meets all quality standards"
        
        return validation_results
        
    except Exception as e:
        validation_results["status"] = "REJECTED"
        validation_results["critical_issues"].append({
            "type": "validation_error",
            "message": f"Validation process failed: {str(e)}"
        })
        return validation_results

def _extract_executive_summary_counts(content: str) -> Dict[str, int]:
    """Extract risk counts from executive summary"""
    counts = {}
    patterns = {
        "total": r"Total Risks Identified:\*\*\s*(\d+)",
        "critical": r"Critical Risks:\*\*\s*(\d+)",
        "high": r"High Risks:\*\*\s*(\d+)",
        "medium": r"Medium Risks:\*\*\s*(\d+)",
        "low": r"Low Risks:\*\*\s*(\d+)"
    }
    
    for risk_type, pattern in patterns.items():
        match = re.search(pattern, content, re.IGNORECASE)
        counts[risk_type] = int(match.group(1)) if match else 0
    
    return counts

def _count_detailed_scenarios(content: str) -> int:
    """Count detailed risk scenarios"""
    scenario_pattern = r"#### Risk Scenario \d+:"
    return len(re.findall(scenario_pattern, content))

def _count_matrix_risks(content: str) -> int:
    """Count risks in summary matrix"""
    matrix_section = re.search(r"### 2\.2 Risk Summary Matrix.*?(?=###|\Z)", content, re.DOTALL)
    if not matrix_section:
        return 0
    
    matrix_content = matrix_section.group(0)
    rows = [row for row in matrix_content.split('\n') if row.startswith('|') and not row.startswith('|---')]
    return max(0, len(rows) - 1)  # Subtract header row

def _validate_risk_counts(exec_counts: Dict, detailed_count: int, matrix_count: int) -> List[Dict]:
    """Validate consistency between risk counts"""
    issues = []
    total_claimed = exec_counts.get("total", 0)
    
    if total_claimed != detailed_count:
        issues.append({
            "type": "count_mismatch",
            "severity": "critical",
            "message": f"Executive summary claims {total_claimed} risks but only {detailed_count} detailed scenarios found"
        })
    
    if total_claimed != matrix_count:
        issues.append({
            "type": "matrix_mismatch", 
            "severity": "critical",
            "message": f"Executive summary claims {total_claimed} risks but risk matrix has {matrix_count} rows"
        })
    
    if detailed_count != matrix_count:
        issues.append({
            "type": "scenario_matrix_mismatch",
            "severity": "critical", 
            "message": f"Found {detailed_count} detailed scenarios but {matrix_count} risks in matrix"
        })
    
    return issues

def _validate_scenario_completeness(content: str, expected_count: int) -> List[Dict]:
    """Validate each risk scenario is complete"""
    issues = []
    required_elements = [
        "Risk Categories:",
        "Business Description:",
        "Technical Evidence:",
        "Risk Assessment Matrix:",
        "Business Impact Analysis:",
        "Risk Management Strategy:"
    ]
    
    scenarios = re.findall(r"#### Risk Scenario \d+:.*?(?=#### Risk Scenario \d+:|### 2\.2 Risk Summary Matrix|\Z)", 
                          content, re.DOTALL)
    
    for i, scenario in enumerate(scenarios, 1):
        missing_elements = [elem for elem in required_elements if elem not in scenario]
        if missing_elements:
            issues.append({
                "type": "incomplete_scenario",
                "severity": "critical",
                "message": f"Risk Scenario {i} missing: {', '.join(missing_elements)}"
            })
    
    return issues

def _validate_business_language(content: str) -> List[Dict]:
    """Validate appropriate business language usage"""
    issues = []
    technical_terms = ["VPC", "ECS", "Lambda", "DynamoDB", "CloudWatch", "IAM", "S3"]
    business_sections = ["Executive Summary", "Business Context", "Business Impact Analysis"]
    
    for section in business_sections:
        section_match = re.search(f"### {section}.*?(?=###|\Z)", content, re.DOTALL)
        if section_match:
            section_content = section_match.group(0)
            found_terms = [term for term in technical_terms if term in section_content]
            if found_terms:
                issues.append({
                    "type": "technical_language",
                    "severity": "warning", 
                    "message": f"Technical terms in {section}: {', '.join(found_terms)}"
                })
    
    return issues

def _validate_technical_evidence(content: str, scenario_count: int) -> List[Dict]:
    """Validate technical evidence inclusion"""
    issues = []
    evidence_count = len(re.findall(r"\*\*Technical Evidence:\*\*", content))
    
    if evidence_count != scenario_count:
        issues.append({
            "type": "missing_technical_evidence",
            "severity": "critical",
            "message": f"Found {evidence_count} technical evidence sections but {scenario_count} risk scenarios"
        })
    
    return issues

@tool
def validate_architecture_review(review_content: str) -> Dict[str, any]:
    """
    Validates architecture review for completeness and quality.
    
    Args:
        review_content: Complete architecture review markdown content
        
    Returns:
        Dict with validation results
    """
    
    validation_results = {
        "status": "PENDING",
        "is_valid": False,
        "critical_issues": [],
        "warnings": [],
        "summary": ""
    }
    
    try:
        issues = []
        
        # Check for required sections
        required_sections = [
            "Business Overview",
            "Technical Architecture", 
            "Component Details",
            "Security Features",
            "Deployment Model",
            "Operational Readiness"
        ]
        
        for section in required_sections:
            if section not in review_content:
                issues.append({
                    "type": "missing_section",
                    "severity": "critical",
                    "message": f"Missing required section: {section}"
                })
        
        # Check for overall score
        if "Overall Score:" not in review_content and "Total Score:" not in review_content:
            issues.append({
                "type": "missing_score",
                "severity": "critical", 
                "message": "Missing overall architecture score"
            })
        
        # Check for recommendations
        if "Recommendation" not in review_content:
            issues.append({
                "type": "missing_recommendations",
                "severity": "warning",
                "message": "Architecture review should include recommendations"
            })
        
        validation_results["critical_issues"] = [i for i in issues if i.get("severity") == "critical"]
        validation_results["warnings"] = [i for i in issues if i.get("severity") == "warning"]
        validation_results["is_valid"] = len(validation_results["critical_issues"]) == 0
        
        # Set status
        if len(validation_results["critical_issues"]) > 0:
            validation_results["status"] = "REJECTED"
            validation_results["summary"] = "Architecture review missing critical components"
        elif len(validation_results["warnings"]) > 0:
            validation_results["status"] = "CONDITIONAL"
            validation_results["summary"] = "Architecture review acceptable with minor improvements"
        else:
            validation_results["status"] = "APPROVED"
            validation_results["summary"] = "Architecture review meets quality standards"
        
        return validation_results
        
    except Exception as e:
        validation_results["status"] = "REJECTED"
        validation_results["critical_issues"].append({
            "type": "validation_error",
            "message": f"Architecture validation failed: {str(e)}"
        })
        return validation_results

@tool
def validate_security_assessment(assessment_content: str) -> Dict[str, any]:
    """
    Validates security assessment for completeness and compliance.
    
    Args:
        assessment_content: Complete security assessment content
        
    Returns:
        Dict with validation results
    """
    
    validation_results = {
        "status": "PENDING",
        "is_valid": False,
        "critical_issues": [],
        "warnings": [],
        "summary": ""
    }
    
    try:
        issues = []
        
        # Check for security control coverage
        security_areas = ["Access Controls", "Network Security", "Data Protection", "Audit Logging"]
        
        for area in security_areas:
            if area not in assessment_content:
                issues.append({
                    "type": "missing_security_area",
                    "severity": "warning",
                    "message": f"Security area not covered: {area}"
                })
        
        # Check for compliance mapping
        if "compliance" not in assessment_content.lower():
            issues.append({
                "type": "missing_compliance",
                "severity": "warning",
                "message": "Security assessment should include compliance considerations"
            })
        
        validation_results["critical_issues"] = [i for i in issues if i.get("severity") == "critical"]
        validation_results["warnings"] = [i for i in issues if i.get("severity") == "warning"]
        validation_results["is_valid"] = len(validation_results["critical_issues"]) == 0
        
        # Set status
        if len(validation_results["critical_issues"]) > 0:
            validation_results["status"] = "REJECTED"
            validation_results["summary"] = "Security assessment has critical gaps"
        elif len(validation_results["warnings"]) > 0:
            validation_results["status"] = "CONDITIONAL"
            validation_results["summary"] = "Security assessment acceptable with improvements"
        else:
            validation_results["status"] = "APPROVED"
            validation_results["summary"] = "Security assessment meets standards"
        
        return validation_results
        
    except Exception as e:
        validation_results["status"] = "REJECTED"
        validation_results["critical_issues"].append({
            "type": "validation_error",
            "message": f"Security validation failed: {str(e)}"
        })
        return validation_results

@tool 
def generate_audit_report(validation_results: Dict) -> str:
    """Generate detailed audit report from validation results"""
    
    status = validation_results.get("status", "UNKNOWN")
    critical_issues = validation_results.get("critical_issues", [])
    warnings = validation_results.get("warnings", [])
    summary = validation_results.get("summary", "No summary available")
    
    if status == "APPROVED":
        report = f"✅ **APPROVED** - {summary}\n\n"
    elif status == "REJECTED":
        report = f"❌ **REJECTED** - {summary}\n\n"
    else:
        report = f"⚠️ **CONDITIONAL APPROVAL** - {summary}\n\n"
    
    if critical_issues:
        report += "**Critical Issues (Must Fix):**\n"
        for issue in critical_issues:
            report += f"- {issue.get('message', 'Unknown issue')}\n"
        report += "\n"
    
    if warnings:
        report += "**Warnings (Should Fix):**\n"
        for warning in warnings:
            report += f"- {warning.get('message', 'Unknown warning')}\n"
        report += "\n"
    
    return report


def _validate_risk_categorization(content: str) -> List[Dict]:
    """Validate that risks are categorized as SOLUTION or ENTERPRISE"""
    issues = []
    
    has_solution_label = bool(re.search(r'\[SOLUTION\]', content, re.IGNORECASE))
    has_enterprise_label = bool(re.search(r'\[ENTERPRISE\]', content, re.IGNORECASE))
    has_separation = bool(re.search(r'Solution.Introduced|Inherited.*Enterprise|Enterprise.*Risk', content, re.IGNORECASE))
    
    if not (has_solution_label or has_enterprise_label or has_separation):
        issues.append({
            "type": "missing_categorization",
            "severity": "warning",
            "message": "Risks are not categorized as [SOLUTION] vs [ENTERPRISE]. Assessment should clearly separate solution-introduced risks from inherited enterprise risks."
        })
    
    return issues


def _validate_traceability(content: str) -> List[Dict]:
    """Validate that risks are traceable to components and controls"""
    issues = []
    
    # Check for component references in risk scenarios
    has_component_refs = bool(re.search(r'node\d+|component|service|Lambda|S3|DynamoDB|ECS|API Gateway|Kinesis|SageMaker', content))
    has_control_refs = bool(re.search(r'[A-Z]{2}-\d+|CPS\s*\d+|PCI.DSS|NIST|DORA|CRI', content))
    
    if not has_component_refs:
        issues.append({
            "type": "missing_traceability",
            "severity": "critical",
            "message": "Risk scenarios do not reference specific architecture components. Each risk must be traceable to a specific component from the architecture review."
        })
    
    if not has_control_refs:
        issues.append({
            "type": "missing_control_refs",
            "severity": "critical",
            "message": "Risk scenarios do not reference specific control frameworks or control IDs. Each risk must map to specific framework requirements."
        })
    
    return issues


def _validate_timeline_factuality(content: str) -> List[Dict]:
    """Validate that remediation timelines are grounded in org data, not arbitrary"""
    issues = []
    
    # Check for generic arbitrary timelines without justification
    generic_timelines = re.findall(r'(?:0[-–]30\s*days|30[-–]90\s*days|90\+?\s*days|1[-–]3\s*months|3[-–]6\s*months)', content)
    has_sla_reference = bool(re.search(r'patch\s*SLA|SLA|patch.*(?:4\s*h|72\s*h|30\s*day)|change\s*velocity|deploy.*week', content, re.IGNORECASE))
    
    if generic_timelines and not has_sla_reference:
        issues.append({
            "type": "arbitrary_timelines",
            "severity": "warning",
            "message": f"Found {len(generic_timelines)} generic timeline references without org SLA justification. Timelines should reference the organization's patch SLA and change velocity."
        })
    
    return issues


def _validate_framework_citations(content: str) -> List[Dict]:
    """Validate that framework citations are specific (control IDs, not just names)"""
    issues = []
    
    # Check for specific control IDs (e.g., SC-28, AC-6, IA-5)
    specific_controls = re.findall(r'[A-Z]{2}-\d+(?:\(\d+\))?', content)
    # Check for generic framework mentions without specifics
    generic_mentions = re.findall(r'(?:NIST|PCI-DSS|APRA|CRI|DORA)\s+(?:compliance|requirements|standards)', content, re.IGNORECASE)
    
    if len(generic_mentions) > len(specific_controls):
        issues.append({
            "type": "vague_citations",
            "severity": "warning",
            "message": "Framework references are too generic. Citations should include specific control IDs (e.g., NIST SC-28, PCI-DSS 3.5) rather than just framework names."
        })
    
    return issues
