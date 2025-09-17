import sys
from PyQt6.QtWidgets import (QApplication, QMainWindow, QTabWidget, QWidget, QVBoxLayout)
from robot_control_tab import RobotControlTab
from simulation_control_tab import SimulationControlTab
from PyQt6.QtGui import QFont

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机械臂控制上位机")
        # self.setFont(QFont("Arial", 9))
        self.initUI()

    def initUI(self):
        # 创建中央控件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 机械臂控制选项卡
        self.robot_tab = RobotControlTab(self)
        self.tab_widget.addTab(self.robot_tab, "机械臂控制")

        # 3D仿真控制选项卡
        self.sim_tab = SimulationControlTab(self)
        self.tab_widget.addTab(self.sim_tab, "3D仿真控制")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyleSheet(
        "QPushButton { background-color: lightblue; }"
        "QLineEdit { border: 2px solid lightblue; }"
        "QCheckBox { border: 2px solid lightblue; }"
    )
    window = MainWindow()
    window.setGeometry(200, 50, 400, 600) 
    window.show()
    sys.exit(app.exec())