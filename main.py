# This Python file uses the following encoding: utf-8
import sys
import subprocess
from pathlib import Path
import json
import threading
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QDoubleSpinBox, QGridLayout, QGroupBox,
                             QMessageBox, QProgressBar)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("UR5e机器人控制界面")
        self.setFont(QFont("Arial", 9))
        # 初始化控制值
        self.ctrl_values = [-1.57, -1.34, 2.65, -1.3, 1.55, 0]  # 默认控制值
        self.control_thread = None
        self.running = False
        self.initUI()

        # 用于更新进度条的定时器
        self.timer = QTimer(self)
        self.timer.timeout.connect(self.update_progress)
        self.progress_value = 0

    def initUI(self):
        # 创建中央控件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 创建关节控制参数面板
        group_box = QGroupBox("关节控制参数 (rad)")
        group_box.setFont(QFont("Arial", 10, QFont.Weight.Bold))
        grid_layout = QGridLayout()

        joint_names = ["基座旋转", "肩部升降", "肘部伸展", "手腕俯仰", "手腕偏转", "手腕旋转"]

        # 创建标签和输入框
        self.spinboxes = []
        for i, name in enumerate(joint_names):
            label = QLabel(f"{name}:")
            label.setFont(QFont("Arial", 9))
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-6.28, 6.28)  # 弧度范围，±360°
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(self.ctrl_values[i])
            spinbox.setFont(QFont("Arial", 9))
            spinbox.valueChanged.connect(self.update_ctrl_value)

            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(spinbox, i, 1)
            self.spinboxes.append(spinbox)

        group_box.setLayout(grid_layout)
        main_layout.addWidget(group_box)

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)
        self.progress_bar.setVisible(False)
        main_layout.addWidget(self.progress_bar)

        # 添加按钮布局
        button_layout = QHBoxLayout()

        startButton = QPushButton("启动仿真")
        startButton.setFont(QFont("Arial", 9))
        startButton.clicked.connect(self.run_mujoco_simulation)

        updateButton = QPushButton("更新参数")
        updateButton.setFont(QFont("Arial", 9))
        updateButton.clicked.connect(self.update_simulation_params)

        stopButton = QPushButton("停止仿真")
        stopButton.setFont(QFont("Arial", 9))
        stopButton.clicked.connect(self.stop_simulation)

        closedLoopButton = QPushButton("闭环控制")
        closedLoopButton.setFont(QFont("Arial", 9))
        closedLoopButton.setStyleSheet("background-color: #4CAF50; color: white;")
        closedLoopButton.clicked.connect(self.start_closed_loop_control)

        button_layout.addWidget(startButton)
        button_layout.addWidget(updateButton)
        button_layout.addWidget(stopButton)
        button_layout.addWidget(closedLoopButton)
        button_layout.addStretch(1)

        main_layout.addLayout(button_layout)

        # 状态标签
        self.status_label = QLabel("就绪")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.status_label.setFont(QFont("Arial", 9, QFont.Weight.Bold))
        main_layout.addWidget(self.status_label)

        # 添加当前动作状态标签
        self.action_label = QLabel("")
        self.action_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.action_label.setFont(QFont("Arial", 9))
        self.action_label.setVisible(False)
        main_layout.addWidget(self.action_label)

        # 添加垂直弹簧使布局居中
        main_layout.addStretch(1)

        # 存储仿真进程
        self.simulation_process = None
        self.closed_loop_active = False

    def update_ctrl_value(self):
        """更新控制值数组"""
        for i in range(6):
            self.ctrl_values[i] = self.spinboxes[i].value()

    def run_mujoco_simulation(self):
        """运行mujoco_simulation.py文件"""
        try:
            # 确保没有其他仿真在运行
            if self.simulation_process and self.simulation_process.poll() is None:
                self.status_label.setText("已有一个仿真在运行")
                return

            # 获取当前脚本所在目录
            script_path = Path(__file__).parent / "mujoco_simulation.py"

            # 创建包含控制参数的临时文件
            self.save_ctrl_params()

            # 在独立的进程中异步执行脚本
            self.simulation_process = subprocess.Popen([sys.executable, str(script_path)])
            self.status_label.setText("仿真运行中...")
            print(f"成功启动Mujoco仿真，参数: {self.ctrl_values}")

        except Exception as e:
            self.status_label.setText(f"错误: {str(e)}")
            print(f"运行仿真失败: {str(e)}")

    def save_ctrl_params(self):
        """保存控制参数到文件"""
        try:
            with open("ctrl_params.json", "w") as f:
                json.dump(self.ctrl_values, f)
            print(f"控制参数已保存: {self.ctrl_values}")
        except Exception as e:
            print(f"保存控制参数失败: {str(e)}")

    def update_simulation_params(self):
        """更新仿真中的控制参数"""
        # 更新内存中的控制值
        self.update_ctrl_value()

        # 保存到文件
        self.save_ctrl_params()

        if self.simulation_process and self.simulation_process.poll() is None:
            self.status_label.setText("参数已更新")
            print(f"仿真参数已更新: {self.ctrl_values}")
        else:
            self.status_label.setText("请先启动仿真")
            print("无法更新参数: 没有运行中的仿真")

    def stop_simulation(self):
        """停止当前运行的仿真"""
        if self.closed_loop_active:
            self.stop_closed_loop_control()

        if self.simulation_process and self.simulation_process.poll() is None:
            self.simulation_process.terminate()
            self.simulation_process = None
            self.status_label.setText("仿真已停止")
            self.action_label.setVisible(False)
            self.progress_bar.setVisible(False)
            print("仿真已停止")
        else:
            self.status_label.setText("没有运行中的仿真")

    def closeEvent(self, event):
        """确保窗口关闭时停止仿真"""
        self.stop_simulation()
        super().closeEvent(event)

    def start_closed_loop_control(self):
        """开始闭环控制"""
        if not self.simulation_process or self.simulation_process.poll() is not None:
            QMessageBox.warning(self, "警告", "请先启动仿真！")
            return

        try:
            with open("closedLoopParams.json", "r") as f:
                trajectory_points = json.load(f)

            if not trajectory_points or len(trajectory_points) == 0:
                QMessageBox.warning(self, "警告", "轨迹点文件为空！")
                return

            # 启动闭环控制线程
            self.closed_loop_active = True
            self.control_thread = threading.Thread(target=self.execute_closed_loop, args=(trajectory_points,))
            self.control_thread.daemon = True
            self.control_thread.start()

            # 显示进度条
            self.progress_bar.setVisible(True)
            self.progress_bar.setValue(0)

            # 显示当前动作标签
            self.action_label.setText("执行闭环控制...")
            self.action_label.setVisible(True)
            self.status_label.setText("执行闭环控制")

            # 启动进度条定时器
            self.timer.start(200)

            print("闭环控制已启动")

        except FileNotFoundError:
            QMessageBox.critical(self, "错误", "找不到 closedLoopParams.json 文件！")
        except json.JSONDecodeError:
            QMessageBox.critical(self, "错误", "无法解析 closedLoopParams.json 文件！")
        except Exception as e:
            QMessageBox.critical(self, "错误", f"发生错误: {str(e)}")

    def stop_closed_loop_control(self):
        """停止闭环控制"""
        self.closed_loop_active = False
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)

        # 停止定时器
        self.timer.stop()
        self.progress_bar.setVisible(False)
        self.action_label.setVisible(False)
        self.status_label.setText("闭环控制已停止")
        print("闭环控制已停止")

    def execute_closed_loop(self, trajectory_points):
        """执行闭环控制轨迹"""
        total_points = len(trajectory_points)
        self.progress_value = 0

        for idx, point in enumerate(trajectory_points):
            if not self.closed_loop_active:
                break

            # 更新界面
            self.action_label.setText(f"移动到位置 {idx + 1}/{total_points}")

            # 保存控制参数
            with open("ctrl_params.json", "w") as f:
                json.dump(point, f)

            # 更新进度
            self.progress_value = int((idx + 1) * 100 / total_points)

            # 等待机械臂移动到该位置（根据实际情况调整）
            time.sleep(2.0)

            print(f"已移动到位置 {idx + 1}/{total_points}: {point}")

        # 完成循环
        if self.closed_loop_active:
            self.action_label.setText("闭环控制完成！")
            self.status_label.setText("闭环控制完成")
            print("闭环控制完成")

            # 等待3秒后恢复状态
            time.sleep(3.0)
            self.status_label.setText("就绪")
            self.action_label.setVisible(False)

        self.closed_loop_active = False

    def update_progress(self):
        """更新进度条显示"""
        self.progress_bar.setValue(self.progress_value)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(100, 100, 600, 500)
    window.show()
    sys.exit(app.exec())