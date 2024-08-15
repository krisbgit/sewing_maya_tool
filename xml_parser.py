# import maya.cmds as cmds
import re
import xml.etree.ElementTree as etree

def main(file):
    file_root = _read_xml_file(file)
    seam_root = get_seam_info_from_file(file_root)
    seam_info = get_seam_line_attrs(seam_root)
    return seam_info

def _read_xml_file(file):
    parsed_file = etree.parse(file)
    file_root = parsed_file.getroot()

    return file_root


def get_seam_info_from_file(file_root):
    seam_root = _get_seamline_root_tag(file_root)
    return seam_root


def get_seam_line_attrs(seam_root):
    seams_info = []
    for seam in seam_root:
        seam_line_indexes = []
        for seam_line in seam:
            seam_line_indexes.append(seam_line.attrib["MeshPointIndexes"])
        seam_line_info_dict = _build_seam_dict(
            start_line_indexes=re.split("/", seam_line_indexes[0]), 
            end_line_indexes=re.split("/", seam_line_indexes[1])
        )

        seams_info.append(seam_line_info_dict)
    return seams_info

def get_seam_vertex_range(object):
    
    object_range_vertices = re.findall(r"[\w]+", cmds.ls(f'{object}.vtx[:]')[0])
    return object_range_vertices[2:]

# def find_seam_values_by_range(start_range, end_range):
#     for vertex in range(start_range, end_range):


def _build_seam_dict(start_line_indexes, end_line_indexes):
    return {"start_line": start_line_indexes, "end_line": end_line_indexes}


def _get_seamline_root_tag(file_root):

    for child_root in file_root:
        if child_root.tag == "SeamLinePairList":
            return child_root

def extract_seams_info(filepath):
    file_root = _read_xml_file(filepath)
    seam_root = get_seam_info_from_file(file_root)
    seam_info = get_seam_line_attrs(seam_root)
    return seam_info