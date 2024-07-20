import re
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds


def main(geometry_list, detection_degree_threshold=30):
    # get the mesh vertex position

    for geometry in geometry_list:
        object = inint_api_objects(geometry)
        object_boundary_edge_list = get_boundary_edges(object)
        object_corner_list = get_corner_vertex_by_angle(object, detection_degree_threshold, object_boundary_edge_list)
        
        polygon_points = []
        polygon_connects = []
        new_polygon_object = om.MFnMesh()
        for index, corner_vertex in enumerate(object_corner_list):
            polygon_point = re.findall(r"[\w]+", corner_vertex)[2]
            polygon_points.append(object.get("mesh_component").getPoint(int(polygon_point)))
            polygon_connects.append(index)

        new_polygon_object.create(polygon_points, [len(polygon_points)], polygon_connects)
        new_polygon_object.updateSurface()


def inint_api_objects(geometry):
    """Initializes API Clases for manipulating geometry and its components

    Args:
        geometry (str): outliner name of one of the objects selected by the user

    Returns:
        dict: combination of API Class objects for the given geometry
    """
    selection_list = om.MSelectionList()
    selection_list.add(geometry)

    object_dag_path = selection_list.getDagPath(0)
    object_name = str(object_dag_path)
    object_mesh_component = om.MFnMesh(object_dag_path)

    return {
        "dag_path": object_dag_path,
        "name": object_name,
        "mesh_component": object_mesh_component,
    }


def _get_boundary_polygons(object_name, object_mesh_component):
    object_num_polygons = object_mesh_component.numPolygons
    boundary_polygon_list = []

    for polygon_index in range(0, object_num_polygons):
        if object_mesh_component.onBoundary(polygon_index):
            boundary_polygon_list.append(f"{object_name}.f[{polygon_index}]")

    return boundary_polygon_list


def get_boundary_edges(object):
    object_mesh_component = object.get("mesh_component")
    object_name = object.get("name")
    boundary_polygon_list = _get_boundary_polygons(object_name, object_mesh_component)
    boundary_edge_list = []

    for boundary_polygon in boundary_polygon_list:
        # PolyInfo requires components to be selected.
        cmds.select(boundary_polygon)
        # Uses PolyInfo to retrieve Edges.
        # PolyInfo Output: ['FACE     82:    223    224    225 \n']
        # Regex Cleanup: ['FACE', '82', '223', '224', '225'] then Slice Array to Ignore first 2 indexes.
        polygon_edges = re.findall(r"[\w]+", cmds.polyInfo(fe=True)[0])[2:]

        for polygon_edge in polygon_edges:
            if object_mesh_component.edgeBorderInfo(int(polygon_edge)) == -2:
                boundary_edge_list.append(f"{object_name}.e[{polygon_edge}]")

    cmds.select(cl=True)
    return boundary_edge_list


def _boundary_edges_to_vertices(object_name, boundary_edge_list):
    boundary_vertex_list = []
    for boundary_edge in boundary_edge_list:
        # PolyInfo requires components to be selected.
        cmds.select(boundary_edge)
        # Uses PolyInfo to retrieve Vertices.
        # PolyInfo Output: ['EDGE    205:     68     67  Hard\n']
        # Regex Cleanup: ['EDGE', '205', '68', '67', 'Hard'] then Slice Array to Ignore first 2 indexes and the last one.
        boundary_edge_vertices = re.findall(r"[\w]+", cmds.polyInfo(ev=True)[0])[2:-1]

        for vertex in boundary_edge_vertices:
            boundary_vertex_list.append(f"{object_name}.vtx[{vertex}]")

    return boundary_vertex_list

def get_corner_vertex_by_angle(object, detection_degree_threshold, boundary_edge_list):
    object_name = object.get("name")
    object_corner_list = []
    boundary_vertices = _boundary_edges_to_vertices(object_name, boundary_edge_list)
    
    for boundary_vertex in boundary_vertices:
        vector_list = []
        connected_border_edges = _get_edges_connected_to_vertex(boundary_vertex, object_name, boundary_edge_list)
        for connected_border_edge in connected_border_edges:
            vector_list.append(_calculate_vector_from_vertices(object, connected_border_edge, object_name))

        if vector_list:
            corner_angle = vector_list[0].angle(vector_list[1])

            if math.degrees(corner_angle) > detection_degree_threshold:
                if boundary_vertex not in object_corner_list:
                    object_corner_list.append(boundary_vertex)

    return object_corner_list

def _calculate_vector_from_vertices(object, connected_border_edge, object_name):
    start_vertex, end_vertex = _set_start_end_vector_vertices(connected_border_edge, object_name)
    start_point = object.get("mesh_component").getPoint(int(start_vertex))
    end_point = object.get("mesh_component").getPoint(int(end_vertex))
    
    return start_point - end_point

def _get_edges_connected_to_vertex(boundary_vertex, object_name, boundary_edge_list):
    # PolyInfo requires components to be selected.
    cmds.select(boundary_vertex)
    # Uses PolyInfo to retrieve Vertices.
    # PolyInfo Output: ['EDGE    205:     68     67  Hard\n']
    # Regex Cleanup: ['EDGE', '205', '68', '67', 'Hard'] then Slice Array to Ignore first 2 indexes and the last one.
    connected_edges = re.findall(r"[\w]+", cmds.polyInfo(ve=True)[0])[2:]
    # List Comprehension to format connected edges (list of indexes) to Maya edge component (polySurface.e[index]).
    formatted_connected_edges = [f"{object_name}.e[{edge_index}]" for edge_index in connected_edges]
    # List Intersection to get only onBoundary edges to calculate vectors.
    connected_border_edges = list(set(formatted_connected_edges) & set(boundary_edge_list))

    cmds.select(cl=True)
    return connected_border_edges

def _set_start_end_vector_vertices(connected_border_edge, object_name):
    cmds.select(connected_border_edge)
    vector_vertices = re.findall("[\w]+", cmds.polyInfo(ev=True)[0])[2:-1]
    
    cmds.select(cl=True)
    return vector_vertices[0], vector_vertices[1]


if __name__ == "__main__":
    main(geometry_list=cmds.ls(sl=True), detection_degree_threshold=50)
