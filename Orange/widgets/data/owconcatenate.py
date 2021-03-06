"""
Concatenate
===========

Concatenate (append) two or more datasets.

"""

from collections import OrderedDict
from functools import reduce

import numpy as np
from AnyQt.QtWidgets import QFormLayout
from AnyQt.QtCore import Qt

import Orange.data
from Orange.util import flatten
from Orange.widgets import widget, gui, settings
from Orange.widgets.settings import Setting
from Orange.widgets.utils.annotated_data import add_columns
from Orange.widgets.utils.sql import check_sql_input
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Input, Output


class OWConcatenate(widget.OWWidget):
    name = "数据合并"
    description = "连接（附加）两个或多个数据集。"
    priority = 1111
    icon = "icons/Concatenate.svg"
    keywords = ["append", "join", "extend"]

    class Inputs:
        primary_data = Input("主要数据", Orange.data.Table)
        additional_data = Input("附加数据",
                                Orange.data.Table,
                                multiple=True,
                                default=True)

    class Outputs:
        data = Output("数据", Orange.data.Table)

    #: Domain merging operations
    MergeUnion, MergeIntersection = 0, 1

    #: Domain role of the "Source ID" attribute.
    ClassRole, AttributeRole, MetaRole = 0, 1, 2

    #: Selected domain merging operation
    merge_type = settings.Setting(0)
    #: Append source ID column
    append_source_column = settings.Setting(False)
    #: Selected "Source ID" domain role
    source_column_role = settings.Setting(0)
    #: User specified name for the "Source ID" attr
    source_attr_name = settings.Setting("资源 ID")

    want_main_area = False
    resizing_enabled = False

    domain_opts = ("所有表中出现的属性的联合",
                   "所有表中属性的交集")

    id_roles = ("类属性", "属性", "元属性")

    auto_commit = Setting(True)

    def __init__(self):
        super().__init__()

        self.primary_data = None
        self.more_data = OrderedDict()

        self.mergebox = gui.vBox(self.controlArea, "领域合并")
        box = gui.radioButtons(
            self.mergebox, self, "merge_type",
            callback=self._merge_type_changed)

        gui.widgetLabel(box, self.tr("当没有主表时，域应该是:"))

        for opts in self.domain_opts:
            gui.appendRadioButton(box, self.tr(opts))

        gui.separator(box)

        label = gui.widgetLabel(
            box,
            self.tr("只有在输入类之间没有冲突时，结果表才会有一个类。"))
        label.setWordWrap(True)

        ###
        box = gui.vBox(
            self.controlArea, self.tr("来源识别"),
            addSpace=False)

        cb = gui.checkBox(
            box, self, "append_source_column",
            self.tr("附加数据源 IDs"),
            callback=self._source_changed)

        ibox = gui.indentedBox(box, sep=gui.checkButtonOffsetHint(cb))

        form = QFormLayout(
            spacing=8,
            labelAlignment=Qt.AlignLeft,
            formAlignment=Qt.AlignLeft,
            fieldGrowthPolicy=QFormLayout.AllNonFixedFieldsGrow
        )

        form.addRow(
            self.tr("特征名称:"),
            gui.lineEdit(ibox, self, "source_attr_name", valueType=str,
                         callback=self._source_changed))

        form.addRow(
            self.tr("地点:"),
            gui.comboBox(ibox, self, "source_column_role", items=self.id_roles,
                         callback=self._source_changed))

        ibox.layout().addLayout(form)
        mleft, mtop, mright, _ = ibox.layout().getContentsMargins()
        ibox.layout().setContentsMargins(mleft, mtop, mright, 4)

        cb.disables.append(ibox)
        cb.makeConsistent()

        box = gui.auto_commit(
            self.controlArea, self, "auto_commit", "应用", commit=self.apply,
            orientation=Qt.Horizontal, checkbox_label="自动应用")
        box.button.setFixedWidth(180)
        box.layout().insertStretch(0)

    @Inputs.primary_data
    @check_sql_input
    def set_primary_data(self, data):
        self.primary_data = data

    @Inputs.additional_data
    @check_sql_input
    def set_more_data(self, data=None, id=None):
        if data is not None:
            self.more_data[id] = data
        elif id in self.more_data:
            del self.more_data[id]

    def handleNewSignals(self):
        self.mergebox.setDisabled(self.primary_data is not None)
        self.apply()

    def apply(self):
        tables, domain, source_var = [], None, None
        if self.primary_data is not None:
            tables = [self.primary_data] + list(self.more_data.values())
            domain = self.primary_data.domain
        elif self.more_data:
            tables = self.more_data.values()
            if self.merge_type == OWConcatenate.MergeUnion:
                domain = reduce(domain_union,
                                (table.domain for table in tables))
            else:
                domain = reduce(domain_intersection,
                                (table.domain for table in tables))

        if tables and self.append_source_column:
            assert domain is not None
            names = [getattr(t, 'name', '') for t in tables]
            if len(names) != len(set(names)):
                names = ['{} ({})'.format(name, i)
                         for i, name in enumerate(names)]
            source_var = Orange.data.DiscreteVariable(
                self.source_attr_name,
                values=names
            )
            places = ["class_vars", "attributes", "metas"]
            domain = add_columns(
                domain,
                **{places[self.source_column_role]: (source_var,)})

        tables = [table.transform(domain) for table in tables]
        if tables:
            data = type(tables[0]).concatenate(tables, axis=0)
            if source_var:
                source_ids = np.array(list(flatten(
                    [i] * len(table) for i, table in enumerate(tables)))).reshape((-1, 1))
                data[:, source_var] = source_ids

        else:
            data = None

        self.Outputs.data.send(data)

    def _merge_type_changed(self, ):
        if self.primary_data is None and self.more_data:
            self.apply()

    def _source_changed(self):
        self.apply()

    def send_report(self):
        items = OrderedDict()
        if self.primary_data is not None:
            items["Domain"] = "from primary data"
        else:
            items["Domain"] = self.tr(self.domain_opts[self.merge_type]).lower()
        if self.append_source_column:
            items["Source data ID"] = "{} (as {})".format(
                self.source_attr_name,
                self.id_roles[self.source_column_role].lower())
        self.report_items(items)


def unique(seq):
    seen_set = set()
    for el in seq:
        if el not in seen_set:
            yield el
            seen_set.add(el)


def domain_union(A, B):
    union = Orange.data.Domain(
        tuple(unique(A.attributes + B.attributes)),
        tuple(unique(A.class_vars + B.class_vars)),
        tuple(unique(A.metas + B.metas))
    )
    return union


def domain_intersection(A, B):
    def tuple_intersection(t1, t2):
        inters = set(t1) & set(t2)
        return tuple(unique(el for el in t1 + t2 if el in inters))

    intersection = Orange.data.Domain(
        tuple_intersection(A.attributes, B.attributes),
        tuple_intersection(A.class_vars, B.class_vars),
        tuple_intersection(A.metas, B.metas),
    )

    return intersection


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWConcatenate).run(
        set_more_data=[(Orange.data.Table("iris"), 0),
                       (Orange.data.Table("zoo"), 1)])
