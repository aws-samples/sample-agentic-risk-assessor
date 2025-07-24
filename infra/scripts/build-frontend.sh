#!/usr/bin/env bash

# Frontend Build Script
# Handles dependency issues and ensures clean build

set -e

FRONTEND_DIR="../../frontend"

echo "🚀 Starting frontend build process..."

cd $FRONTEND_DIR

echo "🧹 Cleaning previous build artifacts..."
rm -rf .next node_modules

echo "📦 Installing dependencies..."
npm ci

echo "🔍 Type checking..."
npx tsc --noEmit

echo "🏗️ Building frontend..."
npm run build

echo "✅ Frontend build completed successfully!"