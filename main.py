import os
import re
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
import xml_parser

class Pattern():

    def __init__(self, geometry, detection_degree_threshold, pattern_index, seam_info, global_vertex_range):
        self.geometry = geometry
        self.detection_degree_threshold = detection_degree_threshold
        self.pattern_index = pattern_index
        self.object = self.init_api_objects(geometry)
        self.border_edge = self.get_boundary_edges()
        self.vertices = self.get_corner_vertex_by_angle(self.border_edge)
        self.min_vertex, self.max_vertex = self.find_min_max_vertices()
        self.seams = self.find_seam_by_vertices(seam_info)
        self.global_vertex_range = global_vertex_range
        self.current_vertices = 0
        self.create()

    def find_seam_by_vertices(self, seam_info):
        pattern_seams = []
        for seam_dict in seam_info:
            seam_vertices = seam_dict["start_line"]
            for seam_vertex in seam_vertices:
                if self.min_vertex < int(seam_vertex) < self.max_vertex:
                    pattern_seams.append(seam_dict)
                    break
        return pattern_seams
    
    def find_min_max_vertices(self):
        return int(self.format_vertex_index(min(self.vertices))[2]), int(self.format_vertex_index(max(self.vertices))[2])

    def init_api_objects(self, geometry):
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

    def get_boundary_edges(self):
        object_mesh_component = self.object.get("mesh_component")
        object_name = self.object.get("name")
        boundary_polygon_list = self._get_boundary_polygons(object_name, object_mesh_component)
        boundary_edge_list = []

        for boundary_polygon in boundary_polygon_list:
            # PolyInfo requires components to be selected.
            cmds.select(boundary_polygon)
            # Uses PolyInfo to retrieve Edges.
            # PolyInfo Output: ['FACE     82:    223    224    225 \n']
            # Regex Cleanup: ['FACE', '82', '223', '224', '225'] then Slice Array to Ignore first 2 indexes.
            polygon_edges = self.format_vertex_index(text=cmds.polyInfo(fe=True)[0])[2:]

            for polygon_edge in polygon_edges:
                if object_mesh_component.edgeBorderInfo(int(polygon_edge)) == -2:
                    boundary_edge_list.append(f"{object_name}.e[{polygon_edge}]")

        cmds.select(cl=True)
        return boundary_edge_list
    
    def get_corner_vertex_by_angle(self, boundary_edge_list):
        object_name = self.object.get("name")
        object_corner_list = []
        boundary_vertices = self._boundary_edges_to_vertices(object_name, boundary_edge_list)
        
        for boundary_vertex in boundary_vertices:
            vector_list = []
            connected_border_edges = self._get_edges_connected_to_vertex(boundary_vertex, object_name, boundary_edge_list)
            for connected_border_edge in connected_border_edges:
                vector_list.append(self._calculate_vector_from_vertices(connected_border_edge, object_name))

            if vector_list:
                corner_angle = vector_list[0].angle(vector_list[1])

                if math.degrees(corner_angle) > self.detection_degree_threshold:
                    if boundary_vertex not in object_corner_list:
                        object_corner_list.append(boundary_vertex)

        return object_corner_list
    
    def create(self):
        # get the mesh vertex position
        self.vertices = self.get_corner_vertex_by_angle(self.border_edge)
        
        polygon_points = []
        polygon_points_sorted = []
        polygon_connects = []
        new_polygon_object = om.MFnMesh()
        for corner_vertex in self.vertices:
            polygon_point = self.format_vertex_index(text=corner_vertex)[2]
            polygon_points_sorted.append(int(polygon_point))

        for index, sorted_vertex in enumerate(sorted(polygon_points_sorted)):
            polygon_points.append(self.object.get("mesh_component").getPoint(int(sorted_vertex)))
            polygon_connects.append(index)

        new_polygon_object.create(polygon_points, [len(polygon_points)], polygon_connects)
        new_polygon_object.updateSurface()
        print(len(polygon_points))
        self.current_vertices = len(polygon_points)

    def _get_boundary_polygons(self, object_name, object_mesh_component):
        object_num_polygons = object_mesh_component.numPolygons
        boundary_polygon_list = []

        for polygon_index in range(0, object_num_polygons):
            if object_mesh_component.onBoundary(polygon_index):
                boundary_polygon_list.append(f"{object_name}.f[{polygon_index}]")

        return boundary_polygon_list

    def _boundary_edges_to_vertices(self, object_name, boundary_edge_list):
        boundary_vertex_list = []
        for boundary_edge in boundary_edge_list:
            # PolyInfo requires components to be selected.
            cmds.select(boundary_edge)
            # Uses PolyInfo to retrieve Vertices.
            # PolyInfo Output: ['EDGE    205:     68     67  Hard\n']
            # Regex Cleanup: ['EDGE', '205', '68', '67', 'Hard'] then Slice Array to Ignore first 2 indexes and the last one.
            boundary_edge_vertices = self.format_vertex_index(text=cmds.polyInfo(ev=True)[0])[2:-1]

            for vertex in boundary_edge_vertices:
                boundary_vertex_list.append(f"{object_name}.vtx[{vertex}]")

        return boundary_vertex_list

    def _calculate_vector_from_vertices(self, connected_border_edge, object_name):
        start_vertex, end_vertex = self._set_start_end_vector_vertices(connected_border_edge, object_name)
        start_point = self.object.get("mesh_component").getPoint(int(start_vertex))
        end_point = self.object.get("mesh_component").getPoint(int(end_vertex))
        
        return start_point - end_point

    def _get_edges_connected_to_vertex(self, boundary_vertex, object_name, boundary_edge_list):
        # PolyInfo requires components to be selected.
        cmds.select(boundary_vertex)
        # Uses PolyInfo to retrieve Vertices.
        # PolyInfo Output: ['EDGE    205:     68     67  Hard\n']
        # Regex Cleanup: ['EDGE', '205', '68', '67', 'Hard'] then Slice Array to Ignore first 2 indexes and the last one.
        connected_edges = self.format_vertex_index(text=cmds.polyInfo(ve=True)[0])[2:]
        # List Comprehension to format connected edges (list of indexes) to Maya edge component (polySurface.e[index]).
        formatted_connected_edges = [f"{object_name}.e[{edge_index}]" for edge_index in connected_edges]
        # List Intersection to get only onBoundary edges to calculate vectors.
        connected_border_edges = list(set(formatted_connected_edges) & set(boundary_edge_list))

        cmds.select(cl=True)
        return connected_border_edges

    def _set_start_end_vector_vertices(self, connected_border_edge, object_name):
        cmds.select(connected_border_edge)
        vector_vertices = re.findall("[\w]+", cmds.polyInfo(ev=True)[0])[2:-1]
        
        cmds.select(cl=True)
        return vector_vertices[0], vector_vertices[1]

    def format_vertex_index(self, text):
        return re.findall(r"[\w]+", text)


def sort_pieces_by_vertex_index():
    sorted_pieces = []
    for geo in cmds.ls(sl=True):
        geometry_index = re.findall(r'[\d]', geo)
        geometry = "".join(geometry_index)
        sorted_pieces.append(int(geometry))
    return sorted(sorted_pieces)

def create_pattern():
    filepath = os.path.join(os.path.dirname(__file__),"smt_exportPattern_002_meta_data.xml")
    seam_info = xml_parser.extract_seams_info(filepath)

    pieces = []
    global_vertex_range = 0
    for index, geometry in enumerate(cmds.ls(sl=True)):
        cmds.select(geometry)
        global_vertex_range += int(cmds.polyEvaluate(v=True))
        piece = Pattern(geometry, detection_degree_threshold=50, pattern_index=index, seam_info=seam_info, global_vertex_range=global_vertex_range)
        pieces.append(piece)
    return pieces

if __name__ == "__main__":
    create_pattern()