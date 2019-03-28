import os
import logging
from warnings import catch_warnings
from urllib.parse import urlparse

import numpy as np
from AnyQt.QtWidgets import \
    QStyle, QComboBox, QMessageBox, QGridLayout, QLabel, \
    QLineEdit, QSizePolicy as Policy
from AnyQt.QtCore import Qt, QTimer, QSize

from Orange.canvas.gui.utils import OSX_NSURL_toLocalFile
from Orange.data.table import Table, get_sample_datasets_dir
from Orange.data.io import FileFormat, UrlReader, class_from_qualified_name
from Orange.widgets import widget, gui
from Orange.widgets.settings import Setting, ContextSetting, \
    PerfectDomainContextHandler, SettingProvider
from Orange.widgets.utils.Newdomaineditor import DomainEditor
# from Orange.widgets.utils.Mydomaineditor import DomainEditor
from Orange.widgets.utils.itemmodels import PyListModel
from Orange.widgets.utils.filedialogs import RecentPathsWComboMixin, \
    open_filename_dialog
from Orange.widgets.widget import Output

# Backward compatibility: class RecentPath used to be defined in this module,
# and it is used in saved (pickled) settings. It must be imported into the
# module's namespace so that old saved settings still work
from Orange.widgets.utils.filedialogs import RecentPath


log = logging.getLogger(__name__)

## 主要介绍了data.domain.variables 和 data.domain.metas的作用
# 对每个str变量加路径
def add_origin(examples, filename):
    """
    Adds attribute with file location to each string variable
    Used for relative filenames stored in string variables (e.g. pictures)
    TODO: we should consider a cleaner solution (special variable type, ...)
    """
    if not filename:
        return
    vars = examples.domain.variables + examples.domain.metas
    # print('data.domain.variables',examples.domain.variables)
    # print('data.domain.metas',examples.domain.metas)

    strings = [var for var in vars if var.is_string]
    dir_name, _ = os.path.split(filename) #返回文件路径（除去了文件名）
    for var in strings:
        # print('var.attributes',var.attributes)
        if "type" in var.attributes and "origin" not in var.attributes:
            var.attributes["origin"] = dir_name

##与UPL有关模块
class NamedURLModel(PyListModel):
    def __init__(self, mapping):
        self.mapping = mapping
        super().__init__()

    def data(self, index, role):
        data = super().data(index, role)
        if role == Qt.DisplayRole:
            return self.mapping.get(data, data)
        return data

    def add_name(self, url, name):
        self.mapping[url] = name
        self.modelReset.emit()

##???未知class作用
class LineEditSelectOnFocus(QLineEdit):
    def focusInEvent(self, event):
        super().focusInEvent(event)
        # If selectAll is called directly, placing the cursor unselects the text
        QTimer.singleShot(0, self.selectAll)


class OWFile(widget.OWWidget, RecentPathsWComboMixin):
    name = "领域编辑器2"
    icon = "icons/gear.svg"
    id = "orange.widgets.data.file"
    description = "Read data from an input file or network " \
                  "and send a data table to the output."

    priority = 10
    category = "Data"
    keywords = ["file", "load", "read", "open"]

    class Outputs:
        data = Output("领域背景", Table, doc="专业领域背景的介绍")

    want_main_area = False

    SEARCH_PATHS = [("sample-datasets", get_sample_datasets_dir())]
    SIZE_LIMIT = 1e7
    LOCAL_FILE, URL = range(2)

    settingsHandler = PerfectDomainContextHandler(
        match_values=PerfectDomainContextHandler.MATCH_VALUES_ALL
    )

    # Overload RecentPathsWidgetMixin.recent_paths to set defaults
    recent_paths = Setting([
        RecentPath("", "sample-datasets", "iris.tab"),
        RecentPath("", "sample-datasets", "titanic.tab"),
        RecentPath("", "sample-datasets", "housing.tab"),
        RecentPath("", "sample-datasets", "heart_disease.tab"),
    ])
    recent_urls = Setting([])
    source = Setting(LOCAL_FILE)
    xls_sheet = ContextSetting("")
    sheet_names = Setting({})
    url = Setting("")

    variables = ContextSetting([])

    domain_editor = SettingProvider(DomainEditor)

##用于警告代码可以无视
    class Warning(widget.OWWidget.Warning):
        file_too_big = widget.Msg("The file is too large to load automatically."
                                  " Press Reload to load.")
        load_warning = widget.Msg("Read warning:\n{}")
