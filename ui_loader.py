import sys
import os
import xml_parser
import main

from PySide2 import QtCore
from PySide2 import QtUiTools
from PySide2 import QtWidgets
from PySide2 import QtGui
from shiboken2 import wrapInstance

import maya.cmds as cmds
import maya.OpenMayaUI as omui

def maya_main_window():
    """
    Return the Maya main window widget as a Python object
    """
    main_window_ptr = omui.MQtUtil.mainWindow()
    if sys.version_info.major >= 3:
        return wrapInstance(int(main_window_ptr), QtWidgets.QWidget)
    else:
        return wrapInstance(long(main_window_ptr), QtWidgets.QWidget)
    
class Sewing_maya_tool(QtWidgets.QDialog):

    def __init__(self, title, ui_file, parent=maya_main_window()):
        super(Sewing_maya_tool, self).__init__(parent)

        self.setWindowTitle(title)
        self.pattern = 0
        self.init_ui(ui_file)
        self.create_layout()
        self.create_connections()

    def create_connections(self):
        pass

    def init_ui(self, ui_file):
        file = QtCore.QFile(os.path.join(os.path.dirname(__file__), ui_file))
        file.open(QtCore.QFile.ReadOnly)
        loader = QtUiTools.QUiLoader()
        self.ui = loader.load(file, parentWidget=None)
        file.close()

    def create_layout(self):
        main_layout = QtWidgets.QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)
        main_layout.addWidget(self.ui)

    def remove_widget(self):
        self.hide()

class Pattern_Widget(Sewing_maya_tool):
    def create_connections(self):
        pass

    def setup_pattern_info(self):
        for piece in self.pattern:
            piece_tree_item = QtWidgets.QTreeWidgetItem(self.ui.treeWidget)
            piece_tree_item.setText(0, f"piece_{piece.pattern_index:02d}")
            # piece_tree_item.setText(1, f"{piece.current_vertices}")
            piece_tree_item.setText(1, f"{len(piece.vertices)}")
            piece_tree_item.setTextColor(0, QtGui.QColor("red"))
            for index, edge in enumerate(piece.edges):
                edge_tree_child = QtWidgets.QTreeWidgetItem()
                edge_tree_child.setText(0, f"edge_{index:02d}")
                edge_tree_child.setText(1, str(piece.edges[index].boundary_ref_edge))
                piece_tree_item.addChild(edge_tree_child)

class Start_Widget(Sewing_maya_tool):
    def create_connections(self):
        self.ui.createPattern.clicked.connect(self.initialize_pattern_setup)

    def initialize_pattern_setup(self):
        pattern_ui = Pattern_Widget(title="SMT", ui_file="patternList.ui")
        pattern_ui.pattern = main.create_pattern()
        pattern_ui.setup_pattern_info()
        pattern_ui.show()
        self.remove_widget()
    

if __name__ == "__main__":
    designer_ui = Start_Widget(title="SMT", ui_file="SMT.ui")
    designer_ui.show()
    try:
        designer_ui.close() # pylint: disable=E0601
        designer_ui.deleteLater()
    except:
        pass

    
