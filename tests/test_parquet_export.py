"""
Test Parquet Export and Read

This script:
1. Checks if Parquet files exist
2. Reads them with Pandas
3. Shows basic statistics
"""

import os
import pandas as pd
from pathlib import Path

print("=" * 60)
print("  TESTING PARQUET EXPORT")
print("=" * 60)
print()

# Check if files exist
parquet_dir = Path("data/parquet")

if not parquet_dir.exists():
    print("❌ Parquet directory doesn't exist yet")
    print("   Run: python manage.py analytics export --output-dir data/parquet")
    print()
    print("   Note: Stop services first with .\\stop_all.bat")
    exit(1)

files = {
    'dim_candidates': parquet_dir / 'dim_candidates.parquet',
    'dim_jobs': parquet_dir / 'dim_jobs.parquet',
    'fact_applications': parquet_dir / 'fact_applications.parquet'
}

print("📁 Checking Parquet files...")
print()

for name, filepath in files.items():
    if filepath.exists():
        size_kb = filepath.stat().st_size / 1024
        print(f"✅ {name}: {size_kb:.2f} KB")
    else:
        print(f"❌ {name}: Not found")

print()
print("=" * 60)
print("  READING PARQUET FILES")
print("=" * 60)
print()

# Read and analyze each file
for name, filepath in files.items():
    if not filepath.exists():
        continue
    
    print(f"\n📊 {name.upper()}")
    print("-" * 60)
    
    df = pd.read_parquet(filepath)
    
    print(f"  • Rows: {len(df)}")
    print(f"  • Columns: {len(df.columns)}")
    print(f"  • Memory: {df.memory_usage(deep=True).sum() / 1024:.2f} KB")
    print()
    print("  Columns:")
    for col in df.columns:
        print(f"    - {col} ({df[col].dtype})")
    
    if len(df) > 0:
        print()
        print("  First 3 rows:")
        print(df.head(3).to_string(index=False))

print()
print("=" * 60)
print("  ANALYTICS SUMMARY")
print("=" * 60)
print()

# Analyze fact_applications if it exists
fact_file = files['fact_applications']
if fact_file.exists():
    df = pd.read_parquet(fact_file)
    
    print("📈 Application Statistics:")
    print(f"  • Total Applications: {len(df)}")
    
    if 'status' in df.columns:
        print(f"\n  Status Distribution:")
        status_counts = df['status'].value_counts()
        for status, count in status_counts.items():
            pct = (count / len(df)) * 100
            print(f"    - {status}: {count} ({pct:.1f}%)")
    
    if 'ai_score' in df.columns:
        print(f"\n  AI Scores:")
        print(f"    - Average: {df['ai_score'].mean():.1f}")
        print(f"    - Min: {df['ai_score'].min()}")
        print(f"    - Max: {df['ai_score'].max()}")
        print(f"    - Std Dev: {df['ai_score'].std():.1f}")
    
    if 'is_hired' in df.columns:
        hired_count = df['is_hired'].sum()
        hired_pct = (hired_count / len(df)) * 100
        print(f"\n  Hiring:")
        print(f"    - Hired: {hired_count} ({hired_pct:.1f}%)")
        print(f"    - Not Hired: {len(df) - hired_count} ({100 - hired_pct:.1f}%)")

print()
print("=" * 60)
print("✅ PARQUET EXPORT TEST COMPLETE!")
print("=" * 60)
print()
print("Next steps:")
print("  1. These files can be imported to BigQuery")
print("  2. Analyze with Pandas, Spark, or other tools")
print("  3. Share with data scientists")
print("  4. Use as backup/restore")
