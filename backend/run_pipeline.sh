#!/bin/bash
# Full Pipeline Test Script - Phase 1 through Phase 5
# Run this directly in your terminal: bash run_pipeline.sh

set -e  # Exit on error

cd /Users/vaishvik/Desktop/Job\ Application

echo "========================================="
echo "PHASE 1-5 PIPELINE TEST"
echo "========================================="

# Clean slate
echo ""
echo "=== STEP 1: SETUP ==="
rm -f database/jobs.db
python main.py setup --resume "data/master_resume/IT RESUME VAISHVIK PATEL.pdf"

# Search for jobs
echo ""
echo "=== STEP 2: SEARCH ==="
python main.py search

# Analyze jobs
echo ""
echo "=== STEP 3: ANALYZE ==="
python main.py analyze --all-analyze

# Generate and validate resumes
echo ""
echo "=== STEP 4: RESUMES ==="
python main.py resumes --all --validate

# Export to Excel
echo ""
echo "=== STEP 5: EXPORT ==="
python main.py export

# Check status
echo ""
echo "=== STEP 6: STATUS ==="
python main.py status

echo ""
echo "========================================="
echo "PIPELINE COMPLETE!"
echo "========================================="
echo "Check output/job_applications.xlsx for results"