from collections import OrderedDict
import threading
import textwrap

from AnyQt import QtWidgets

from Orange.widgets import widget, gui
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Input
from Orange.data.table import Table
from Orange.data import StringVariable, DiscreteVariable, ContinuousVariable
from Orange.widgets import report
try:
    from Orange.data.sql.table import SqlTable
except ImportError:
    SqlTable = None


class OWDataInfo(widget.OWWidget):
    name = "数据信息"
    id = "orange.widgets.data.info"
    description = "显示数据集相关信息， 例如：列中变量的数量和类型以及行数。"
    icon = "icons/DataInfo.svg"
    priority = 80
    category = "Data"
    keywords = ["information", "inspect"]

    class Inputs:
        data = Input("数据", Table)

    want_main_area = False

    def __init__(self):
        super().__init__()

        self._clear_fields()

        boxs = [("Data Set Name", "数据集名称"), 
                ("Data Set Size", "数据集大小"),
                ("Features", "特征"),
                ("Targets", "目标"),
                ("Meta Attributes", "元特征"),
                ("Location", "位置"),
                ("Data Attributes", "数据属性"),
               ]

        for i, (box, label) in enumerate(boxs):
        # for box in ("Data Set Name", "Data Set Size", "Features", "Targets",
        #             "Meta Attributes", "Location", "Data Attributes"):
            name = box.lower().replace(" ", "_")
            bo = gui.vBox(self.controlArea, label,
                          addSpace=False and box != "Meta Attributes")
            gui.label(bo, self, "%%(%s)s" % name)

        # ensure the widget has some decent minimum width.
        self.targets = "Categorical outcome with 123 values"
        self.layout().activate()
        # NOTE: The minimum width is set on the 'contained' widget and
        # not `self`. The layout will set a fixed size to `self` taking
        # into account the minimum constraints of the children (it would
        # override any minimum/fixed size set on `self`).
        self.targets = ""
        self.controlArea.setMinimumWidth(self.controlArea.sizeHint().width())
        self.layout().setSizeConstraint(QtWidgets.QLayout.SetFixedSize)


    @Inputs.data
    def data(self, data):
        if data is None:
            self._clear_fields()
        else:
            self._set_fields(data)
            self._set_report(data)

    def _clear_fields(self):
        self.data_set_name = ""
        self.data_set_size = ""
        self.features = self.targets = self.meta_attributes = ""
        self.location = ""
        self.data_desc = None
        self.data_attributes = ""

    @staticmethod
    def _count(s, tpe):
        return sum(isinstance(x, tpe) for x in s)

    def _set_fields(self, data):
        def n_or_none(n):
            return n or "-"

        def pack_table(info):
            return '<table>\n' + "\n".join(
                '<tr><td align="right" width="90">{}:</td>\n'
                '<td width="40">{}</td></tr>\n'.format(
                    d,
                    textwrap.shorten(str(v), width=30, placeholder="..."))
                for d, v in info
            ) + "</table>\n"

        def pack_counts(s, include_non_primitive=False):
            if not s:
                return "无"
            return pack_table(
                (name, n_or_none(self._count(s, type_)))
                for name, type_ in (
                    ("类别", DiscreteVariable),
                    ("数字", ContinuousVariable),
                    ("文本", StringVariable))[:2 + include_non_primitive]
            )

        domain = data.domain
        class_var = domain.class_var

        sparseness = [s for s, m in (("features", data.X_density),
                                     ("meta attributes", data.metas_density),
                                     ("targets", data.Y_density)) if m() > 1]
        if sparseness:
            sparseness = "<p>Sparse representation: {}</p>"\
                         .format(", ".join(sparseness))
        else:
            sparseness = ""
        self.data_set_size = pack_table((
            ("行", '~{}'.format(data.approx_len())),
            ("列", len(domain)+len(domain.metas)))) + sparseness

        def update_size():
            self.data_set_size = pack_table((
                ("行", len(data)),
                ("列", len(domain)+len(domain.metas)))) + sparseness

        threading.Thread(target=update_size).start()

        self.data_set_name = getattr(data, "name", "N/A")

        self.features = pack_counts(domain.attributes)
        self.meta_attributes = pack_counts(domain.metas, True)
        if class_var:
            if class_var.is_continuous:
                self.targets = "数值目标变量"
            else:
                self.targets = "{}个值的分类结果".format(len(class_var.values))
        elif domain.class_vars:
            disc_class = self._count(domain.class_vars, DiscreteVariable)
            cont_class = self._count(domain.class_vars, ContinuousVariable)
            if not cont_class:
                self.targets = "多目标数据, {} 个分类目标".format(n_or_none(disc_class))
            elif not disc_class:
                self.targets = "多目标数据,{} 个数字目标".format(n_or_none(cont_class))
            else:
                self.targets = "<p>多目标数据，</p>" + pack_counts(domain.class_vars)
        else:
            self.targets = "无"

        if data.attributes:
            self.data_attributes = pack_table(data.attributes.items())
        else:
            self.data_attributes = ""

    def _set_report(self, data):
        domain = data.domain
        count = self._count

        self.data_desc = dd = OrderedDict()
        dd["Name"] = self.data_set_name

        if SqlTable is not None and isinstance(data, SqlTable):
            connection_string = ' '.join(
                '{}={}'.format(key, value)
                for key, value in data.connection_params.items()
                if value is not None and key != 'password')
            self.location = "表 '{}', 连接:\n{}"\
                            .format(data.table_name, connection_string)
            dd["Rows"] = data.approx_len()
        else:
            self.location = "内存数据"
            dd["Rows"] = len(data)

        def join_if(items):
            return ", ".join(s.format(n) for s, n in items if n)

        dd["Features"] = len(domain.attributes) > 0 and join_if((
            ("{} categorical", count(domain.attributes, DiscreteVariable)),
            ("{} numeric", count(domain.attributes, ContinuousVariable))
        ))
        if domain.class_var:
            name = domain.class_var.name
            if domain.class_var.is_discrete:
                dd["Target"] = "categorical outcome '{}'".format(name)
            else:
                dd["Target"] = "numeric target '{}'".format(name)
        elif domain.class_vars:
            disc_class = count(domain.class_vars, DiscreteVariable)
            cont_class = count(domain.class_vars, ContinuousVariable)
            tt = ""
            if disc_class:
                tt += report.plural("{number} categorical outcome{s}", disc_class)
            if cont_class:
                tt += report.plural("{number} numeric target{s}", cont_class)
        dd["Meta attributes"] = len(domain.metas) > 0 and join_if((
            ("{} categorical", count(domain.metas, DiscreteVariable)),
            ("{} numeric", count(domain.metas, ContinuousVariable)),
            ("{} text", count(domain.metas, StringVariable))
        ))

    def send_report(self):
        if self.data_desc:
            self.report_items(self.data_desc)


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWDataInfo).run(Table("iris"))
