-How to automatically set lung window for CT images in Slicer (the parameters inside window level can be modified as you require):

in slicer python interactor window:


```
all_nodes = slicer.mrmlScene.GetNodesByClass('vtkMRMLScalarVolumeNode')
for ct in all_nodes:
    if isinstance(ct, slicer.vtkMRMLLabelMapVolumeNode):      
        continue                
    else:
        ct.GetDisplayNode().SetAutoWindowLevel(False)        
        ct.GetDisplayNode().SetWindowLevel(1500,-500)   


