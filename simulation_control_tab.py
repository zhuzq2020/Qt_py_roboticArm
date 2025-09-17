from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QGridLayout, QGroupBox, 
                            QHBoxLayout, QPushButton, QLabel, QDoubleSpinBox, QListWidget,
                            QProgressBar, QTextEdit, QFileDialog, QLineEdit)
from PyQt6.QtGui import QFont
import sys
import subprocess
from pathlib import Path
import json
import threading
import time
from PyQt6.QtCore import QTimer

class SimulationControlTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.ctrl_values = [0, -1, -1, -1, 0, 0]  # 默认控制值
        self.ctrl_params_label = None
        self.closed_loop_params_label = None
        self.initUI()
        self.set_button_enable_func(False)

        self.progress_timer = QTimer(self)
        self.progress_timer.timeout.connect(self.update_progress)

    def initUI(self):
        """初始化仿真控制选项卡"""
        layout = QHBoxLayout(self)

        tc_box = QGroupBox("遥控")
        layout0 = QVBoxLayout()
        tc_box.setLayout(layout0)

        tm_box = QGroupBox("遥测")
        layout1 = QVBoxLayout()
        tm_box.setLayout(layout1)

        # 添加按钮布局
        button_box = QGroupBox("仿真控制")
        button_layout = QGridLayout()

        startButton = QPushButton("启动仿真")
        startButton.clicked.connect(self.run_mujoco_simulation)

        stopButton = QPushButton("停止仿真")
        stopButton.clicked.connect(self.stop_simulation)

        self.closedLoopButton = QPushButton("闭环控制")
        self.closedLoopButton.clicked.connect(self.start_closed_loop_control)

        self.stopClosedLoopButton = QPushButton("闭环停止")
        self.stopClosedLoopButton.clicked.connect(self.stop_closed_loop_control)

        importButton = QPushButton("导入闭环参数")
        importButton.clicked.connect(self.import_closed_loop_params)

        button_layout.addWidget(startButton, 0, 0, 1, 2)
        button_layout.addWidget(stopButton, 1, 0, 1, 2)
        button_layout.addWidget(importButton, 2, 0, 1, 2)
        button_layout.addWidget(self.closedLoopButton, 3, 0)
        button_layout.addWidget(self.stopClosedLoopButton, 3, 1)

        button_box.setLayout(button_layout)
        layout0.addWidget(button_box)

        # 创建关节控制参数面板
        group_box = QGroupBox("开环控制参数 (rad)")
        grid_layout = QGridLayout()

        joint_names = ["基座旋转", "肩部升降", "肘部伸展", "手腕俯仰", "手腕偏转", "手腕旋转"]

        # 创建标签和输入框
        self.spinboxes = []
        for i, name in enumerate(joint_names):
            label = QLabel(f"{name}:")
            spinbox = QLineEdit(str(self.ctrl_values[i]))

            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(spinbox, i, 1)
            self.spinboxes.append(spinbox)

        self.updateButton = QPushButton("开环控制")
        self.updateButton.clicked.connect(self.update_simulation_params)
        
        grid_layout.addWidget(self.updateButton, 6, 0, 1, 2)

        group_box.setLayout(grid_layout)
        layout0.addWidget(group_box)

        # 参数显示布局
        params_box = QGroupBox("参数显示")
        params_layout = QGridLayout()
        
        # ctrl_params.json 显示
        ctrl_label = QLabel("开环控制参数")
        self.ctrl_params_label = QLabel()
        
        # closedLoopParams.json 显示
        closed_loop_label = QLabel("闭环控制参数")
        self.closed_loop_params_label = QListWidget()
        
        params_layout.addWidget(ctrl_label, 0, 0)
        params_layout.addWidget(self.ctrl_params_label, 0, 1)
        params_layout.addWidget(closed_loop_label, 1, 0)
        params_layout.addWidget(self.closed_loop_params_label, 1, 1)
        
        params_box.setLayout(params_layout)
        layout1.addWidget(params_box)

        # 添加进度条
        progress_box = QGroupBox("闭环控制进度条")
        progress_layout = QGridLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.progress_bar)
        progress_box.setLayout(progress_layout)
        
        layout1.addWidget(progress_box)

        # 仿真状态
        show_box = QGroupBox("仿真状态")
        show_layout = QGridLayout()

        clearShowButton = QPushButton("清空数据")
        clearShowButton.clicked.connect(self.clear_show_func)

        self.show_list = QListWidget()

        show_layout.addWidget(clearShowButton)
        show_layout.addWidget(self.show_list)
        show_box.setLayout(show_layout)
        
        layout1.addWidget(show_box)

        layout.addWidget(tc_box)
        layout.addWidget(tm_box) 

        # 存储仿真进程
        self.simulation_process = None
        self.closed_loop_active = False

    def update_ctrl_value(self):
        """更新控制值数组"""
        for i in range(6):
            try:
                # 获取输入值
                value = float(self.spinboxes[i].text())
                
                # 检查值是否在有效范围内
                if abs(value) > 6.28:
                    # 弹出错误提示框
                    from PyQt6.QtWidgets import QMessageBox
                    QMessageBox.critical(
                        self, 
                        "输入错误", 
                        f"值 {value} 超出范围 (-6.28 到 6.28)，请重新输入！"
                    )
                    # 重置为默认值
                    self.spinboxes[i].setText(str(self.ctrl_values[i]))
                    return False
                
                # 更新控制值
                self.ctrl_values[i] = value
                
            except ValueError:
                # 处理非数字输入
                from PyQt6.QtWidgets import QMessageBox
                QMessageBox.critical(
                    self, 
                    "输入错误", 
                    "请输入有效的数字！"
                )
                # 重置为默认值
                self.spinboxes[i].setText(str(self.ctrl_values[i]))
                return False
        return True

    def run_mujoco_simulation(self):
        """运行mujoco_simulation.py文件"""
        try:
            # 确保没有其他仿真在运行
            if self.simulation_process and self.simulation_process.poll() is None:
                self.show_list.addItem("已有一个仿真在运行")
                self.show_list.scrollToBottom()
                return

            # 获取当前脚本所在目录
            script_path = Path(__file__).parent / "mujoco_simulation.py"

            # 创建包含控制参数的临时文件
            self.save_ctrl_params()

            # 在独立的进程中异步执行脚本
            self.simulation_process = subprocess.Popen([sys.executable, str(script_path)])
            self.show_list.addItem(f"成功启动Mujoco仿真，参数: {self.ctrl_values}")
            self.show_list.scrollToBottom()

            self.set_button_enable_func(True)

        except Exception as e:
            self.show_list.addItem(f"运行仿真失败: {str(e)}")
            self.show_list.scrollToBottom()

    def save_ctrl_params(self):
        """保存控制参数到文件"""
        try:
            with open("ctrl_params.json", "w") as f:
                json.dump(self.ctrl_values, f)
            self.show_list.addItem(f"控制参数已保存: {self.ctrl_values}")
            self.show_list.scrollToBottom()

            self.update_params_display()
        except Exception as e:
            self.show_list.addItem(f"保存控制参数失败: {str(e)}")
            self.show_list.scrollToBottom()

    def update_simulation_params(self):
        """更新仿真中的控制参数"""
        # 更新内存中的控制值
        if self.update_ctrl_value():
            return

        # 保存到文件
        self.save_ctrl_params()

        if self.simulation_process and self.simulation_process.poll() is None:
            self.show_list.addItem(f"仿真参数已更新: {self.ctrl_values}")
            self.show_list.scrollToBottom()
        else:
            self.show_list.addItem("请先启动仿真")
            self.show_list.scrollToBottom()            

    def stop_simulation(self):
        """停止当前运行的仿真"""
        if self.closed_loop_active:
            self.stop_closed_loop_control()

        if self.simulation_process and self.simulation_process.poll() is None:
            self.simulation_process.terminate()
            self.simulation_process = None
            self.show_list.addItem("仿真已停止")
            self.show_list.scrollToBottom()

            self.set_button_enable_func(False)    
        else:
            self.show_list.addItem("没有运行中的仿真")
            self.show_list.scrollToBottom()    

    def start_closed_loop_control(self):
        """开始闭环控制"""
        if not self.simulation_process or self.simulation_process.poll() is not None:
            self.show_list.addItem("请先启动仿真！")
            self.show_list.scrollToBottom()
            return

        try:
            with open("closedLoopParams.json", "r") as f:
                trajectory_points = json.load(f)

            if not trajectory_points or len(trajectory_points) == 0:
                self.show_list.addItem("轨迹点文件为空！")
                self.show_list.scrollToBottom()
                return

            self.update_params_display()

            # 显示进度条
            self.progress_bar.setValue(0)
            self.progress_timer.start(100)

            # 显示当前动作标签
            self.show_list.addItem("执行闭环控制")
            self.show_list.scrollToBottom() 

            # 启动闭环控制线程
            self.closed_loop_active = True
            self.control_thread = threading.Thread(target=self.execute_closed_loop, args=(trajectory_points,))
            self.control_thread.daemon = True
            self.control_thread.start()

        except FileNotFoundError:
            self.show_list.addItem("找不到 closedLoopParams.json 文件！")
            self.show_list.scrollToBottom()
        except json.JSONDecodeError:
            self.show_list.addItem("无法解析 closedLoopParams.json 文件！")
            self.show_list.scrollToBottom()
        except Exception as e:
            self.show_list.addItem(f"发生错误: {str(e)}")
            self.show_list.scrollToBottom()

    def stop_closed_loop_control(self):
        """停止闭环控制"""
        self.closed_loop_active = False
        if self.control_thread and self.control_thread.is_alive():
            self.control_thread.join(timeout=1.0)

        # 停止定时器
        self.progress_timer.stop()
            
        self.show_list.addItem("闭环控制已停止")
        self.show_list.scrollToBottom() 

    def execute_closed_loop(self, trajectory_points):
        """执行闭环控制轨迹"""
        total_points = len(trajectory_points)
        self.progress_value = 0

        for idx, point in enumerate(trajectory_points):
            if not self.closed_loop_active:
                break

            # 更新界面
            self.show_list.addItem(f"移动到位置 {idx + 1}/{total_points}")
            self.show_list.scrollToBottom()            

            # 保存控制参数
            with open("ctrl_params.json", "w") as f:
                json.dump(point, f)

            # 更新进度
            self.progress_value = int((idx + 1) * 100 / total_points)

            # 等待机械臂移动到该位置（根据实际情况调整）
            time.sleep(2.0)

        # 完成循环
        if self.closed_loop_active:
            self.show_list.addItem("闭环控制已完成")
            self.show_list.scrollToBottom() 

        self.closed_loop_active = False

    def update_progress(self):
        """更新进度条显示"""
        self.progress_bar.setValue(self.progress_value)

    def update_params_display(self):
        """更新参数显示标签"""
        try:
            # 更新ctrl_params显示
            with open("ctrl_params.json", "r") as f:
                ctrl_data = json.load(f)
            self.ctrl_params_label.setText(str(ctrl_data))
            
            # 更新closedLoopParams显示
            with open("closedLoopParams.json", "r") as f:
                closed_loop_data = json.load(f)
            # 清空列表并添加新数据
            self.closed_loop_params_label.clear()
            for row in closed_loop_data:
                # 将每个点的数据格式化为字符串
                formatted_row = ", ".join([f"{item:.4f}" for item in row])
                self.closed_loop_params_label.addItem(formatted_row)
        except Exception as e:
            self.show_list.addItem(f"更新参数显示失败: {str(e)}")
            self.show_list.scrollToBottom()

    def import_closed_loop_params(self):
        """导入闭环控制参数文件"""
        # 打开文件对话框
        file_path, _ = QFileDialog.getOpenFileName(
            self, 
            "选择闭环参数文件", 
            "", 
            "文本文件 (*.txt);;JSON文件 (*.json);;所有文件 (*)"
        )
        
        if not file_path:
            return  # 用户取消了选择
        
        try:
            # 读取文件内容
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # 尝试解析JSON
            try:
                data = json.loads(content)
            except json.JSONDecodeError:
                # 如果直接解析失败，尝试处理可能的格式问题
                # 例如：去掉注释、处理单引号等
                content = self.sanitize_json(content)
                data = json.loads(content)
            
            # 验证数据格式
            if not isinstance(data, list) or not all(isinstance(item, list) for item in data):
                raise ValueError("数据格式不正确，应为二维数组")
            
            # 保存到closedLoopParams.json
            with open("closedLoopParams.json", 'w') as f:
                json.dump(data, f, indent=4)
            
            # 更新显示
            self.update_params_display()
            
            # 显示成功消息
            self.show_list.addItem(f"成功导入闭环参数文件: {Path(file_path).name}")
            self.show_list.scrollToBottom()
            
        except Exception as e:
            self.show_list.addItem(f"导入失败: {str(e)}")
            self.show_list.scrollToBottom()

    def sanitize_json(self, content):
        """清理JSON内容，使其可解析"""
        # 移除单行注释
        lines = content.split('\n')
        cleaned_lines = []
        for line in lines:
            # 移除行尾注释
            if '//' in line:
                line = line.split('//')[0]
            # 移除行内注释
            if '#' in line:
                line = line.split('#')[0]
            cleaned_lines.append(line.strip())
        
        # 重新组合
        cleaned_content = '\n'.join(cleaned_lines)
        
        # 替换单引号为双引号
        cleaned_content = cleaned_content.replace("'", '"')
        
        # 尝试解析
        try:
            json.loads(cleaned_content)
            return cleaned_content
        except json.JSONDecodeError:
            # 如果仍然失败，尝试添加缺失的逗号
            # 这是一个简化的处理，实际可能需要更复杂的解析
            cleaned_content = cleaned_content.replace('}\n{', '},\n{')
            cleaned_content = cleaned_content.replace(']\n[', '],\n[')
            return cleaned_content
        
    def clear_show_func(self):
        self.show_list.clear()

    def set_button_enable_func(self, state):
        self.updateButton.setEnabled(state)
        self.closedLoopButton.setEnabled(state)
        self.stopClosedLoopButton.setEnabled(state)