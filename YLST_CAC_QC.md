```
import os
import csv
import math
import slicer
import vtk

# ============================================================
# User settings
# ============================================================

CSV_PATH = "$HOME/comic_cluster/SAN/medic/YLST/measurements/combined/combined_CAC_agatston_score_TS_smoothed.csv"

IMAGE_BASE_DIR = "$HOME/comic_clusterSAN/medic/YLST/scans/nifti/soft_recon"
MASK_BASE_DIR = "$HOME/comic_clusterSAN/medic/YLST/segmentation/soft_recon/Satsuma_Labs/CAC"

ID_COL = "pid"
SCORE_COL = "agatston_total"

# Rows are based on the table AFTER sorting by agatston_total descending.
# Example: load first 100 and last 100
LOAD_FIRST_N = 0
LOAD_LAST_N = 20

# Additional explicit 1-based sorted rows, e.g. [1, 2, 50, 150]
EXPLICIT_ROWS_1BASED = []

# Additional inclusive 1-based sorted row ranges, e.g. [(101, 120), (500, 550)]
EXPLICIT_RANGES_1BASED = [(800, 820),(2000, 2020)]

# Display options
CLEAR_SCENE_BEFORE_LOADING = False
LOAD_MASK_AS_LABELMAP = True
CONVERT_MASK_TO_SEGMENTATION = True      # useful for 3D display
SHOW_CAC_3D = True                       # may be slow for many cases
CENTER_VIEW_ON_CAC = True

# If loading many cases, 3D conversion can be slow. Set this False for faster batch review.
MAX_CASES_FOR_3D_CONVERSION = 30

# ============================================================
# Helper functions
# ============================================================

def parse_float(x):
    try:
        if x is None or str(x).strip() == "":
            return float("nan")
        return float(str(x).strip())
    except Exception:
        return float("nan")


def get_patient_id_from_pid(pid):
    """
    pid format expected:
        ylst-{patientID}-{accessionID}

    Example:
        ylst-123456-abcdef
    """
    parts = pid.split("-")
    if len(parts) < 3 or parts[0] != "ylst":
        raise ValueError(f"Unexpected pid format: {pid}")
    return parts[1]


def get_paths(pid):
    patient_id = get_patient_id_from_pid(pid)
    image_path = os.path.join(IMAGE_BASE_DIR, patient_id, f"{pid}.nii.gz")
    mask_path = os.path.join(MASK_BASE_DIR, f"{pid}_CACmask.nii.gz")
    return image_path, mask_path


def collect_selected_indices(n_records):
    """
    Returns zero-based indices into sorted_records.
    User-facing rows are 1-based.
    """
    selected_rows = set()

    if LOAD_FIRST_N is not None and LOAD_FIRST_N > 0:
        for r in range(1, min(LOAD_FIRST_N, n_records) + 1):
            selected_rows.add(r)

    if LOAD_LAST_N is not None and LOAD_LAST_N > 0:
        start = max(1, n_records - LOAD_LAST_N + 1)
        for r in range(start, n_records + 1):
            selected_rows.add(r)

    for r in EXPLICIT_ROWS_1BASED:
        if 1 <= r <= n_records:
            selected_rows.add(r)
        else:
            print(f"[WARN] Explicit row {r} is outside valid range 1-{n_records}")

    for start, end in EXPLICIT_RANGES_1BASED:
        if start > end:
            start, end = end, start
        start = max(1, start)
        end = min(n_records, end)
        for r in range(start, end + 1):
            selected_rows.add(r)

    return [r - 1 for r in sorted(selected_rows)]


def set_labelmap_display(label_node):
    display_node = label_node.GetDisplayNode()
    if display_node:
        display_node.SetOpacity(0.7)
        display_node.SetVisibility(True)


def convert_labelmap_to_segmentation(label_node, pid):
    seg_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode",
        f"{pid}_CAC_seg"
    )

    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
        label_node,
        seg_node
    )

    seg_node.CreateDefaultDisplayNodes()
    seg_node.SetReferenceImageGeometryParameterFromVolumeNode(label_node)

    display_node = seg_node.GetDisplayNode()
    if display_node:
        display_node.SetVisibility2DFill(True)
        display_node.SetVisibility2DOutline(True)
        display_node.SetOpacity2DFill(0.7)
        display_node.SetOpacity3D(0.8)
        display_node.SetVisibility3D(SHOW_CAC_3D)

    try:
        seg_node.CreateClosedSurfaceRepresentation()
    except Exception as e:
        print(f"[WARN] Could not create 3D representation for {pid}: {e}")

    return seg_node


def center_slice_views_on_label(label_node):
    """
    Centers slice views on the physical centre of the non-zero label voxels.
    """
    image_data = label_node.GetImageData()
    if image_data is None:
        return

    extent = image_data.GetExtent()
    ijk_to_ras = vtk.vtkMatrix4x4()
    label_node.GetIJKToRASMatrix(ijk_to_ras)

    count = 0
    sum_i = 0.0
    sum_j = 0.0
    sum_k = 0.0

    # For CAC masks, non-zero voxels are usually sparse.
    # Direct loop is acceptable for QC use, but can be slow for very large masks.
    for k in range(extent[4], extent[5] + 1):
        for j in range(extent[2], extent[3] + 1):
            for i in range(extent[0], extent[1] + 1):
                v = image_data.GetScalarComponentAsDouble(i, j, k, 0)
                if v > 0:
                    count += 1
                    sum_i += i
                    sum_j += j
                    sum_k += k

    if count == 0:
        print(f"[WARN] Empty CAC mask: {label_node.GetName()}")
        return

    center_ijk = [
        sum_i / count,
        sum_j / count,
        sum_k / count,
        1.0
    ]

    center_ras = [0.0, 0.0, 0.0, 1.0]
    ijk_to_ras.MultiplyPoint(center_ijk, center_ras)

    slicer.modules.markups.logic().JumpSlicesToLocation(
        center_ras[0],
        center_ras[1],
        center_ras[2],
        True
    )


def set_slice_background_and_label(volume_node, label_node):
    lm = slicer.app.layoutManager()
    for view_name in ["Red", "Yellow", "Green"]:
        slice_widget = lm.sliceWidget(view_name)
        if not slice_widget:
            continue
        composite = slice_widget.mrmlSliceCompositeNode()
        composite.SetBackgroundVolumeID(volume_node.GetID())
        composite.SetLabelVolumeID(label_node.GetID())
        composite.SetLabelOpacity(0.7)

    slicer.util.resetSliceViews()


# ============================================================
# Main
# ============================================================

if CLEAR_SCENE_BEFORE_LOADING:
    slicer.mrmlScene.Clear(0)

print(f"[INFO] Reading CSV: {CSV_PATH}")

records = []
with open(CSV_PATH, "r", newline="") as f:
    reader = csv.DictReader(f)
    for row in reader:
        pid = row.get(ID_COL, "").strip()
        score = parse_float(row.get(SCORE_COL, ""))

        if pid == "":
            continue

        records.append({
            "pid": pid,
            "agatston_total": score,
            "row": row
        })

print(f"[INFO] Total records read: {len(records)}")

records_sorted = sorted(
    records,
    key=lambda x: (
        -x["agatston_total"] if not math.isnan(x["agatston_total"]) else float("inf")
    )
)

selected_indices = collect_selected_indices(len(records_sorted))
selected_records = [records_sorted[i] for i in selected_indices]

print(f"[INFO] Selected records after sorting: {len(selected_records)}")

if len(selected_records) > MAX_CASES_FOR_3D_CONVERSION:
    do_3d_conversion = False
    print(
        f"[INFO] {len(selected_records)} cases selected. "
        f"Disabling segmentation conversion/3D display because this exceeds "
        f"MAX_CASES_FOR_3D_CONVERSION={MAX_CASES_FOR_3D_CONVERSION}."
    )
else:
    do_3d_conversion = CONVERT_MASK_TO_SEGMENTATION

loaded = []
missing = []
failed = []

for idx, rec in zip(selected_indices, selected_records):
    sorted_row_1based = idx + 1
    pid = rec["pid"]
    score = rec["agatston_total"]

    print("\n" + "=" * 80)
    print(f"[INFO] Sorted row: {sorted_row_1based}")
    print(f"[INFO] PID: {pid}")
    print(f"[INFO] Agatston total: {score}")

    try:
        image_path, mask_path = get_paths(pid)
    except Exception as e:
        print(f"[ERROR] {e}")
        failed.append((pid, "pid_parse_error"))
        continue

    print(f"[INFO] Image: {image_path}")
    print(f"[INFO] Mask : {mask_path}")

    image_exists = os.path.exists(image_path)
    mask_exists = os.path.exists(mask_path)

    if not image_exists or not mask_exists:
        print("[WARN] Missing file(s):")
        if not image_exists:
            print(f"       Missing image: {image_path}")
        if not mask_exists:
            print(f"       Missing mask : {mask_path}")
        missing.append((pid, image_exists, mask_exists))
        continue

    try:
        volume_node = slicer.util.loadVolume(
            image_path,
            {
                "name": f"{pid}_CT",
                "singleFile": True
            }
        )

        seg_node = slicer.util.loadSegmentation(
            mask_path,
            {
            "name": f"{pid}_CAC_seg",
            "show": False
            }
        )

        loaded.append({
            "sorted_row": sorted_row_1based,
            "pid": pid,
            "agatston_total": score,
            "volume_node": volume_node,
            "seg_node": seg_node
        })

        print(f"[OK] Loaded {pid}")

    except Exception as e:
        print(f"[ERROR] Failed to load {pid}: {e}")
        failed.append((pid, str(e)))


print("\n" + "=" * 80)
print("[SUMMARY]")
print(f"Loaded cases : {len(loaded)}")
print(f"Missing cases: {len(missing)}")
print(f"Failed cases : {len(failed)}")

if missing:
    print("\n[MISSING FILES]")
    for pid, image_exists, mask_exists in missing:
        print(
            f"{pid} | image_exists={image_exists} | mask_exists={mask_exists}"
        )

if failed:
    print("\n[FAILED LOADS]")
    for pid, reason in failed:
        print(f"{pid} | {reason}")

print("\n[INFO] Done.")
