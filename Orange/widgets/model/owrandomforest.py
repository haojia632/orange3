from AnyQt.QtCore import Qt

from Orange.data import Table
from Orange.modelling import RandomForestLearner
from Orange.widgets import settings, gui
from Orange.widgets.utils.owlearnerwidget import OWBaseLearner
from Orange.widgets.utils.widgetpreview import WidgetPreview
from Orange.widgets.widget import Msg


class OWRandomForest(OWBaseLearner):
    name = "随机森林"
    description = "使用一组决策树进行预测。"
    icon = "icons/RandomForest.svg"
    replaces = [
        "Orange.widgets.classify.owrandomforest.OWRandomForest",
        "Orange.widgets.regression.owrandomforestregression.OWRandomForestRegression",
    ]
    priority = 40
    keywords = []

    LEARNER = RandomForestLearner

    n_estimators = settings.Setting(10)
    max_features = settings.Setting(5)
    use_max_features = settings.Setting(False)
    random_state = settings.Setting(0)
    use_random_state = settings.Setting(False)
    max_depth = settings.Setting(3)
    use_max_depth = settings.Setting(False)
    min_samples_split = settings.Setting(5)
    use_min_samples_split = settings.Setting(True)
    index_output = settings.Setting(0)

    class Error(OWBaseLearner.Error):
        not_enough_features = Msg("属性数量不足 ({})")

    def add_main_layout(self):
        box = gui.vBox(self.controlArea, '基本属性')
        self.n_estimators_spin = gui.spin(
            box, self, "n_estimators", minv=1, maxv=10000, controlWidth=80,
            alignment=Qt.AlignRight, label="树个数: ",
            callback=self.settings_changed)
        self.max_features_spin = gui.spin(
            box, self, "max_features", 2, 50, controlWidth=80,
            label="每次拆分时考虑的属性数: ",
            callback=self.settings_changed, checked="use_max_features",
            checkCallback=self.settings_changed, alignment=Qt.AlignRight,)
        self.random_state_spin = gui.spin(
            box, self, "random_state", 0, 2 ** 31 - 1, controlWidth=80,
            label="随机发生器的固定种子: ", alignment=Qt.AlignRight,
            callback=self.settings_changed, checked="use_random_state",
            checkCallback=self.settings_changed)

        box = gui.vBox(self.controlArea, "生长控制")
        self.max_depth_spin = gui.spin(
            box, self, "max_depth", 1, 50, controlWidth=80,
            label="单株树极限深度: ", alignment=Qt.AlignRight,
            callback=self.settings_changed, checked="use_max_depth",
            checkCallback=self.settings_changed)
        self.min_samples_split_spin = gui.spin(
            box, self, "min_samples_split", 2, 1000, controlWidth=80,
            label="拆分不要小于: ",
            callback=self.settings_changed, checked="use_min_samples_split",
            checkCallback=self.settings_changed, alignment=Qt.AlignRight)

    def create_learner(self):
        common_args = {"n_estimators": self.n_estimators}
        if self.use_max_features:
            common_args["max_features"] = self.max_features
        if self.use_random_state:
            common_args["random_state"] = self.random_state
        if self.use_max_depth:
            common_args["max_depth"] = self.max_depth
        if self.use_min_samples_split:
            common_args["min_samples_split"] = self.min_samples_split

        return self.LEARNER(preprocessors=self.preprocessors, **common_args)

    def check_data(self):
        self.Error.not_enough_features.clear()
        if super().check_data():
            n_features = len(self.data.domain.attributes)
            if self.use_max_features and self.max_features > n_features:
                self.Error.not_enough_features(n_features)
                self.valid_data = False
        return self.valid_data

    def get_learner_parameters(self):
        """Called by send report to list the parameters of the learner."""
        return (
            ("Number of trees", self.n_estimators),
            ("Maximal number of considered features",
             self.max_features if self.use_max_features else "unlimited"),
            ("Fixed random seed", self.use_random_state and self.random_state),
            ("Maximal tree depth",
             self.max_depth if self.use_max_depth else "unlimited"),
            ("Stop splitting nodes with maximum instances",
             self.min_samples_split if self.use_min_samples_split else "unlimited")
        )


if __name__ == "__main__":  # pragma: no cover
    WidgetPreview(OWRandomForest).run(Table("iris"))
