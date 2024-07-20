import re
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds

def main():
    # get the mesh vertex position
    sel = cmds.ls(sl=True)

    # vertexIds = []
    # for i in sel:
    #     i = re.findall("\[(.*)\]", i)
    #     print(i)
    #     vertexIds.append(int(i))
    esquinas = []
    for object_id, object in enumerate(sel):
        # get the dag path
        selection_list = om.MSelectionList()
        selection_list.add(sel[object_id])
        dag_path = selection_list.getDagPath(0)

        # creating Mfn Mesh
        obj_name = str(dag_path)
        mfn_mesh = om.MFnMesh(dag_path)
        points = []
        polygonConnects = []

        #######

        borderPoly = []
        # border_sel = om.MSelectionList()
        for index in range(0, mfn_mesh.numPolygons):
            if mfn_mesh.onBoundary(index):
                borderPoly.append(obj_name+".f[{0}]".format(index))
                # border_sel.add(obj_name+".f[{0}]".format(index))
        # om.MGlobal.setActiveSelectionList(border_sel)

        # Takes every polygon making the border and get their edges with the PolyInfo command #
        edge_sel = []
        vertex_sel = []
        for poly in borderPoly:
            cmds.select(poly)
            edges = re.findall("[\w]+", cmds.polyInfo(fe=True)[0])
            del edges[0:2]
            border_edges = 0
            for edge in edges:
                if mfn_mesh.edgeBorderInfo(int(edge)) == -2:
                    edge_sel.append(obj_name+".e[{0}]".format(edge))
                    border_edges += 1
                    if border_edges >= 2:
                        pass
                        #edge_sel.add(poly)
        #om.MGlobal.setActiveSelectionList(edge_sel)
        cmds.select(cl=True)
        for edge in edge_sel:
            cmds.select(edge)
            vertex = re.findall("[\w]+", cmds.polyInfo(ev=True)[0])
            del vertex[0:2]
            del vertex[-1]
            if not obj_name+"vtx[{0}]".format(vertex[0]) in vertex_sel:
                vertex_sel.append(obj_name+".vtx[{0}]".format(vertex[0]))
            if not obj_name+"vtx[{0}]".format(vertex[1]) in vertex_sel:
                vertex_sel.append(obj_name+".vtx[{0}]".format(vertex[1]))
        
        cmds.select(vertex_sel, add=True)

        for vertex in vertex_sel:
            vectors = []
            cmds.select(vertex)
            connected_edges = re.findall("[\w]+", cmds.polyInfo(ve=True)[0])
            edges_angle = []
            del connected_edges[0:2]
            
            for edge in connected_edges:
                if obj_name+".e[{0}]".format(edge) in edge_sel:
                    edges_angle.append(edge)

            for edge_vtx in edges_angle:
                cmds.select(obj_name+".e[{0}]".format(edge_vtx))
                info = re.findall("[\w]+", cmds.polyInfo(ev=True)[0])
                del info[0:2]
                del info[-1]
                
                points = []
                for vertexID in info: # VERTICES QUE CONFORMAN EL EDGE #

                    points.append(mfn_mesh.getPoint(int(vertexID)))
                vectors.append(points[0] - points[1])
            
            if len(vectors) > 0:
                angle = vectors[0].angle(vectors[1])
            
                if math.degrees(angle) > 50:
                    if vertex not in esquinas:
                        esquinas.append(vertex)
                
                cmds.select(cl=True)
    cmds.select(esquinas, add=True)  



        #######
        # for index, id in enumerate(vertexIds):
        #     points.append(mfn_mesh.getPoint(id))
        #     polygonConnects.append(index)

        # print(points, polygonConnects)

        # new_mesh.create(points, [len(points)], polygonConnects)
        # new_mesh.updateSurface()

if __name__ == "__main__":
    main()
