Print the loaded volume filenames (full path)

```
import slicer

volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

for volume in volumes:
    storageNode = volume.GetStorageNode()
    if storageNode:
        print(storageNode.GetFileName())
        
```

Print the loaded volume filenames (only filename)
```        
import slicer
import os

volumes = slicer.util.getNodesByClass("vtkMRMLScalarVolumeNode")

filenames = []

for volume in volumes:
    storageNode = volume.GetStorageNode()
    if storageNode and storageNode.GetFileName():
        fullpath = storageNode.GetFileName()
        filename = os.path.basename(fullpath)
        filenames.append(filename)

print("Found", len(filenames), "volume files:\n")
for name in filenames:
    print(name)
```

Save the filenames to list
```
import os
import slicer

outputFile = os.path.join(slicer.app.defaultScenePath, "volume_filenames.txt")

with open(outputFile, "w") as f:
    for name in filenames:
        f.write(name + "\n")

print("Saved to:", outputFile)

```