##用于报错代码可以无视
    class Error(widget.OWWidget.Error):
        file_not_found = widget.Msg("File not found.")
        missing_reader = widget.Msg("Missing reader.")
        sheet_error = widget.Msg("Error listing available sheets.")
        unknown = widget.Msg("Read error:\n{}")

    def __init__(self):
        super().__init__()
        RecentPathsWComboMixin.__init__(self)
        self.domain = None
        self.data = None
        self.loaded_file = ""
        self.reader = None

        layout = QGridLayout()  ##画布的布局，使用网格划分的方式
        gui.widgetBox(self.controlArea, margin=20, orientation=layout)
        vbox = gui.radioButtons(None, self, "source", box=True, addSpace=True,
                                callback=self.load_data, addToLayout=False)

        rb_button = gui.appendRadioButton(vbox, "File:", addToLayout=False)
        layout.addWidget(rb_button, 0, 0, Qt.AlignVCenter) #确定位置0,0

        box = gui.hBox(None, addToLayout=False, margin=0) #水平box
        box.setSizePolicy(Policy.MinimumExpanding, Policy.Fixed) #设置size
        self.file_combo.setSizePolicy(Policy.MinimumExpanding, Policy.Fixed) # 按钮和下拉菜单的联合体
        self.file_combo.activated[int].connect(self.select_file) ##使用.connect（功能函数）来实现与功能函数的连接
        box.layout().addWidget(self.file_combo)
        layout.addWidget(box, 0, 1) #确定位置0,1

        file_button = gui.button(
            None, self, '...', callback=self.browse_file, autoDefault=False)
        file_button.setIcon(self.style().standardIcon(QStyle.SP_DirOpenIcon))
        file_button.setSizePolicy(Policy.Maximum, Policy.Fixed)
        layout.addWidget(file_button, 0, 2)

        reload_button = gui.button(
            None, self, "Reload", callback=self.load_data, autoDefault=False)
        reload_button.setIcon(self.style().standardIcon(
            QStyle.SP_BrowserReload))
        reload_button.setSizePolicy(Policy.Fixed, Policy.Fixed)
        layout.addWidget(reload_button, 0, 3)

        ## 含Information的box设置
        box = gui.widgetBox(self.controlArea, "Info")
        self.info = gui.widgetLabel(box, '请设置领域特征')
        # self.warnings = gui.widgetLabel(box, '')

        ##下面几句控制含有table的box
        box = gui.widgetBox(self.controlArea, "双击进行编辑")
        self.domain_editor = DomainEditor(self) ##对table操作的事情在DomainEditor内部定义
        self.editor_model = self.domain_editor.model() ##设置与Apply激活状态有关
        box.layout().addWidget(self.domain_editor)

## Apply 按钮
        box = gui.hBox(self.controlArea)
        # gui.button(
        #     box, self, "Browse documentation datasets",
        #     callback=lambda: self.browse_file(True), autoDefault=False)
        # gui.rubber(box)
        self.apply_button = gui.button(
            box, self, "应用", callback=self.apply_domain_edit)
        self.apply_button.setEnabled(False)
        self.apply_button.setFixedWidth(170)

        # print('editor_model',self.editor_model)
        ## 如果数据改变就激活apply按钮.dataChange表示是否改变数据
        self.editor_model.dataChanged.connect(
            lambda: self.apply_button.setEnabled(True))

        self.set_file_list()  ##设置文件列表中的项
        # Must not call open_file from within __init__. open_file
        # explicitly re-enters the event loop (by a progress bar)

        self.setAcceptDrops(True) ##表示接受响应释放操作

        if self.source == self.LOCAL_FILE:
            last_path = self.last_path()
            if last_path and os.path.exists(last_path) and \
                    os.path.getsize(last_path) > self.SIZE_LIMIT:
                self.Warning.file_too_big()
                return

        ##QTimer.singleShot()表示在s秒后调用一个槽函数（self.load_data）
        QTimer.singleShot(0, self.load_data)


    def sizeHint(self):
        return QSize(600, 550)

    def select_file(self, n):
        assert n < len(self.recent_paths)
        super().select_file(n)
        if self.recent_paths:
            self.source = self.LOCAL_FILE
            self.load_data()
            self.set_file_list()

