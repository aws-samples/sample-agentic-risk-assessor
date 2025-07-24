# Organization Profile Configuration

This directory contains YAML configuration files that define the conversation flow, questions, and profile structure for the Organization Profile Agent.

## Directory Structure

```
config/
├── profile_config.yaml          # Main configuration file
├── industries/                  # Industry-specific configurations
│   ├── financial.yaml
│   ├── healthcare.yaml
│   ├── technology.yaml
│   └── default.yaml            # Fallback for unknown industries
└── regions/                     # Region-specific configurations
    ├── north_america.yaml
    ├── europe.yaml
    ├── apac.yaml
    └── global.yaml
```

## Configuration Files

### profile_config.yaml

The main configuration file that defines:
- **Profile Structure**: Sections and fields that make up a complete profile
- **Conversation Flow**: Rules for how the conversation progresses
- **Industry Detection**: Keywords for automatically detecting industries
- **Region Detection**: Keywords for automatically detecting regions

### Industry Configurations

Industry-specific files (e.g., `financial.yaml`) define:
- Additional fields specific to that industry
- Industry-specific regulations and standards
- MCP search queries tailored to the industry
- Contextual questions based on sub-industries

### Region Configurations

Region-specific files (e.g., `apac.yaml`) define:
- Regional regulations by country
- Data residency requirements
- Cross-border transfer considerations
- Region-specific MCP search queries

## How It Works

1. **Initial Questions**: The agent asks core questions defined in `profile_config.yaml`
2. **Industry Detection**: When user mentions their industry, the corresponding industry config is loaded
3. **Region Detection**: When user mentions their region, the corresponding region config is loaded
4. **Dynamic Questions**: Additional questions are asked based on loaded configurations
5. **Completeness Check**: Profile completeness is calculated based on configured sections
6. **Profile Generation**: Final profile is generated using the configured structure

## Adding New Industries

To add a new industry:

1. Create a new file: `industries/your_industry.yaml`
2. Define industry-specific fields, regulations, and questions
3. Add detection keywords to `profile_config.yaml` under `industry_detection`

Example:
```yaml
# industries/manufacturing.yaml
industry: "Manufacturing"

additional_fields:
  regulatory_environment:
    - name: "iso_9001"
      type: "choice"
      question: "Is your organization ISO 9001 certified?"
      options:
        - "Yes"
        - "No"
        - "In progress"

regulations:
  - name: "ISO 9001"
    description: "Quality Management Systems"
    applicable_to: ["manufacturers"]
```

## Adding New Regions

To add a new region:

1. Create a new file: `regions/your_region.yaml`
2. Define region-specific regulations and questions
3. Add detection keywords to `profile_config.yaml` under `region_detection`

## Modifying Questions

To modify existing questions:

1. Open the relevant configuration file
2. Find the field you want to modify
3. Update the `question` text or `options`
4. Save the file - changes take effect on next agent restart

No code changes required!

## Configuration Schema

### Field Definition

```yaml
- name: "field_name"              # Internal field name (snake_case)
  type: "choice"                  # text, choice, multi-choice
  required: true                  # Is this field required?
  question: "Your question here?" # The question to ask
  options:                        # For choice/multi-choice types
    - "Option 1"
    - "Option 2"
  triggers_industry_config: true  # Load industry config when answered
```

### Section Definition

```yaml
- name: "Section Name"
  priority: 1                     # Order in which to ask (1 = first)
  required: true                  # Is this section required?
  fields:                         # List of fields in this section
    - name: "field1"
      # ... field definition
```

## Best Practices

1. **Keep questions concise**: Maximum 100 words for voice compatibility
2. **Limit options**: Maximum 4 options for multiple choice
3. **Use clear labels**: Make options easy to understand
4. **Test changes**: Always test configuration changes before deploying
5. **Version control**: Commit configuration changes with descriptive messages

## Troubleshooting

### Agent not asking expected questions

- Check that the field is marked as `required: true`
- Verify the section priority is correct
- Ensure the field name matches in all references

### Industry/region config not loading

- Check that detection keywords are present in `profile_config.yaml`
- Verify the config file name matches the industry/region key
- Check logs for configuration loading errors

### Questions appearing in wrong order

- Adjust the `priority` field in section definitions
- Check the `section_order` in `conversation_flow` configuration

## Configuration Validation

To validate your configuration files:

```bash
# From the agents/organization_profile directory
python -c "import yaml; yaml.safe_load(open('config/profile_config.yaml'))"
```

If there are no errors, your YAML is valid.

## Future Enhancements

Planned features:
- Multi-language support (separate config files per language)
- Conditional questions (show question X only if answer to Y was Z)
- Question templates with variable substitution
- Configuration versioning and migration tools
