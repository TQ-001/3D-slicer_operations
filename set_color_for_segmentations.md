```
import vtk, colorsys

# Get all segmentation nodes currently in the scene
segNodes = slicer.util.getNodesByClass("vtkMRMLSegmentationNode")

# Make colors stable + nicely spaced (golden-ratio hue stepping)
golden = 0.61803398875
globalIndex = 0

for segNode in segNodes:
    # Ensure display node exists + visible
    segNode.CreateDefaultDisplayNodes()
    dispNode = segNode.GetDisplayNode()
    dispNode.SetVisibility(True)          # overall visibility
    dispNode.SetVisibility2D(True)
    dispNode.SetVisibility3D(True)

    segmentation = segNode.GetSegmentation()

    # Collect segment IDs
    ids = vtk.vtkStringArray()
    segmentation.GetSegmentIDs(ids)

    # Assign each segment a different color
    for k in range(ids.GetNumberOfValues()):
        segId = ids.GetValue(k)

        h = (globalIndex * golden) % 1.0
        r, g, b = colorsys.hsv_to_rgb(h, 0.65, 0.95)

        segmentation.GetSegment(segId).SetColor(r, g, b)
        globalIndex += 1

    segNode.Modified()
```
