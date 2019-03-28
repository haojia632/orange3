from Orange.data import Table
from Orange.modelling.constant import ConstantLearner
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.settings import Setting

class OWConstant(OWBaseLearner):
    name = "常数"
    description = "从训练集预测最频繁的课程或平均值。"
    icon = "icons/Constant.svg"
    replaces = [
        "Orange.widgets.classify.owmajority.OWMajority",
        "Orange.widgets.regression.owmean.OWMean",
    ]
    priority = 10
    keywords = ["majority", "mean"]

    LEARNER = ConstantLearner

    learner_name = Setting("常数")

if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWConstant).run(Table("iris"))
