Temp file for spinal cord QC

```
import os
import re
import qt
import slicer
import vtk

# =========================
# User settings
# =========================

DEST_DIR = "$HOME/Spinal_cord_QC"

mkdir -p $HOME/Spinal_cord_QC

SEGMENT_NAMES_TO_SHOW = ["Segment_2", "Segment_3", "Segment_4"]

# View direction for 3D rendering:
# "LR" means camera looks along the left-right anatomical axis.
# In Slicer RAS coordinates, X is left-right.
THREE_D_VIEW_DIRECTION = "RL"

# Image size of captured views
VIEW_WIDTH = 900
VIEW_HEIGHT = 900

# Whether to automatically convert loaded labelmaps to segmentation nodes
CONVERT_LABELMAP_TO_SEGMENTATION = True

os.makedirs(DEST_DIR, exist_ok=True)


# =========================
# Helper functions
# =========================

def get_patient_id_from_node_name(name):
    """
    Expected examples:
      1005234_19000101_128309
      1005234_19000101_128309.nii.gz
      1005234_19000101_128309_0000
    """
    base = name.replace(".nii.gz", "").replace(".nii", "")
    if base.endswith("_0000"):
        base = base[:-5]
    return base


def find_ct_node_for_patient(patient_id):
    """
    Find scalar volume named {patient_id}_0000 or containing that string.
    """
    volume_nodes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

    exact_name = f"{patient_id}_0000"
    for node in volume_nodes:
        if node.GetName() == exact_name:
            return node

    for node in volume_nodes:
        if exact_name in node.GetName():
            return node

    return None


def find_segmentation_node_for_patient(patient_id):
    """
    Find existing segmentation node matching patient_id.
    """
    seg_nodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")

    for node in seg_nodes:
        if patient_id in node.GetName():
            return node

    return None


def find_labelmap_node_for_patient(patient_id):
    """
    Find labelmap node matching patient_id.
    """
    label_nodes = slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode")

    for node in label_nodes:
        if patient_id in node.GetName():
            return node

    return None


def convert_labelmap_to_segmentation(label_node, reference_volume_node=None):
    """
    Convert a loaded labelmap volume to a segmentation node.
    """
    seg_node = slicer.mrmlScene.AddNewNodeByClass(
        "vtkMRMLSegmentationNode",
        label_node.GetName().replace(".nii.gz", "").replace(".nii", "") + "_seg"
    )

    if reference_volume_node is not None:
        seg_node.SetReferenceImageGeometryParameterFromVolumeNode(reference_volume_node)

    slicer.modules.segmentations.logic().ImportLabelmapToSegmentationNode(
        label_node,
        seg_node
    )

    return seg_node


def get_or_create_segmentation_for_patient(patient_id):
    seg_node = find_segmentation_node_for_patient(patient_id)
    if seg_node is not None:
        return seg_node

    if not CONVERT_LABELMAP_TO_SEGMENTATION:
        return None

    label_node = find_labelmap_node_for_patient(patient_id)
    ct_node = find_ct_node_for_patient(patient_id)

    if label_node is None:
        return None

    return convert_labelmap_to_segmentation(label_node, ct_node)


def set_only_selected_segments_visible(seg_node, segment_names):
    """
    Hide all segments, then show only the selected segment names.
    """
    display_node = seg_node.GetDisplayNode()
    if display_node is None:
        seg_node.CreateDefaultDisplayNodes()
        display_node = seg_node.GetDisplayNode()

    segmentation = seg_node.GetSegmentation()

    # Hide all
    for i in range(segmentation.GetNumberOfSegments()):
        segment_id = segmentation.GetNthSegmentID(i)
        display_node.SetSegmentVisibility(segment_id, False)
        # Removed the 2D/3D specific visibility calls here

    # Show selected
    missing = []
    for seg_name in segment_names:
        segment_id = segmentation.GetSegmentIdBySegmentName(seg_name)
        if not segment_id:
            missing.append(seg_name)
            continue

        display_node.SetSegmentVisibility(segment_id, True)
        # Removed the 2D/3D specific visibility calls here

    display_node.SetVisibility(True)
    display_node.SetVisibility2D(True)
    display_node.SetVisibility3D(True)

    if missing:
        print(f"[WARNING] Missing segments in {seg_node.GetName()}: {missing}")

def setup_layout():
    """
    Use a layout with one 3D view and one red slice view.
    """
    slicer.app.layoutManager().setLayout(slicer.vtkMRMLLayoutNode.SlicerLayoutFourUpView)

    lm = slicer.app.layoutManager()

    three_d_view = lm.threeDWidget(0).threeDView()
    red_view = lm.sliceWidget("Red").sliceView()

    three_d_view.setFixedSize(VIEW_WIDTH, VIEW_HEIGHT)
    red_view.setFixedSize(VIEW_WIDTH, VIEW_HEIGHT)

    return three_d_view, red_view


def setup_slice_view(ct_node, seg_node):
    """
    Configure sagittal slice view with CT background and segmentation overlay.
    """
    lm = slicer.app.layoutManager()
    red_widget = lm.sliceWidget("Red")
    red_logic = red_widget.sliceLogic()
    red_comp = red_logic.GetSliceCompositeNode()
    red_node = red_logic.GetSliceNode()

    # Set sagittal orientation
    red_node.SetOrientation("Sagittal")

    # Set CT as background
    red_comp.SetBackgroundVolumeID(ct_node.GetID())

    # Do not use label overlay here because we are using segmentation display
    red_comp.SetLabelVolumeID(None)

    # Fit to volume
    slicer.util.setSliceViewerLayers(background=ct_node, fit=True)

    # Center on segmentation
    bounds = [0] * 6
    seg_node.GetRASBounds(bounds)
    center_ras = [
        0.5 * (bounds[0] + bounds[1]),
        0.5 * (bounds[2] + bounds[3]),
        0.5 * (bounds[4] + bounds[5]),
    ]
    red_node.JumpSliceByCentering(*center_ras)

    red_widget.sliceView().forceRender()


def setup_3d_view(ct_node, seg_node, view_direction="LR"):
    """
    Configure 3D view and set camera to look along LR axis.
    """
    three_d_view = slicer.app.layoutManager().threeDWidget(0).threeDView()
    view_node = three_d_view.mrmlViewNode()

    view_node.SetBoxVisible(False)
    view_node.SetAxisLabelsVisible(False)
    view_node.SetOrientationMarkerType(slicer.vtkMRMLViewNode.OrientationMarkerTypeAxes)

    # Fit camera to segmentation bounds
    bounds = [0] * 6
    seg_node.GetRASBounds(bounds)

    cx = 0.5 * (bounds[0] + bounds[1])
    cy = 0.5 * (bounds[2] + bounds[3])
    cz = 0.5 * (bounds[4] + bounds[5])
    center = [cx, cy, cz]

    dx = max(bounds[1] - bounds[0], 1)
    dy = max(bounds[3] - bounds[2], 1)
    dz = max(bounds[5] - bounds[4], 1)
    dist = 2.5 * max(dx, dy, dz)

    camera_node = slicer.modules.cameras.logic().GetViewActiveCameraNode(view_node)
    camera = camera_node.GetCamera()

    if view_direction.upper() == "LR":
        # Camera placed on +X side, looking toward centre.
        # This gives a left-right projection.
        camera.SetPosition(cx + dist, cy, cz)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)

    elif view_direction.upper() == "RL":
        camera.SetPosition(cx - dist, cy, cz)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)

    elif view_direction.upper() == "AP":
        camera.SetPosition(cx, cy + dist, cz)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)

    elif view_direction.upper() == "PA":
        camera.SetPosition(cx, cy - dist, cz)
        camera.SetFocalPoint(cx, cy, cz)
        camera.SetViewUp(0, 0, 1)

    else:
        raise ValueError(f"Unknown view direction: {view_direction}")

    camera.OrthogonalizeViewUp()
    camera.SetParallelProjection(True)
    camera.SetParallelScale(0.65 * max(dy, dz, dx))

    three_d_view.resetFocalPoint()
    three_d_view.forceRender()


def capture_view_to_png(view, output_png):
    """
    Capture a Slicer view to PNG.
    """
    slicer.util.forceRenderAllViews()
    qt.QApplication.processEvents()

    pixmap = qt.QPixmap.grabWidget(view)
    pixmap.save(output_png)

    return output_png


def concatenate_pngs_horizontally(left_png, right_png, output_png):
    """
    Concatenate two PNG images horizontally using Qt.
    """
    left_img = qt.QImage(left_png)
    right_img = qt.QImage(right_png)

    height = max(left_img.height(), right_img.height())
    width = left_img.width() + right_img.width()

    combined = qt.QImage(width, height, qt.QImage.Format_RGB32)
    combined.fill(qt.Qt.white)

    painter = qt.QPainter(combined)
    painter.drawImage(0, 0, left_img)
    painter.drawImage(left_img.width(), 0, right_img)
    painter.end()

    combined.save(output_png)


def add_title_to_combined_png(input_png, output_png, title_text):
    """
    Add a simple title at the top of the combined PNG.
    """
    img = qt.QImage(input_png)

    title_height = 50
    out = qt.QImage(img.width(), img.height() + title_height, qt.QImage.Format_RGB32)
    out.fill(qt.Qt.white)

    painter = qt.QPainter(out)

    font = qt.QFont()
    font.setPointSize(18)
    font.setBold(True)
    painter.setFont(font)
    painter.setPen(qt.Qt.black)

    painter.drawText(
        qt.QRect(0, 0, img.width(), title_height),
        qt.Qt.AlignCenter,
        title_text
    )

    painter.drawImage(0, title_height, img)
    painter.end()

    out.save(output_png)


def process_patient(patient_id):
    print(f"\n[INFO] Processing {patient_id}")

    # --- NEW: Hide all segmentations to clear the 3D view from the previous patient ---
    for node in slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
        if node.GetDisplayNode():
            node.GetDisplayNode().SetVisibility(False)
    # ----------------------------------------------------------------------------------

    ct_node = find_ct_node_for_patient(patient_id)
    if ct_node is None:
        print(f"[ERROR] CT node not found for {patient_id}. Expected {patient_id}_0000")
        return False

    seg_node = get_or_create_segmentation_for_patient(patient_id)
    if seg_node is None:
        print(f"[ERROR] Segmentation or labelmap node not found for {patient_id}")
        return False

    print(f"[INFO] CT: {ct_node.GetName()}")
    print(f"[INFO] Segmentation: {seg_node.GetName()}")

    # This turns visibility back ON for the current patient only
    set_only_selected_segments_visible(seg_node, SEGMENT_NAMES_TO_SHOW)

    three_d_view, red_view = setup_layout()

    # Center the views on the new patient's coordinates
    setup_3d_view(ct_node, seg_node, THREE_D_VIEW_DIRECTION)
    setup_slice_view(ct_node, seg_node)

    tmp_3d = os.path.join(DEST_DIR, f"{patient_id}_tmp_3D.png")
    tmp_sag = os.path.join(DEST_DIR, f"{patient_id}_tmp_sagittal.png")
    tmp_combined = os.path.join(DEST_DIR, f"{patient_id}_tmp_combined.png")

    final_png = os.path.join(DEST_DIR, f"{patient_id}_spinal_cord_QC.png")

    capture_view_to_png(three_d_view, tmp_3d)
    capture_view_to_png(red_view, tmp_sag)

    concatenate_pngs_horizontally(tmp_3d, tmp_sag, tmp_combined)
    add_title_to_combined_png(
        tmp_combined,
        final_png,
        f"{patient_id}: 3D RL render + sagittal overlay"
    )

    # Clean temporary images
    for p in [tmp_3d, tmp_sag, tmp_combined]:
        if os.path.exists(p):
            os.remove(p)

    print(f"[DONE] Saved: {final_png}")
    return True

def find_loaded_patient_ids():
    """
    Infer patient IDs from loaded labelmaps/segmentations.
    Prefer segmentation nodes, fallback to labelmap nodes.
    """
    patient_ids = set()

    for seg_node in slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
        name = seg_node.GetName()
        pid = get_patient_id_from_node_name(name)
        if find_ct_node_for_patient(pid) is not None:
            patient_ids.add(pid)

    for label_node in slicer.util.getNodesByClass("vtkMRMLLabelMapVolumeNode"):
        name = label_node.GetName()
        pid = get_patient_id_from_node_name(name)
        if find_ct_node_for_patient(pid) is not None:
            patient_ids.add(pid)

    return sorted(patient_ids)


# =========================
# Run QC for all loaded cases
# =========================

patient_ids = find_loaded_patient_ids()

print(f"[INFO] Found {len(patient_ids)} loaded patient(s):")
for pid in patient_ids:
    print("  ", pid)

for pid in patient_ids:
    process_patient(pid)

print("\n[ALL DONE]")
