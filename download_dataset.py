"""
Download twcs.csv using opendatasets (will prompt for Kaggle username + key).
Run: python download_dataset.py
"""
import os, sys, shutil

dest = r'C:\Users\Siddhi\Desktop\Hiver'

try:
    import opendatasets as od
    print("Downloading via opendatasets...")
    print("You will be prompted for your Kaggle username and API key.")
    print("Get your API key from: https://www.kaggle.com/settings -> API -> Create New Token")
    print()
    od.download(
        'https://www.kaggle.com/datasets/thoughtvector/customer-support-on-twitter',
        data_dir=dest
    )
    # opendatasets puts files in a subdirectory
    sub = os.path.join(dest, 'customer-support-on-twitter')
    src_csv = os.path.join(sub, 'twcs.csv')
    dst_csv = os.path.join(dest, 'twcs.csv')
    if os.path.exists(src_csv) and not os.path.exists(dst_csv):
        shutil.move(src_csv, dst_csv)
        print(f"Moved twcs.csv to {dst_csv}")
    if os.path.exists(dst_csv):
        size_mb = os.path.getsize(dst_csv) / (1024*1024)
        print(f"SUCCESS: twcs.csv is ready ({size_mb:.1f} MB)")
        print("Now run: python analyze_brands.py")
    else:
        print("twcs.csv not found after download. Check the download folder.")
except ImportError:
    print("opendatasets not available")
except Exception as e:
    print(f"Download failed: {e}")
