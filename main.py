import re
import maya.api.OpenMaya as om
import maya.cmds as cmds

# get the mesh vertex position
sel = cmds.ls(sl=True)
print(sel)
vertexIds = []
for i in sel:
    vertexId = re.findall("\[(.*)\]", i)[0]
    vertexIds.append(int(vertexId))

# get the dag path
selection_list = om.MSelectionList()
selection_list.add(sel[0])
dag_path = selection_list.getDagPath(0)
print(selection_list)
print(dag_path)
# creating Mfn Mesh
mfn_mesh = om.MFnMesh(dag_path)
new_mesh = om.MFnMesh()
points = []
polygonConnects = []

for index, idx in enumerate(vertexIds):
    points.append(mfn_mesh.getPoint(idx))
    polygonConnects.append(index)

print(points, polygonConnects)

new_mesh.create(points, [len(points)], polygonConnects)
new_mesh.updateSurface()
