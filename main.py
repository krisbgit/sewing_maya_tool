import os
import re
import math
import maya.api.OpenMaya as om
import maya.cmds as cmds
import xml_parser

class Edge():
    
    def __init__(self, corners, parent_piece, boundary_ref_edge):
        self.corners = sorted(corners)
        self.parent_piece = parent_piece
        self.boundary_ref_edge = boundary_ref_edge
        self.create_ref_edge()

    def create_ref_edge(self):
        for edge in self.boundary_ref_edge:
            cmds.select(f"{self.parent_piece}.e[{edge}]", add=True)
        cmds.polyToCurve(form=2, degree=1)
        cmds.select(cl=True)
    
class Piece():

    def __init__(self, geometry, detection_degree_threshold, pattern_index, seam_info, global_vertex_range):
        self.geometry = geometry
        self.detection_degree_threshold = detection_degree_threshold
        self.pattern_index = pattern_index
        self.object = self.init_api_objects(geometry)
        self.global_vertex_range = global_vertex_range
        self.border_edge = self.get_boundary_edges()
        self.vertices = self.get_corner_vertex_by_angle(self.border_edge)
        self.seam_info = seam_info
        
        self.edges = self.create_edge_list()
        self.create()

    def create_edge_list(self):
        edges = []
        for index, corner in enumerate(self.vertices):
            start_corner = int(self.format_vertex_index(text=corner)[-1])
            end_corner = int(self.format_vertex_index(text=self.vertices[index-1])[-1])
            edges.append(self.create_edge_object(corners=(start_corner, end_corner)))
        return edges

    def _get_vertex_range_from_edge(self):
        edge_vertices = []
        cmds.select(self.border_edge)
        for vertex_info in cmds.polyInfo(ev=True):
            vertices = re.findall("[\w]+", vertex_info)[2:-1]
            for vertex in vertices:
                edge_vertices.append(int(vertex))
        cmds.select(cl=True)
        return max(edge_vertices)

    def create_edge_object(self, corners):
        ref_edges = []
        end_range= corners[0] if corners[0] != 0 else (self._get_vertex_range_from_edge() + 1)
        start_range = corners[1] + 1
        print(start_range, end_range)
        for vtx in range(start_range, end_range):
            cmds.select(f'{self.geometry}.vtx[{vtx}]')
            ref_edges.extend(self.format_vertex_index(text=cmds.polyInfo(ve=True)[0])[2:])
        
        ref_edges = self.sort_boundary_ref_edge(ref_edges)
        edge = Edge(parent_piece=self.geometry, corners=corners, boundary_ref_edge=ref_edges)
        return edge

    def sort_boundary_ref_edge(self, ref_edges):
        boundary_ref_edges = []
        for edge in list(set(ref_edges)):
            if f"{self.geometry}.e[{edge}]" in self.border_edge:
                boundary_ref_edges.append(int(edge))
        return sorted(boundary_ref_edges)

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

        return self._sort_unformated(object_corner_list, object_name)

    def _sort_unformated(self, list_to_sort, object_name):
        sorted_elements = []
        for element in list_to_sort:
            sorted_elements.append(int(self.format_vertex_index(element)[-1]))
        return [f"{object_name}.vtx[{element}]" for element in sorted(sorted_elements)]

    def create(self):
        
        polygon_points = []
        polygon_points_sorted = []
        polygon_connects = []
        new_polygon_object = om.MFnMesh()
        for corner_vertex in self.vertices:
            polygon_point = self.format_vertex_index(text=corner_vertex)[-1]
            polygon_points_sorted.append(int(polygon_point))

        for index, sorted_vertex in enumerate(sorted(polygon_points_sorted)):
            polygon_points.append(self.object.get("mesh_component").getPoint(int(sorted_vertex)))
            polygon_connects.append(index)

        new_polygon_object.create(polygon_points, [len(polygon_points)], polygon_connects)
        new_polygon_object.updateSurface()

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
        start_vertex, end_vertex = self._set_start_end_vector_vertices(connected_border_edge)
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

    def _set_start_end_vector_vertices(self, connected_border_edge):
        cmds.select(connected_border_edge)
        vector_vertices = self.format_vertex_index(cmds.polyInfo(ev=True)[0])[2:-1]
        
        cmds.select(cl=True)
        return vector_vertices[0], vector_vertices[1]

    def format_vertex_index(self, text):
        return re.findall(r"[\w]+", text)

    def find_seam_by_vertices(self, seam_info, min_vtx, max_vtx):
        pattern_seams = []
        for seam_dict in seam_info:
            seam_vertices = seam_dict["start_line"]
            for seam_vertex in seam_vertices:
                if min_vtx < int(seam_vertex) < max_vtx:
                    pattern_seams.append(seam_dict)
                    break
        return pattern_seams
    
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
        piece = Piece(geometry, detection_degree_threshold=50, pattern_index=index, seam_info=seam_info, global_vertex_range=global_vertex_range)
        pieces.append(piece)
    return pieces

if __name__ == "__main__":
    create_pattern()