## 读取文件
    def browse_file(self, in_demos=False):
        if in_demos:
            start_file = get_sample_datasets_dir()
            if not os.path.exists(start_file):
                QMessageBox.information(
                    None, "File",
                    "Cannot find the directory with documentation datasets")
                return
        else:
            start_file = self.last_path() or os.path.expanduser("~/")

        readers = [f for f in FileFormat.formats
                   if getattr(f, 'read', None) and getattr(f, "EXTENSIONS", None)]
        filename, reader, _ = open_filename_dialog(start_file, None, readers)
        if not filename:
            return
        self.add_path(filename)
        if reader is not None:
            self.recent_paths[0].file_format = reader.qualified_name()

        self.source = self.LOCAL_FILE
        self.load_data()

## 获取数据self.data,方式是调用了_try_load函数，并且将数据send到Output的channel中
    # Open a file, create data from it and send it over the data channel
    def load_data(self):
        # We need to catch any exception type since anything can happen in
        # file readers
        self.closeContext() ##重新设置widget 的context
        self.domain_editor.set_domain(None) #把domain设置为None
        self.apply_button.setEnabled(False) #把apply button设置为不可见
        self.clear_messages()
        self.set_file_list()

        ##这句话判断数据导入是否有错误
        error = self._try_load()
        if error:
            error()
            self.data = None
            # self.sheet_box.hide()
            self.Outputs.data.send(None)
            self.info.setText("无数据.")

    ## 导入数据的核心方法：获取self.data数据，同时判断这个出错可能性
    def _try_load(self):
        # pylint: disable=broad-except
        if self.last_path() and not os.path.exists(self.last_path()):
            return self.Error.file_not_found

        try:
            self.reader = self._get_reader() ##这里获取reader
            assert self.reader is not None
        except Exception:
            return self.Error.missing_reader

        try:
            self._update_sheet_combo()
        except Exception:
            return self.Error.sheet_error

        with catch_warnings(record=True) as warnings:
            try:
                data = self.reader.read() ##通过这句话读取数据,这是的data已经是table型数据了
                print('jia',type(data))
            except Exception as ex:
                log.exception(ex)
                return lambda x=ex: self.Error.unknown(str(x))
            if warnings:
                self.Warning.load_warning(warnings[-1].message.args[0])

        self.info.setText(self._describe(data)) #描述info的text

        self.loaded_file = self.last_path() ##描述文档地址

        add_origin(data, self.loaded_file)
        self.data = data
        # print('liangyue',dir(self.data))
        self.openContext(data.domain)

        # print('data',data)
        self.apply_domain_edit()  # sends data

## 获取导入文件的格式
    def _get_reader(self):
        """

        Returns
        -------
        FileFormat
        """
        if self.source == self.LOCAL_FILE:
            path = self.last_path()
            if self.recent_paths and self.recent_paths[0].file_format:
                qname = self.recent_paths[0].file_format
                reader_class = class_from_qualified_name(qname)
                reader = reader_class(path)
                print('reader_class',reader_class)
            else:
                reader = FileFormat.get_reader(path)
                # Return reader instance that can be used to read the file
            if self.recent_paths and self.recent_paths[0].sheet:
                reader.select_sheet(self.recent_paths[0].sheet)

            return reader
        elif self.source == self.URL:
            url = self.url_combo.currentText().strip()
            if url:
                return UrlReader(url)

## 更新file的下拉列表中的内容
    def _update_sheet_combo(self):
        if len(self.reader.sheets) < 2:
            # self.sheet_box.hide()
            self.reader.select_sheet(None)
            return

        self.sheet_combo.clear()
        self.sheet_combo.addItems(self.reader.sheets)
        self._select_active_sheet()
        # self.sheet_box.show()

    def _select_active_sheet(self):
        if self.reader.sheet:
            try:
                idx = self.reader.sheets.index(self.reader.sheet)
                self.sheet_combo.setCurrentIndex(idx)
            except ValueError:
                # Requested sheet does not exist in this file
                self.reader.select_sheet(None)
        else:
            self.sheet_combo.setCurrentIndex(0)

