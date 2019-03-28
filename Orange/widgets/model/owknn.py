from AnyQt.QtCore import Qt

from Orange.data import Table
from Orange.modelling import KNNLearner
from Orange.widgets import gui
from Orange.widgets.settings import Setting
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview


class OWKNNLearner(OWBaseLearner):
    name = "KNN"
    description = "根据最近的训练实例进行预测。"
    icon = "icons/KNN.svg"
    replaces = [
        "Orange.widgets.classify.owknn.OWKNNLearner",
        "Orange.widgets.regression.owknnregression.OWKNNRegression",
    ]
    priority = 20
    keywords = ["k nearest", "knearest", "neighbor", "neighbour"]

    LEARNER = KNNLearner

    weights = ["匀实", "距离"]
    metrics = ["欧氏", "曼哈顿", "切比雪夫", "马氏"]

    learner_name = Setting("kNN")
    n_neighbors = Setting(5)
    metric_index = Setting(0)
    weight_index = Setting(0)

    def add_main_layout(self):
        box = gui.vBox(self.controlArea, "邻居")
        self.n_neighbors_spin = gui.spin(
            box, self, "n_neighbors", 1, 100, label="邻居数:",
            alignment=Qt.AlignRight, callback=self.settings_changed,
            controlWidth=80)
        self.metrics_combo = gui.comboBox(
            box, self, "metric_index", orientation=Qt.Horizontal,
            label="距离:", items=[i.capitalize() for i in self.metrics],
            callback=self.settings_changed)
        self.weights_combo = gui.comboBox(
            box, self, "weight_index", orientation=Qt.Horizontal,
            label="分量:", items=[i.capitalize() for i in self.weights],
            callback=self.settings_changed)

    def create_learner(self):
        return self.LEARNER(
            n_neighbors=self.n_neighbors,
            metric=self.metrics[self.metric_index],
            weights=self.weights[self.weight_index],
            preprocessors=self.preprocessors)

    def get_learner_parameters(self):
        return (("Number of neighbours", self.n_neighbors),
                ("Metric", self.metrics[self.metric_index].capitalize()),
                ("Weight", self.weights[self.weight_index].capitalize()))


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWKNNLearner).run(Table("iris"))
