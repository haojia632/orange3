"""Naive Bayes Learner
"""

from Orange.data import Table
from Orange.classification.naive_bayes import NaiveBayesLearner
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.settings import Setting

class OWNaiveBayes(OWBaseLearner):
    name = "朴素贝叶斯分类器"
    description = "基于贝叶斯定理的特征独立假设的快速简单概率分类器。"
    icon = "icons/NaiveBayes.svg"
    replaces = [
        "Orange.widgets.classify.ownaivebayes.OWNaiveBayes",
    ]
    priority = 70
    keywords = []

    LEARNER = NaiveBayesLearner
    learner_name = Setting("朴素贝叶斯分类器")

if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWNaiveBayes).run(Table("iris"))