## 下面是info的描述语句
    def _describe(self, table):
        domain = table.domain
        text = ""

        attrs = getattr(table, "attributes", {})
        descs = [attrs[desc]
                 for desc in ("Name", "Description") if desc in attrs]
        if len(descs) == 2:
            descs[0] = "<b>{}</b>".format(descs[0])
        if descs:
            text += "<p>{}</p>".format("<br/>".join(descs))

        text += "<p>{} 个实例数据(s), {} 个输入特征(s), {} 个元特征(s)".\
            format(len(table), len(domain.attributes), len(domain.metas))
        if domain.has_continuous_class:
            text += "<br/>回归模型 ."
        elif domain.has_discrete_class:
            text += "<br/>分类模型; 共分为 {} 类.".\
                format(len(domain.class_var.values))
        elif table.domain.class_vars:
            text += "<br/>多目标模型; {} 个目标".format(
                len(table.domain.class_vars))
        else:
            text += "<br/>无目标值."
        text += "</p>"

        if 'Timestamp' in table.domain:
            # Google Forms uses this header to timestamp responses
            text += '<p>First entry: {}<br/>Last entry: {}</p>'.format(
                table[0, 'Timestamp'], table[-1, 'Timestamp'])
        return text

    def storeSpecificSettings(self):
        self.current_context.modified_variables = self.variables[:]

    def retrieveSpecificSettings(self):
        if hasattr(self.current_context, "modified_variables"):
            self.variables[:] = self.current_context.modified_variables


    ## 对Ourputs的data赋值为table
    def apply_domain_edit(self):
        if self.data is None:
            table = None
        else:
            domain, cols = self.domain_editor.get_domain(self.data.domain, self.data)
            printData = self.data
            printDomain = self.data.domain
            if not (domain.variables or domain.metas):
                table = None
            else:
                X, y, m = cols
                #X是输入，domain.attributes;y是输出class_var;m是元特征
                ## 下面解决将self.data的数据付给了table。
                # 1data's name; 2数据编号ids；3数据属性attributes
                table = Table.from_numpy(domain, X, y, m, self.data.W)
                table.name = self.data.name
                index = self.data.ids
                table.ids = np.array(self.data.ids)
                # print('ids',table.ids)

                data = self.data
                table.attributes = getattr(self.data, 'attributes', {})
                ## 将table的属性定义为{}
                ''' 对Ourputs的data赋值为table'''
        # print('table is :',table)
        # print('table domain',table.domain)
        # print('table name',table.name)
        # print('table class_var name',table.domain.class_vars[0].name)
        self.Outputs.data.send(table)
        self.apply_button.setEnabled(False)

    def get_widget_name_extension(self):
        _, name = os.path.split(self.loaded_file)
        return os.path.splitext(name)[0]

    def send_report(self):
        def get_ext_name(filename):
            try:
                return FileFormat.names[os.path.splitext(filename)[1]]
            except KeyError:
                return "unknown"

        if self.data is None:
            self.report_paragraph("File", "No file.")
            return

        if self.source == self.LOCAL_FILE:
            home = os.path.expanduser("~")
            if self.loaded_file.startswith(home):
                # os.path.join does not like ~
                name = "~" + os.path.sep + \
                       self.loaded_file[len(home):].lstrip("/").lstrip("\\")
            else:
                name = self.loaded_file
            if self.sheet_combo.isVisible():
                name += " ({})".format(self.sheet_combo.currentText())
            self.report_items("File", [("File name", name),
                                       ("Format", get_ext_name(name))])
        else:
            self.report_items("Data", [("Resource", self.url),
                                       ("Format", get_ext_name(self.url))])

        self.report_data("Data", self.data)

    def dragEnterEvent(self, event):
        """Accept drops of valid file urls"""
        urls = event.mimeData().urls()
        if urls:
            try:
                FileFormat.get_reader(OSX_NSURL_toLocalFile(urls[0]) or
                                      urls[0].toLocalFile())
                event.acceptProposedAction()
            except IOError:
                pass

    def dropEvent(self, event):
        """Handle file drops"""
        urls = event.mimeData().urls()
        if urls:
            self.add_path(OSX_NSURL_toLocalFile(urls[0]) or
                          urls[0].toLocalFile())  # add first file
            self.source = self.LOCAL_FILE
            self.load_data()

    def workflowEnvChanged(self, key, value, oldvalue):
        """
        Function called when environment changes (e.g. while saving the scheme)
        It make sure that all environment connected values are modified
        (e.g. relative file paths are changed)
        """
        self.update_file_list(key, value, oldvalue)


if __name__ == "__main__":
    import sys
    from AnyQt.QtWidgets import QApplication
    a = QApplication(sys.argv)
    ow = OWFile()
    ow.show()
    a.exec_()
    ow.saveSettings()
