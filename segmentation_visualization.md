In Slicer’s Python Interactor, you can hide all segmentations (all loaded segmentation nodes) by turning off their display nodes:

## Hide all segmentation visualizations (Options 2D + 3D) in the whole scene
```
for segNode in slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
    dispNode = segNode.GetDisplayNode()
    if dispNode:
        dispNode.SetVisibility(False)      # master visibility
        dispNode.SetVisibility2D(True)    # Set to 'False' to hide in slice views
        dispNode.SetVisibility3D(True)    # Set to 'False' to hide in 3D views
```

If you want to “keep the segmentation node visible, but hide every individual segment inside it,” use this instead:

## Hide all segments inside every segmentation node
```
for segNode in slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
    dispNode = segNode.GetDisplayNode()
    if not dispNode:
        continue
    segmentation = segNode.GetSegmentation()
    for i in range(segmentation.GetNumberOfSegments()):
        segId = segmentation.GetNthSegmentID(i)
        dispNode.SetSegmentVisibility(segId, False)
```
### If you want all segmentations to show as 3D renders (closed surfaces), run this in Slicer’s Python Interactor:
**Use with care! This can cause a crash if too many segmentations are rendered!**
```
for segNode in slicer.util.getNodesByClass("vtkMRMLSegmentationNode"):
    seg = segNode.GetSegmentation()

    # "Smoothing factor" conversion parameter (0 = no smoothing)
    seg.SetConversionParameter("Smoothing factor", "0")

    # Recreate/update the closed surface using the new parameter
    segNode.CreateClosedSurfaceRepresentation()
```
