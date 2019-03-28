from itertools import chain

import numpy as np
import scipy.sparse as sp

from AnyQt.QtCore import Qt, QAbstractTableModel
from AnyQt.QtGui import QColor
from AnyQt.QtWidgets import QComboBox, QTableView, QSizePolicy

from Orange.data import DiscreteVariable, ContinuousVariable, StringVariable, TimeVariable, Domain
from Orange.statistics.util import unique
from Orange.widgets import gui
from Orange.widgets.gui import HorizontalGridDelegate
from Orange.widgets.settings import ContextSetting
from Orange.widgets.utils.itemmodels import TableModel


# 列索引
class Column:
    input_data = 0
    ouput_data = 1
    lower_limit = 2
    upper_limit = 3
    relation = 4
    not_valid = 5


# 经验表格数据模型
class ExperienceModel(QAbstractTableModel):
    # 初始化构造函数
    def __init__(self, variables, input_dict, ouput_dict, *args):
        super().__init__(*args)
        self.variables = variables

        # 输入字典
        self.input_dict = input_dict
        # 输出字典
        self.ouput_dict = ouput_dict
        # 关系字典
        self.relation_dict = "-1", "1"

    # 设置模型的缓存数据
    def set_variables(self, variables):
        self.modelAboutToBeReset.emit()
        self.variables = variables
        self.modelReset.emit()

    # 获得数据行数
    def rowCount(self, parent):
        return 0 if parent.isValid() else len(self.variables)

    # 获得数据列数
    def columnCount(self, parent):
        return 0 if parent.isValid() else Column.not_valid

    # 获得表格单元数据
    def data(self, index, role):
        row, col = index.row(), index.column()
        val = self.variables[row][col]
        # if role == Qt.DisplayRole or role == Qt.EditRole:
        #     return val
        if role == Qt.DisplayRole or role == Qt.EditRole:
            if type(val) == str and (val.isspace() or val == ""):
                return val
            # if col == Column.input_data:
            #     return self.input_dict[val]
            # if col == Column.ouput_data:
            #     return self.ouput_dict[val]
            # if col == Column.relation:
            #     return self.relation_dict[val]
            # else:
            #     return val
            return val

    # 设置表格单元数据
    def setData(self, index, value, role):
        row, col = index.row(), index.column()
        row_data = self.variables[row]
        if role == Qt.EditRole:
            # if (col == Column.lower_limit or col == Column.upper_limit) and not (value.isspace() or value == ""):
            #     row_data[col] = value
            # elif col == Column.input_data:
            #     row_data[col] = self.input_dict.index(value)
            # elif col == Column.ouput_data:
            #     row_data[col] = self.ouput_dict.index(value)
            # elif col == Column.relation:
            #     row_data[col] = self.relation_dict.index(value)
            # else:
            #     return False
            # return True
            if not (value.isspace() or value == ""):
                row_data[col] = value
            else:
                return False
            return True

    # 设置表格列标签
    def headerData(self, i, orientation, role=Qt.DisplayRole):
        if orientation == Qt.Horizontal and role == Qt.DisplayRole and i < Column.not_valid:
            return ("输入","输出","单调下限","单调上限","关系")[i]
        if role == Qt.TextAlignmentRole:
            return Qt.AlignLeft
        return super().headerData(i, orientation, role)

    # 设置表格列编辑状态
    def flags(self, index):
        # if index.column() == Column.values:
        #     return super().flags(index)
        return super().flags(index) | Qt.ItemIsEditable


# 表格下拉框代理类
class ComboDelegate(HorizontalGridDelegate):
    def __init__(self, view, items):
        super().__init__()
        self.view = view
        self.items = items
    
    def createEditor(self, parent, option, index):
        class Combo(QComboBox):
            def __init__(self, *args):
                super().__init__(*args)
                self.popup_shown = False
                self.highlighted_text = None

            def highlight(self, index):
                self.highlighted_text = index

            def showPopup(self, *args):
                super().showPopup(*args)
                self.popup_shown = True

            def hidePopup(me):
                if me.popup_shown:
                    self.view.model().setData(index, me.highlighted_text, Qt.EditRole)
                    self.popup_shown = False
                super().hidePopup()
                self.view.closeEditor(me, self.NoHint)

        combo = Combo(parent)
        combo.highlighted[str].connect(combo.highlight)
        return combo

# 输入数据下拉框代理类
class InputDataDelegate(ComboDelegate):
    def setEditorData(self, combo, index):
        combo.clear()
        combo.addItems(self.items)
        if (index.data().isspace() or index.data() == ""):
            combo.setCurrentIndex(0)
        else:
            combo.setCurrentIndex(self.items.index(index.data()))

# 输出数据下拉框代理类
class OutputDataDelegate(ComboDelegate):
    def setEditorData(self, combo, index):
        combo.clear()
        combo.addItems(self.items)
        if (index.data().isspace() or index.data() == ""):
            combo.setCurrentIndex(0)
        else:
            combo.setCurrentIndex(self.items.index(index.data()))
# 关系下拉框代理类
class RelationDelegate(ComboDelegate):
    def setEditorData(self, combo, index):
        combo.clear()
        combo.addItems(self.items)
        if (index.data().isspace() or index.data() == ""):
            combo.setCurrentIndex(0)
        else:
            combo.setCurrentIndex(self.items.index(index.data()))

# 经验表格编辑器
class ExperienceEditor(QTableView):
    variables = []

    def __init__(self, widget, input_dict, ouput_dict):
        super().__init__()
        # widget.settingsHandler.initialize(self)
        # widget.contextAboutToBeOpened.connect(lambda args: self.set_domain(args[0]))
        # widget.contextOpened.connect(lambda: self.model().set_variables(self.variables))
        # widget.contextClosed.connect(lambda: self.model().set_variables([]))

        # 设置表格数据模型
        emodel = ExperienceModel(self.variables, input_dict, ouput_dict, self)
        self.setModel(emodel)

        # 设置表格样式
        self.setSelectionMode(QTableView.NoSelection)
        self.horizontalHeader().setStretchLastSection(True)
        self.setShowGrid(True)
        self.setEditTriggers(QTableView.SelectedClicked | QTableView.DoubleClicked)
        self.setSizePolicy(QSizePolicy.MinimumExpanding, QSizePolicy.MinimumExpanding)

        # 设置表格数据编辑代理
        self.grid_delegate = HorizontalGridDelegate()
        self.setItemDelegate(self.grid_delegate)

        # 下拉菜单代理
        self.input_delegate = InputDataDelegate(self, emodel.input_dict)
        self.setItemDelegateForColumn(Column.input_data, self.input_delegate)
        self.output_delegate = OutputDataDelegate(self, emodel.ouput_dict)
        self.setItemDelegateForColumn(Column.ouput_data, self.output_delegate)
        self.relation_delegate = RelationDelegate(self,emodel.relation_dict)
        self.setItemDelegateForColumn(Column.relation,self.relation_delegate)


    # 设置表格数据
    def set_data(self, datas):
        self.variables = datas
        self.model().set_variables(self.variables)

    # 初始化数据，空白表格
    def init_data(self, row_number = 5):
        datas = []
        for i in range(row_number):
            row = []
            for j in range(Column.not_valid):
                row.append("")
            datas.append(row)

        self.set_data(datas)
