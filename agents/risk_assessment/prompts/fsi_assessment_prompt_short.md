# FSI Risk Assessment Prompt
For project {project_id}, conduct a comprehensive FSI risk assessment following the FSI Risk Framework Template structure. Follow this exact workflow:

## STEP 0: READ ORGANIZATION PROFILE
Call get_org_profile with project_id to retrieve the linked organization profile. Note the organization's industry, frameworks, risk appetite, crown jewels, security maturity, and threat landscape. Use this context to calibrate all risk scores and prioritize findings.

## STEP 1: GATHER INFORMATION
First, use your A2A communication tools to gather required information:

### Message to Architect Agent:
"For project {project_id}, perform a fresh architecture assessment. Analyze the architecture diagram, identify all components, data flows, and architecture issues. Return the full review content to me directly. Do not ask follow-up questions."

### Message to Security Architect Agent:
"For project {project_id}, perform a fresh security assessment. Identify all security issues, vulnerabilities, control gaps, and compliance concerns. Return the full assessment content to me directly. Do not ask follow-up questions."

## STEP 2: CONDUCT FSI RISK ASSESSMENT
Using the information gathered above, create a comprehensive FSI risk assessment report following these requirements:

### Critical Requirements:
- **CONDUCT ACTUAL FSI RISK ANALYSIS** - analyze the gathered data and create comprehensive risk assessment
- Using the information from **STEP 1** determine which of the FSI business risk scenarios (see reference at end) are relevant. For each of these risks complete ALL the steps below.
    1. Apply 5x5 risk matrix scoring (likelihood × impact)
    2. Evaluate control effectiveness (E/PE/I/NI)
    3. Calculate residual risk ratings and tolerance levels
- Include specific risk scenarios, mitigation strategies, and recommendations
- **NEVER just save empty templates** - always perform actual risk analysis first
- **SEPARATE risks into two categories:**
    - **SOLUTION-INTRODUCED RISKS** [SOLUTION] — new risks created by THIS architecture (what the project team must fix)
    - **INHERITED ENTERPRISE RISKS** [ENTERPRISE] — pre-existing org risks from the org profile that affect this solution (context for scoring, owned by enterprise not this project)
    - Present them in separate sections in the summary and label each risk in the table
- **FACTUAL REMEDIATION TIMELINES** — do NOT invent arbitrary timelines. Instead:
    - Use the org's patch SLA for severity-based timelines (critical=Xhrs, high=Xdays from org profile)
    - Reference existing audit finding due dates when risks overlap
    - Calibrate effort against org's change velocity (deploys/week)
    - If timeline cannot be grounded in org data, state "Timeline TBD" rather than guessing

Follow the FSI Risk Framework Template structure below:

## FSI RISK FRAMEWORK TEMPLATE TO FOLLOW:
{fsi_template}

## OUTPUT FORMAT REQUIREMENTS

**CRITICAL: You MUST generate the report in MARKDOWN format using the EXACT template structure above. DO NOT generate HTML, DO NOT create your own format.**

