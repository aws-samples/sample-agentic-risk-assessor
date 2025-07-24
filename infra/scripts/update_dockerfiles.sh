#!/bin/bash
# Script to add apt-get upgrade to all agent Dockerfiles

AGENTS_DIR="./agents/deploy"

for dockerfile in "$AGENTS_DIR"/Dockerfile.{orchestrator,architect,risk_framework,security_architect,risk_assessment,organization_profile,auditor}; do
    echo "Updating $dockerfile..."
    
    # Add upgrade to builder stage (after first apt-get install)
    sed -i '' '/# Install build dependencies/,/rm -rf \/var\/lib\/apt\/lists/ {
        /apt-get install -y/a\
    && apt-get upgrade -y \\
    }' "$dockerfile"
    
    # Add upgrade to runtime stage (after second apt-get install)  
    sed -i '' '/# Install only runtime dependencies/,/rm -rf \/var\/lib\/apt\/lists/ {
        /apt-get install -y/a\
    && apt-get upgrade -y \\
    }' "$dockerfile"
done

echo "Done!"
