FROM --platform=linux/amd64 node:18-alpine

WORKDIR /app

# Update Alpine packages to fix CVE-2025-9230 (OpenSSL) and install curl for health checks
RUN apk update && apk upgrade --no-cache openssl && apk add --no-cache curl libc6-compat

COPY package.json package-lock.json* ./
RUN npm install

COPY . .

# Build args for environment variables
ARG NEXT_PUBLIC_API_URL
ARG NEXT_PUBLIC_COGNITO_USER_POOL_ID
ARG NEXT_PUBLIC_COGNITO_CLIENT_ID
ARG NEXT_PUBLIC_AGENTS_URL
ARG NEXT_PUBLIC_FEDERATED_SSO_ENABLED=false
ARG NEXT_PUBLIC_COGNITO_DOMAIN

# Set environment variables for build
ENV NEXT_PUBLIC_API_URL=$NEXT_PUBLIC_API_URL
ENV NEXT_PUBLIC_COGNITO_USER_POOL_ID=$NEXT_PUBLIC_COGNITO_USER_POOL_ID
ENV NEXT_PUBLIC_COGNITO_CLIENT_ID=$NEXT_PUBLIC_COGNITO_CLIENT_ID
ENV NEXT_PUBLIC_AGENTS_URL=$NEXT_PUBLIC_AGENTS_URL
ENV NEXT_PUBLIC_FEDERATED_SSO_ENABLED=$NEXT_PUBLIC_FEDERATED_SSO_ENABLED
ENV NEXT_PUBLIC_COGNITO_DOMAIN=$NEXT_PUBLIC_COGNITO_DOMAIN

# Build the application for production
RUN npm run build

# Create non-root user (Alpine uses addgroup/adduser)
RUN addgroup -S nodejs && adduser -S -G nodejs nodejs && \
    chown -R nodejs:nodejs /app

# Switch to non-root user
USER nodejs

# Expose port 3000
EXPOSE 3000

# Set host to 0.0.0.0 to bind to all interfaces
ENV HOST=0.0.0.0
ENV PORT=3000

# Start the application
CMD ["npm", "start"]
