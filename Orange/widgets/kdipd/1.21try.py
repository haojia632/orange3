

import sys
from PyQt5.QtCore import *
from PyQt5.QtWidgets import *
from PyQt5.QtGui import *
import Orange
import numpy as np
from PyQt5.QtWidgets import (QApplication, QHBoxLayout, QItemDelegate, QPushButton,
                             QTableView, QWidget)
from Orange.data.io import FileFormat
from AnyQt.QtCore import Qt, QAbstractTableModel
from Orange.widgets.widget import OWWidget,Output,Input
from Orange.widgets.utils.widgetpreview import WidgetPreview


# data = Orange.data.Table("lenses")

class Table(QWidget):
    name = "经验编辑器"
    id = "orange.widgets.kdipd.editer"
    icon = "icons/DataInfo.svg"

    description = "从输入文档中读取数据" \
                  "并且返回多个添加的经验"
    priority = 7002
    category = "Data"
    keywords = ["file", "load", "read", "open"]

    class Inputs:
        data = Input('数据',Orange.data.Table)
        print('data',data)
    class Outputs:
        sample = Output('定义域',Orange.data.Table)
        print('sample',sample)

    def __init__(self,callback = None):
        super().__init__()
        self.data = None

        self.setWindowTitle('定义域')
        self.resize(500,300)
        self.callback = callback

        lenth = len(self.data.domain.attributes)
        #设置数据层次结构，4行4列
        self.model = QStandardItemModel(lenth,3)
        # self.model = QStandardItem()

        layout = QVBoxLayout()
        #设置水平方向四个头标签文本内容
        horizontalHeadLabels = ['输入', '下限', '上限']
        self.headName = horizontalHeadLabels
        self.model.setHorizontalHeaderLabels(horizontalHeadLabels)

        verticalHeadLabels = [x.name for x in self.data.domain.attributes]
        for row in range(len(verticalHeadLabels)):
                item=QStandardItem(verticalHeadLabels[row])
                self.model.setItem(row,0,item)

        # 实例化表格视图，设置模型为自定义的模型
        self.tableView=QTableView()
        self.tableView.setModel(self.model)
        layout.addWidget(self.tableView)
        self.setLayout(layout)

        # 增加按钮
        read = QPushButton('点击')
        read.clicked.connect(lambda: self.generataTable())
        layout.addWidget(read)


    @Inputs.data
    def set_dataset(self, data):
        """Set the input train dataset."""
        self.data = data

    def _update_table(self):
        self.table.setRowCount(0)
        self.table.setRowCount(len(self.curvePoints))
        self.table.setColumnCount(len(self.learners))

        self.table.setHorizontalHeaderLabels(
            [learner.name for _, learner in self.learners.items()])
        self.table.setVerticalHeaderLabels(
            ["{:.2f}".format(p) for p in self.curvePoints])

    def generataTable(self):
        row = self.model.rowCount()
        column = self.model.columnCount()
        b = []
        for i in range(row):
            a = []
            for j in range(column):
                item = self.model.item(i, j)
                value = item.text()
                a.append(value)
            b.append(a)
        name = [self.headName]
        data = name+b
        Mytable = FileFormat.data_table(data)
        self.Outputs.sample.send(Mytable) #将输出赋给Outputs

        if self.callback:
            self.callback(Mytable)
        else:
            print('there is a error')

# import Orange
# def get_data(Table):
#         data = Table
#         print('data',data)
#         print('data type',type(data))
#
#         print('attribuyes',data.domain.attributes)



if __name__ == "__main__":
    # import sys
    # from AnyQt.QtWidgets import QApplication
    # a = QApplication(sys.argv)
    # ow = Table()
    # ow.show()
    # a.exec_()
    # ow.saveSettings()
    WidgetPreview(Table).run(Orange.data.Table('iris'))


