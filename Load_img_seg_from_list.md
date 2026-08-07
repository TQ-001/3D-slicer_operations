**Mount from local path first**

```
mkdir -p "$HOME/comic_cluster"
sshfs username@comic.cs.ucl.ac.uk:/ "$HOME/comic_cluster"
```

**Method 1**

Load the image and segmentation mask, generally:

```
import os
import slicer

# 1) txt path：expanduser then open
txt_path = os.path.expanduser(
    "~/comic_cluster/SAN/medic/Cardiac_SUMMIT/ipf/batch_id_QC/Dutch_batch3.txt"
)

print("TXT:", txt_path)
print("TXT exists:", os.path.exists(txt_path))

with open(txt_path, "r") as f:
    ids = [line.strip() for line in f if line.strip()]

print("IDs loaded:", len(ids))
if ids:
    print("First 5 IDs:", ids[:5])

# 2) base path ~
base_img_dir = os.path.expanduser(
    "~/comic_cluster/SAN/medic/hipct_seg/IPF_clinical_data/Dutch2_insp_nifti_LPS"
)
base_seg_dir = os.path.expanduser(
    "~/comic_cluster/SAN/medic/hipct_seg/IPF_clinical_data/Dutch2_insp_nifti_LPS/Satsuma_Labs_A/task_233"
)

print("IMG dir:", base_img_dir, "exists:", os.path.isdir(base_img_dir))
print("SEG dir:", base_seg_dir, "exists:", os.path.isdir(base_seg_dir))

loaded_vol = 0
loaded_seg = 0
missing_img = 0
missing_seg = 0

for i, pid in enumerate(ids):
    image_path = os.path.join(base_img_dir, f"{pid}_0000.nii.gz")
    seg_path   = os.path.join(base_seg_dir, f"{pid}.nii.gz")

    img_ok = os.path.exists(image_path)
    seg_ok = os.path.exists(seg_path)

    # print after a number of loading
    if i < 5 or (i % 50 == 0):
        print(f"[{i}/{len(ids)}] {pid} | img:{img_ok} seg:{seg_ok}")

    if img_ok:
        ok = slicer.util.loadVolume(image_path, {"show": False})
        if ok:
            loaded_vol += 1
        else:
            print("  FAILED loadVolume:", image_path)
    else:
        missing_img += 1

    if seg_ok:
        ok = slicer.util.loadSegmentation(seg_path, {"show": False})
        if ok:
            loaded_seg += 1
        else:
            print("  FAILED loadSegmentation:", seg_path)
    else:
        missing_seg += 1

print("\n===== Summary =====")
print("Volumes loaded:", loaded_vol)
print("Segmentations loaded:", loaded_seg)
print("Missing image:", missing_img)
print("Missing seg:", missing_seg)
```

**Method 2**

But for SUMMIT:

```
import os
import slicer

# Define file paths
summit_list_file = os.path.expanduser('~/comic_cluster/SAN/medic/Cardiac_SUMMIT/SUMMIT/QC/SUMMIT_CAC_label_batch1.txt')
veolity_dir = os.path.expanduser('~/comic_cluster/cluster/project2/SummitVeolityRecon')
lung50_dir = os.path.expanduser('~/comic_cluster/cluster/project2/SummitLung50')

# Read the IDs from the text file
with open(summit_list_file, 'r') as f:
    summit_ids = [line.strip() for line in f if line.strip()]

print(f"Found {len(summit_ids)} SUMMIT IDs to process.")

ids = summit_ids[5:6] # Note: You can use summit_ids[:5] to test loading just the first 5
print(f"Loading {len(ids)} IDs ...")
# Loop through each ID and load the volume
for i, scan_id in enumerate(ids): 
    try:
        # ID format: <pid>_<year_tag>
        # We split only on the FIRST underscore to isolate the pid
        pid, year_tag = scan_id.split('_', 1)
    except ValueError:
        print(f"Skipping invalid ID format: {scan_id}")
        continue
    
    # Define the two possible paths for the .mhd file
    path_primary = os.path.join(veolity_dir, pid, f"{scan_id}.mhd")
    path_secondary = os.path.join(lung50_dir, pid, f"{scan_id}.mhd")
    
    # Check existence and load
    if os.path.exists(path_primary):
        print(f"[{i+1}/{len(ids)}] | Loading {scan_id} from SummitVeolityRecon...")
        slicer.util.loadVolume(path_primary)
    elif os.path.exists(path_secondary):
        print(f"[{i+1}/{len(ids)}] | Loading {scan_id} from SummitLung50...")
        slicer.util.loadVolume(path_secondary)
    else:
        print(f"Warning: Could not find {scan_id} in either target directory.")

print("SUMMIT loading complete.")
```

**Method 3**

For another folder structure (Leeds_YLST):

```
import os
import slicer

# Define file paths
leeds_list_file = os.path.expanduser('~/comic_cluster/SAN/medic/Cardiac_SUMMIT/Leeds_YLST/CAC_QC/Leeds_CAC_label_batch1.txt')
soft_recon_dir = os.path.expanduser('~/comic_cluster/SAN/medic/YLST/scans/nifti/soft_recon')
lung_recon_dir = os.path.expanduser('~/comic_cluster/SAN/medic/YLST/scans/nifti/lung_recon')

# Read the IDs from the text file
with open(leeds_list_file, 'r') as f:
    leeds_ids = [line.strip() for line in f if line.strip()]

print(f"Found {len(leeds_ids)} Leeds IDs to process.")

ids = leeds_ids[:5] # Note: You can use leeds_ids[:5] to test loading just the first 5
print(f"Loading {len(ids)} IDs ...")

# Loop through each ID and load the volume
for i, scan_id in enumerate(ids): 
    # ID format: ylst-<pid>-<serie_num>
    parts = scan_id.split('-')
    if len(parts) < 3:
        print(f"Skipping invalid ID format: {scan_id}")
        continue
        
    pid = parts[1]
    
    # Define the two possible paths for the .nii.gz file
    path_primary = os.path.join(soft_recon_dir, pid, f"{scan_id}.nii.gz")
    path_secondary = os.path.join(lung_recon_dir, pid, f"{scan_id}.nii.gz")
    
    # Check existence and load
    if os.path.exists(path_primary):
        print(f"[{i+1}/{len(ids)}] | Loading {scan_id} from soft_recon...")
        slicer.util.loadVolume(path_primary)
    elif os.path.exists(path_secondary):
        print(f"[{i+1}/{len(ids)}] | Loading {scan_id} from lung_recon...")
        slicer.util.loadVolume(path_secondary)
    else:
        print(f"Warning: Could not find {scan_id} in either target directory.")

print("Leeds loading complete.")
```
