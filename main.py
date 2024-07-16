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

#######

print(mfn_mesh.onBoundary(136))
print(mfn_mesh.edgeBorderInfo(702))

borderPoly = []
border_sel = om.MSelectionList()
for index in range(0, mfn_mesh.numPolygons-1):
    if mfn_mesh.onBoundary(index):
        borderPoly.append(index)
        border_sel.add('polySurface11.f[{0}]'.format(index))
print(border_sel)
om.MGlobal.setActiveSelectionList(border_sel)

#######
for index, id in enumerate(vertexIds):
    points.append(mfn_mesh.getPoint(id))
    polygonConnects.append(index)

print(points, polygonConnects)

new_mesh.create(points, [len(points)], polygonConnects)
new_mesh.updateSurface()