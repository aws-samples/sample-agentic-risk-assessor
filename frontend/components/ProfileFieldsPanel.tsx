import React from 'react';

interface ProfileField {
  name: string;
  label: string;
  value: string | null;
  source?: 'document' | 'user' | null;
}

interface ProfileFieldsPanelProps {
  fields: ProfileField[];
  onFieldClick?: (fieldName: string) => void;
}

const PROFILE_SECTIONS = [
  {
    name: 'Basic Information',
    fields: [
      { name: 'organization_name', label: 'Organization Name' },
      { name: 'industry', label: 'Industry' },
      { name: 'organization_size', label: 'Size' },
      { name: 'region', label: 'Region' },
    ]
  },
  {
    name: 'Regulatory',
    fields: [
      { name: 'primary_regulations', label: 'Regulations' },
      { name: 'compliance_frameworks', label: 'Frameworks' },
    ]
  },
  {
    name: 'Risk Profile',
    fields: [
      { name: 'operational_risk_tolerance', label: 'Operational Risk' },
      { name: 'compliance_risk_tolerance', label: 'Compliance Risk' },
      { name: 'financial_risk_tolerance', label: 'Financial Risk' },
      { name: 'reputational_risk_tolerance', label: 'Reputational Risk' },
      { name: 'rto_critical_systems', label: 'RTO' },
      { name: 'rpo_critical_systems', label: 'RPO' },
    ]
  },
  {
    name: 'Security Capabilities',
    fields: [
      { name: 'iam_maturity', label: 'IAM' },
      { name: 'logging_monitoring_maturity', label: 'Monitoring' },
      { name: 'incident_response_maturity', label: 'Incident Response' },
      { name: 'infrastructure_protection_maturity', label: 'Infrastructure' },
      { name: 'data_protection_maturity', label: 'Data Protection' },
    ]
  },
  {
    name: 'Technology',
    fields: [
      { name: 'cloud_platforms', label: 'Cloud Platforms' },
    ]
  },
  {
    name: 'Business Context',
    fields: [
      { name: 'key_processes', label: 'Key Processes' },
    ]
  },
  {
    name: 'Risk Assessment',
    fields: [
      { name: 'revenue', label: 'Revenue' },
      { name: 'customers', label: 'Customers' },
      { name: 'crown_jewels', label: 'Crown Jewels' },
      { name: 'threat_landscape', label: 'Threat Landscape' },
      { name: 'change_velocity', label: 'Change Velocity' },
      { name: 'key_vendors', label: 'Key Vendors' },
      { name: 'recent_incidents', label: 'Recent Incidents' },
      { name: 'audit_findings', label: 'Audit Findings' },
    ]
  },
];

const ALL_FIELDS = PROFILE_SECTIONS.flatMap(s => s.fields);

export const ProfileFieldsPanel: React.FC<ProfileFieldsPanelProps> = ({
  fields,
  onFieldClick
}) => {
  const fieldMap = new Map(fields.map(f => [f.name, f]));
  const completedCount = ALL_FIELDS.filter(f => fieldMap.get(f.name)?.value).length;
  const totalCount = ALL_FIELDS.length;

  return (
    <div style={{
      borderTop: '1px solid #3e3e42',
      padding: '6px 0',
      overflowY: 'auto',
      flex: 1,
      fontSize: '11px'
    }}>
      {/* Header */}
      <div style={{
        padding: '4px 10px 6px',
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        color: '#ccc',
        fontWeight: 600,
        fontSize: '10px',
        textTransform: 'uppercase',
        letterSpacing: '0.5px'
      }}>
        <span>Profile</span>
        <span style={{ color: completedCount === totalCount ? '#28a745' : '#888', fontWeight: 400 }}>
          {completedCount}/{totalCount}
        </span>
      </div>

      {/* Sections */}
      {PROFILE_SECTIONS.map(section => {
        const sectionCompleted = section.fields.filter(f => fieldMap.get(f.name)?.value).length;
        return (
          <div key={section.name} style={{ marginBottom: '4px' }}>
            {/* Section header */}
            <div style={{
              padding: '3px 10px',
              fontSize: '9px',
              color: sectionCompleted === section.fields.length ? '#28a745' : '#888',
              fontWeight: 600,
              textTransform: 'uppercase',
              letterSpacing: '0.3px'
            }}>
              {sectionCompleted === section.fields.length ? '✓ ' : ''}{section.name}
            </div>
            {/* Fields */}
            {section.fields.map(fieldDef => {
              const field = fieldMap.get(fieldDef.name);
              const hasValue = !!field?.value;
              return (
                <div
                  key={fieldDef.name}
                  onClick={() => onFieldClick?.(fieldDef.name)}
                  style={{
                    padding: '2px 10px 2px 16px',
                    display: 'flex',
                    alignItems: 'center',
                    gap: '5px',
                    cursor: onFieldClick ? 'pointer' : 'default',
                    color: hasValue ? '#ccc' : '#555',
                    borderRadius: '2px',
                  }}
                  onMouseEnter={e => { (e.currentTarget as HTMLElement).style.backgroundColor = '#2a2d2e'; }}
                  onMouseLeave={e => { (e.currentTarget as HTMLElement).style.backgroundColor = 'transparent'; }}
                  title={hasValue ? `${fieldDef.label}: ${field?.value}` : `${fieldDef.label}: pending`}
                >
                  <span style={{ fontSize: '9px', width: '12px' }}>
                    {hasValue ? '✅' : '○'}
                  </span>
                  <span style={{ flex: 1, overflow: 'hidden', textOverflow: 'ellipsis', whiteSpace: 'nowrap' }}>
                    {fieldDef.label}
                  </span>
                </div>
              );
            })}
          </div>
        );
      })}

      {/* Progress bar */}
      <div style={{ padding: '6px 10px 4px' }}>
        <div style={{ height: '2px', backgroundColor: '#3e3e42', borderRadius: '1px', overflow: 'hidden' }}>
          <div style={{
            height: '100%',
            width: `${(completedCount / totalCount) * 100}%`,
            backgroundColor: completedCount === totalCount ? '#28a745' : '#007acc',
            transition: 'width 0.3s'
          }} />
        </div>
      </div>
    </div>
  );
};

export { ALL_FIELDS, PROFILE_SECTIONS };
export type { ProfileField };
