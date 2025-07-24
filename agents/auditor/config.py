"""
Auditor Agent Configuration
"""

AUDITOR_CONFIG = {
    "agent_name": "auditor",
    "agent_description": "Senior Quality Assurance Officer & Compliance Auditor",
    "port": 9006,
    "host": "127.0.0.1",  # Bind to localhost only for security
    
    # Validation standards
    "validation_standards": {
        "risk_assessment": {
            "required_sections": [
                "Executive Summary",
                "Risk Assessment Results", 
                "Risk Summary Matrix",
                "Control Effectiveness Assessment",
                "Risk Treatment Plan"
            ],
            "required_elements_per_risk": [
                "Risk Categories",
                "Business Description", 
                "Technical Evidence",
                "Risk Assessment Matrix",
                "Business Impact Analysis",
                "Risk Management Strategy"
            ]
        },
        "architecture_review": {
            "required_sections": [
                "Business Overview",
                "Technical Architecture",
                "Component Details", 
                "Security Features",
                "Deployment Model",
                "Operational Readiness"
            ]
        },
        "security_assessment": {
            "required_areas": [
                "Access Controls",
                "Network Security",
                "Data Protection",
                "Audit Logging",
                "Vulnerability Management"
            ]
        }
    },
    
    # Quality thresholds
    "quality_thresholds": {
        "max_critical_issues": 0,  # No critical issues allowed for approval
        "max_warnings_for_conditional": 5,  # Max warnings for conditional approval
        "business_language_check": True,
        "technical_evidence_required": True
    },
    
    # A2A communication settings
    "a2a_settings": {
        "timeout": 30,
        "retry_attempts": 3,
        "validation_endpoint": "/validate"
    }
}