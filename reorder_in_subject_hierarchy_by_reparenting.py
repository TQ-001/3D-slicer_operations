import re
import slicer

def is_image_node(n):
    return n is not None and n.IsA("vtkMRMLScalarVolumeNode")

def is_segmentation_node(n):
    return n is not None and n.IsA("vtkMRMLSegmentationNode")

def is_labelmap_node(n):
    return n is not None and n.IsA("vtkMRMLLabelMapVolumeNode")

def collect_pairs():
    nodes = list(slicer.mrmlScene.GetNodes())

    images = {}
    for n in nodes:
        if not is_image_node(n):
            continue
        name = n.GetName() or ""
        m = re.match(r"^(?P<pid>.+)_0000$", name)
        if m:
            images[m.group("pid")] = n

    segs = {}
    for n in nodes:
        name = n.GetName() or ""

        # Segmentation node OR labelmap volume node named {patient_id}.nii.gz
        if is_segmentation_node(n) or is_labelmap_node(n):
            m = re.match(r"^(?P<pid>.+)\.nii(\.gz)?$", name)
            if m:
                segs[m.group("pid")] = n

    patient_ids = sorted(set(images.keys()) | set(segs.keys()))
    pairs = []
    for pid in patient_ids:
        pairs.append({
            "patient_id": pid,
            "imageNode": images.get(pid, None),
            "segNode": segs.get(pid, None),
        })
    return pairs

def reorder_in_subject_hierarchy_by_reparenting(pairs, move_to_scene_root=True):
    shNode = slicer.mrmlScene.GetSubjectHierarchyNode()
    sceneItemID = shNode.GetSceneItemID()

    # Build desired node order: image1, seg1, image2, seg2, ...
    desired_nodes = []
    for p in pairs:
        if p["imageNode"] is not None:
            desired_nodes.append(p["imageNode"])
        if p["segNode"] is not None:
            desired_nodes.append(p["segNode"])

    desired_itemIDs = []
    for n in desired_nodes:
        itemID = shNode.GetItemByDataNode(n)
        if itemID:
            desired_itemIDs.append(itemID)

    if not desired_itemIDs:
        print("No matching items found to reorder.")
        return

    # Create a temporary folder under the scene (used as a staging area)
    tmpName = "__reorder_tmp__"
    tmpFolderID = shNode.CreateFolderItem(sceneItemID, tmpName)

    # Optionally move everything to scene root first (keeps it simple/consistent)
    # If you don't want to change grouping, set move_to_scene_root=False.
    if move_to_scene_root:
        for itemID in desired_itemIDs:
            shNode.SetItemParent(itemID, sceneItemID)

    # Stage: move all desired items into temp folder (this removes them from current ordering)
    for itemID in desired_itemIDs:
        shNode.SetItemParent(itemID, tmpFolderID)

    # Final: move them back in the exact order we want (they get appended in that order)
    for itemID in desired_itemIDs:
        shNode.SetItemParent(itemID, sceneItemID)

    # Remove temp folder (should be empty now)
    shNode.RemoveItem(tmpFolderID)

    print(f"Reordered {len(desired_itemIDs)} items as image/seg interleaving under the scene.")

pairs = collect_pairs()

# Quick summary
missing_img = [p["patient_id"] for p in pairs if p["imageNode"] is None and p["segNode"] is not None]
missing_seg = [p["patient_id"] for p in pairs if p["segNode"] is None and p["imageNode"] is not None]
print(f"Found {len(pairs)} patient IDs.")
if missing_img:
    print(f"WARNING: missing images for {len(missing_img)} IDs (examples): {missing_img[:10]}")
if missing_seg:
    print(f"WARNING: missing segmentations for {len(missing_seg)} IDs (examples): {missing_seg[:10]}")

reorder_in_subject_hierarchy_by_reparenting(pairs, move_to_scene_root=True)