### Mandatory Requirements:
1. **Use EXACT template structure** - Follow every section, heading, and format from the FSI Risk Framework Template above
2. **Generate MARKDOWN only** - No HTML, no custom styling, pure markdown
3. **Replace ALL placeholders** - Fill in [PROJECT_NAME], [CURRENT_DATE], [RISK_NAME], etc. with actual data
4. **Include ALL sections** - Every section from Table of Contents through Recommendations must be present
5. **Follow exact numbering** - Use the same section numbers (1. Project Overview, 2. Risk Summary, 3. Control Assessment, 4. Critical and High Risk Actions, 5. Compliance and Regulatory Considerations, 6. Recommendations and Next Steps)
6. **Use template tables** - Keep the exact table structures for likelihood, impact, risk matrix, etc.
7. **Fill risk scenarios** - Replace example scenarios with actual project-specific risks
8. **Include individual risk matrices** - For each risk scenario, include the 5x5 matrix showing where that specific risk falls (highlight with **bold** the cell corresponding to the risk's likelihood and impact)

### Template Compliance Check:
- ✅ Starts with "# FSI Risk Assessment Report"
- ✅ Has Table of Contents with exact links
- ✅ Includes all 6 numbered sections and the subsections
- ✅ Uses markdown tables (not HTML)
- ✅ Ends with footer format from template

**CRITICAL: After generating the complete assessment following the EXACT template format, you MUST call save_risk_assessment with these exact parameters:**
- **project_id: "{project_id}"**
- **assessment_content: [the complete FSI risk assessment report you just generated in EXACT template format]**

**Then present the complete FSI Risk Assessment Report to the user for review.**

---

## FSI BUSINESS RISK SCENARIOS REFERENCE:

### Scenario 1: Critical service disruption
- **Risk Category**: Operational Risk, Reputational Risk
- **Description**: Delivery of critical service is disrupted beyond acceptable tolerances
- **Impact**: High (4) - majority of customers affected, $loss of revenue, brand damage, regulatory scrutiny
- **Key Controls**: System monitoring, backup systems, incident response procedures, high availability, business continuity

### Scenario 2: Business continuity failure
- **Risk Category**: Operational Risk, Business Continuity Risk
- **Description**: Disaster recovery and business continuity fail to recover critical business operations  
- **Impact**: Very High (5) - Extended outage, customer service disruption
- **Key Controls**: Geographic diversification, disaster recovery sites, business continuity planning

### Scenario 3: Capacity risk
- **Risk Category**: Operational Risk, Business Continuity Risk
- **Description**: Failure of service delivery to meet increased demand  
- **Impact**: Very High (3) - customer service disruption
- **Key Controls**: Capacity planning, high availability, scaling

### Scenario 4: Change delivery failure
- **Risk Category**: Operational Risk, Business Continuity Risk
- **Description**: Disruption to critical operations due to failed change delivery  
- **Impact**: Very High (3) - customer service disruption
- **Key Controls**: testing, automated deployment

### Scenario 5: Insufficient service provider arrangement
- **Risk Category**: Operational Risk, Service Provider Risk
- **Description**: Agreement with material service provider does not meet requirements
- **Impact**: Very High (3) - customer service disruption
- **Key Controls**: contract management, service provider governance

### Scenario 6: Material service provider Failure
- **Risk Category**: Operational Risk, Service Provider Risk
- **Description**: Contractual agreements with Key technology vendor fails to deliver in accordance with agreed service levels 
- **Impact**: Very High (4) - Service disruption, replacement costs, customer impact
- **Key Controls**: Vendor due diligence, contract terms, contingency planning

### Scenario 7: Customer Data Breach
- **Risk Category**: Information Security Risk, Privacy Risk, Regulatory Risk, Reputational Risk
- **Description**: Unauthorized access to customer PII database affecting a large number of customers
- **Impact**: Very High (5) - Regulatory fines, customer lawsuits, brand damage
- **Key Controls**: Data encryption, access management, DLP solutions, security monitoring

### Scenario 8: PCI DSS Non-Compliance
- **Risk Category**: Regulatory Risk, Reputational Risk
- **Description**: Payment processing systems fail PCI DSS audit due to security gaps
- **Impact**: High (3) - Fines, card brand penalties, processing restrictions
- **Key Controls**: PCI compliance program, regular assessments, security controls

### Scenario 9: APRA CPS230 non-compliance
- **Risk Category**: Privacy Risk, Regulatory Risk
- **Description**: Failure to meet CPS230 regulatory expectation
- **Impact**: Medium (3) - Increased regulatory scrutiny, enforceable undertakings, capital overlay
- **Key Controls**: service provider governance, business continuity

### Scenario 10: APRA CPS234 non-compliance
- **Risk Category**: Information Security Risk, Privacy Risk, Regulatory Risk
- **Description**: Failure to meet CPS234 regulatory expectation
- **Impact**: Medium (3) - Increased regulatory scrutiny, enforceable undertakings, capital overlay
- **Key Controls**: information security management