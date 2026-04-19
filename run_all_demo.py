#!/usr/bin/env python3
"""
MASTER DEMO SCRIPT - Run everything in one Python command
No bash required - works on all systems
"""

import subprocess
import sys
import os
from pathlib import Path

print("\n" + "="*90)
print(" "*15 + "🎯 DIGITAL WATERMARKING SYSTEM - COMPLETE DEMO 🎯")
print("="*90)

# Check virtual environment
if sys.prefix == sys.base_prefix:
    print("\n⚠️  WARNING: Not running in virtual environment!")
    print("   Activate it first: source venv/bin/activate")
    print("   Then run: python run_all_demo.py")
    response = input("\nContinue anyway? (y/n): ")
    if response.lower() != 'y':
        sys.exit(1)

print("\n✓ Proceeding with demo...")

# Step 1: Generate test images
print("\n" + "="*90)
print("STEP 1: GENERATING DIVERSE TEST IMAGES")
print("="*90)

try:
    import generate_test_images
    print("✅ Test images generated successfully!")
except Exception as e:
    print(f"⚠️  Error generating test images: {e}")

# Step 2: Generate comprehensive results
print("\n" + "="*90)
print("STEP 2: RUNNING COMPREHENSIVE WATERMARKING EXPERIMENTS")
print("="*90)

try:
    import generate_comprehensive_results
    print("✅ Experiments completed!")
except Exception as e:
    print(f"⚠️  Error running experiments: {e}")

# Step 3: Show results
print("\n" + "="*90)
print("STEP 3: DISPLAYING COMPREHENSIVE RESULTS")
print("="*90)

try:
    import show_comprehensive_results
    print("✅ Results displayed!")
except Exception as e:
    print(f"⚠️  Error displaying results: {e}")

print("\n" + "="*90)
print("✅ DEMO COMPLETE")
print("="*90)
