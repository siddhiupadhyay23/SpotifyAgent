"""
This script sets up Kaggle credentials and downloads twcs.csv.
Run this AFTER placing your kaggle.json in C:/Users/Siddhi/.kaggle/kaggle.json

To get kaggle.json:
1. Go to https://www.kaggle.com/settings
2. Scroll to API section → click 'Create New Token'
3. This downloads kaggle.json
4. Copy it to C:/Users/Siddhi/.kaggle/kaggle.json

Then run: python setup_kaggle.py
"""

import os
import subprocess
import sys

kaggle_json_path = os.path.join(os.path.expanduser('~'), '.kaggle', 'kaggle.json')
dest_dir = r'C:\Users\Siddhi\Desktop\Hiver'

if not os.path.exists(kaggle_json_path):
    print(f"ERROR: kaggle.json not found at {kaggle_json_path}")
    print("Please follow these steps:")
    print("  1. Go to https://www.kaggle.com/settings")
    print("  2. Scroll to API section -> click 'Create New Token'")
    print("  3. Save the downloaded kaggle.json to:", kaggle_json_path)
    print("  4. Then re-run this script")
    sys.exit(1)

print(f"Found kaggle.json at {kaggle_json_path}")
print(f"Downloading twcs.csv to {dest_dir}...")

result = subprocess.run(
    [sys.executable, '-m', 'kaggle', 'datasets', 'download',
     '-d', 'thoughtvector/customer-support-on-twitter',
     '--unzip', '-p', dest_dir],
    capture_output=True, text=True
)

print("STDOUT:", result.stdout)
print("STDERR:", result.stderr)
print("Return code:", result.returncode)

csv_path = os.path.join(dest_dir, 'twcs.csv')
if os.path.exists(csv_path):
    size_mb = os.path.getsize(csv_path) / (1024 * 1024)
    print(f"\nSUCCESS: twcs.csv downloaded ({size_mb:.1f} MB)")
else:
    print("\ntwcs.csv not found after download attempt.")
