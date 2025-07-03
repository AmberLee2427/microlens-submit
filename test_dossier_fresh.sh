#!/bin/bash

# Test script for microlens-submit dossier generation with fresh environment
# This script creates a temporary virtual environment, installs the current version,
# runs the dossier generation test, and cleans up afterward.

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Configuration
VENV_NAME="microlens_test_env"
LOG_FILE="test_dossier_output.log"
TEST_SCRIPT="tests/test_dossier_generation.py"

# Function to print colored output
print_status() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

print_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

print_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# Function to cleanup on exit
cleanup() {
    print_status "Cleaning up..."
    
    # Deactivate virtual environment if active
    if [[ "$VIRTUAL_ENV" != "" ]]; then
        print_status "Deactivating virtual environment..."
        deactivate
    fi
    
    # Remove virtual environment
    if [[ -d "$VENV_NAME" ]]; then
        print_status "Removing virtual environment: $VENV_NAME"
        rm -rf "$VENV_NAME"
    fi
    
    # Remove test artifacts
    if [[ -d "test_submission_project" ]]; then
        print_status "Removing test submission project..."
        rm -rf "test_submission_project"
    fi
    
    if [[ -d "test_dossier_output" ]]; then
        print_status "Removing test dossier output..."
        rm -rf "test_dossier_output"
    fi
    
    print_success "Cleanup completed"
}

# Set up trap to cleanup on script exit
trap cleanup EXIT

# Start logging
print_status "Starting fresh test of microlens-submit dossier generation"
print_status "Log file: $LOG_FILE"
exec > >(tee -a "$LOG_FILE") 2>&1

echo "=========================================="
echo "Test started at: $(date)"
echo "=========================================="

# Check if we're in the right directory
if [[ ! -f "pyproject.toml" ]]; then
    print_error "pyproject.toml not found. Please run this script from the project root directory."
    exit 1
fi

if [[ ! -f "$TEST_SCRIPT" ]]; then
    print_error "Test script not found: $TEST_SCRIPT"
    exit 1
fi

print_status "Current directory: $(pwd)"
print_status "Python version: $(python3 --version)"

# Create virtual environment
print_status "Creating virtual environment: $VENV_NAME"
python3 -m venv "$VENV_NAME"

# Activate virtual environment
print_status "Activating virtual environment..."
source "$VENV_NAME/bin/activate"

print_status "Virtual environment activated: $VIRTUAL_ENV"
print_status "Python version in venv: $(python --version)"

# Upgrade pip
print_status "Upgrading pip..."
pip install --upgrade pip

# Install the package in editable mode
print_status "Installing microlens-submit in editable mode..."
pip install -e .

# Verify installation
print_status "Verifying installation..."
microlens_submit_version=$(python -c "import microlens_submit; print(microlens_submit.__version__)")
print_success "Installed microlens-submit version: $microlens_submit_version"

# Test that the CLI works
print_status "Testing CLI availability..."
if command -v microlens-submit &> /dev/null; then
    print_success "CLI command available"
    microlens-submit version
else
    print_warning "CLI command not found in PATH, but package is installed"
fi

# Run the test script
print_status "Running dossier generation test..."
echo "=========================================="
echo "Test output:"
echo "=========================================="

if python "$TEST_SCRIPT"; then
    print_success "Test completed successfully!"
else
    print_error "Test failed!"
    exit 1
fi

echo "=========================================="
echo "Test completed at: $(date)"
echo "=========================================="

print_success "All tests passed! Check the generated dossier in test_dossier_output/index.html"
print_status "Log file saved to: $LOG_FILE"

# Prompt before cleanup
read -p $'\nPress enter to clean up and remove the test environment and output files...'

# Don't cleanup here - let the trap handle it
print_status "Script completed successfully" 