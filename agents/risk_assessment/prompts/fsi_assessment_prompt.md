# FSI Risk Assessment Prompt

For project {project_id}, conduct a comprehensive FSI risk assessment following the FSI Risk Framework Template structure. Follow this exact workflow:

## STEP 1: GATHER INFORMATION

First, use your A2A communication tools to gather required information:

### Message to Architect Agent:
"For project {project_id}, share any architecture issues found in your existing assessment. If no existing assessment is available, please create a new architecture assessment and share the issues found with me."

### Message to Security Architect Agent:
"For project {project_id}, analyze and identify all security issues, vulnerabilities, and compliance gaps. Map each security issue to FSI risk categories (Technology/Cyber Risk, Privacy Risk, Regulatory/Compliance Risk). For each identified risk, provide: likelihood rating (1-5), impact rating (1-5), risk score using FSI matrix, control effectiveness rating (E/PE/I/NI), and residual risk classification."

### Message to Auditor Agent (use invoke_agent tool):
"For project {project_id}, perform a final audit of the completed risk assessment. Review the assessment for completeness, accuracy, and compliance with FSI framework requirements. Provide audit findings and recommendations."

## STEP 2: CONDUCT FSI RISK ASSESSMENT

Using the information gathered above, create a comprehensive FSI risk assessment report following these requirements:

### Critical Requirements:
- **CONDUCT ACTUAL FSI RISK ANALYSIS** - analyze the gathered data and create comprehensive risk assessment
- Map all identified risks to the 8 FSI business risk categories
- Apply 5x5 risk matrix scoring (likelihood × impact)
- Evaluate control effectiveness (E/PE/I/NI)
- Calculate residual risk ratings and tolerance levels
- Include specific risk scenarios, mitigation strategies, and recommendations
- **NEVER just save empty templates** - always perform actual risk analysis first

### QUALITY STANDARDS (MANDATORY - Prevents W40-type Issues):

#### Risk Count Consistency (CRITICAL):
- **Executive Summary total MUST equal detailed scenarios count**
- **Executive Summary total MUST equal risk matrix rows**
- **Detailed scenarios count MUST equal risk matrix rows**
- **Example**: If you identify 9 risks, you MUST have 9 detailed scenarios AND 9 matrix rows

#### Complete Risk Scenarios (MANDATORY):
Every identified risk MUST include ALL of these elements:
- **Risk Categories** - Primary and secondary FSI categories
- **Business Description** - Executive-level impact description
- **Technical Evidence** - Exactly ONE paragraph with specific technical findings
- **Risk Assessment Matrix** - Visual 5x5 matrix with highlighted cell
- **Business Impact Analysis** - Likelihood, impact, financial/operational/regulatory impacts
- **Risk Management Strategy** - Controls, effectiveness, actions, owner, timeline

#### Business Language Requirements:
- **Executive Sections**: Use business terms ("revenue loss", "operational disruption", "regulatory fines")
- **Avoid Technical Jargon**: Replace "VPC" with "network infrastructure", "ECS" with "application services"
- **Quantify Impact**: Include dollar amounts, timeframes, customer numbers
- **Strategic Focus**: Competitive advantage, market position, stakeholder confidence

#### Technical Evidence Requirements:
For each risk scenario, include exactly one paragraph:
```
**Technical Evidence:**
[One paragraph with specific technical findings, architecture gaps, security vulnerabilities, 
or compliance deficiencies that support this business risk. Include component names, 
configuration issues, or missing controls.]
```

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
5. **Follow exact numbering** - Use the same section numbers (1. Business Risk Categories, 2. Risk Matrix, etc.)
6. **Use template tables** - Keep the exact table structures for likelihood, impact, risk matrix, etc.
7. **Fill risk scenarios** - Replace example scenarios with actual project-specific risks
8. **Include visual risk matrices** - For each risk scenario, include the HTML-styled 5x5 risk matrix table with color coding:
   - Green (#4caf50): Low risk (scores 1-6)
   - Yellow (#ffeb3b): Medium risk (scores 7-11) 
   - Orange (#ff9800): High risk (scores 12-19)
   - Red (#f44336): Critical risk (scores 20-25)
   - **Bold border and highlight** the specific cell where the risk falls based on its likelihood and impact ratings

### Template Compliance Check:
- ✅ Starts with "# FSI Risk Assessment Report"
- ✅ Has Table of Contents with exact links
- ✅ Includes all 13 numbered sections
- ✅ Uses markdown tables (not HTML)
- ✅ Ends with footer format from template

**CRITICAL: After generating the complete assessment following the EXACT template format, you MUST call save_risk_assessment with these exact parameters:**
- **project_id: "{project_id}"**
- **assessment_content: [the complete FSI risk assessment report you just generated in EXACT template format]**

**Then present the complete FSI Risk Assessment Report to the user for review.**

## STEP 3: AUDIT REVIEW

After completing and saving the risk assessment, automatically send the final report to the Auditor Agent for review using your A2A communication tools:

**MANDATORY: Use invoke_agent tool to send this message to auditor:**
"Please audit this completed FSI risk assessment for project {project_id}. Review for completeness, accuracy, and compliance with FSI framework standards. The assessment has been saved and is ready for your final review."