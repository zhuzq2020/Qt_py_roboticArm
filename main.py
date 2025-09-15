import sys
import subprocess
from pathlib import Path
import json
import threading
import time
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QPushButton, QLabel, QLineEdit,
                             QDoubleSpinBox, QGridLayout, QGroupBox,
                             QMessageBox, QProgressBar, QTabWidget, QListWidget,
                             QFileDialog, QCheckBox, QTextEdit)
from PyQt6.QtCore import Qt, QTimer
from PyQt6.QtGui import QFont
import pyads

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("机械臂控制上位机")
        self.setFont(QFont("Arial", 9))

        self.motor_count = 7

        # 初始化控制值
        self.ctrl_values = [0, -1, -1, 0, 0, 0]  # 默认控制值
        self.control_thread = None
        self.running = False
        self.initUI()

        # 用于更新进度条的定时器
        self.show_timer = QTimer(self)
        self.show_timer.timeout.connect(self.update_progress)

        # 用于更新机械臂状态的定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_robot_status)

        self.plc = None

    def initUI(self):
        # 创建中央控件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)
        
        # 创建选项卡
        self.tab_widget = QTabWidget()
        main_layout.addWidget(self.tab_widget)
        
        # 机械臂控制选项卡
        robot_tab = QWidget()
        self.init_robot_tab(robot_tab)
        self.tab_widget.addTab(robot_tab, "机械臂控制")

        # 3D仿真控制选项卡
        sim_tab = QWidget()
        self.init_simulation_tab(sim_tab)
        self.tab_widget.addTab(sim_tab, "3D仿真控制")

    def init_simulation_tab(self, tab):
        """初始化仿真控制选项卡"""
        layout = QVBoxLayout(tab)
        
        # 创建关节控制参数面板
        group_box = QGroupBox("关节控制参数 (rad)")
        grid_layout = QGridLayout()

        joint_names = ["基座旋转", "肩部升降", "肘部伸展", "手腕俯仰", "手腕偏转", "手腕旋转"]

        # 创建标签和输入框
        self.spinboxes = []
        for i, name in enumerate(joint_names):
            label = QLabel(f"{name}:")
            spinbox = QDoubleSpinBox()
            spinbox.setRange(-6.28, 6.28)  # 弧度范围，±360°
            spinbox.setDecimals(2)
            spinbox.setSingleStep(0.1)
            spinbox.setValue(self.ctrl_values[i])
            spinbox.valueChanged.connect(self.update_ctrl_value)

            grid_layout.addWidget(label, i, 0)
            grid_layout.addWidget(spinbox, i, 1)
            self.spinboxes.append(spinbox)

        group_box.setLayout(grid_layout)
        layout.addWidget(group_box)

        # 添加进度条
        progress_box = QGroupBox("闭环控制进度条")
        progress_layout = QGridLayout()

        self.progress_bar = QProgressBar()
        self.progress_bar.setRange(0, 100)
        self.progress_bar.setValue(0)

        progress_layout.addWidget(self.progress_bar)
        progress_box.setLayout(progress_layout)
        
        layout.addWidget(progress_box)

        # 添加按钮布局
        button_box = QGroupBox("遥控")
        button_layout = QHBoxLayout()

        startButton = QPushButton("启动仿真")
        startButton.clicked.connect(self.run_mujoco_simulation)

        updateButton = QPushButton("更新参数")
        updateButton.clicked.connect(self.update_simulation_params)

        stopButton = QPushButton("停止仿真")
        stopButton.clicked.connect(self.stop_simulation)

        closedLoopButton = QPushButton("闭环控制")
        closedLoopButton.clicked.connect(self.start_closed_loop_control)

        button_layout.addWidget(startButton)
        button_layout.addWidget(updateButton)
        button_layout.addWidget(stopButton)
        button_layout.addWidget(closedLoopButton)
        # button_layout.addStretch(1)

        button_box.setLayout(button_layout)
        layout.addWidget(button_box)

        # 仿真状态
        tm_box = QGroupBox("仿真状态")
        tm_layout = QGridLayout()

        self.show_list = QListWidget()

        tm_layout.addWidget(self.show_list)
        tm_box.setLayout(tm_layout)
        
        layout.addWidget(tm_box)

        # 存储仿真进程
        self.simulation_process = None
        self.closed_loop_active = False

    def init_robot_tab(self, tab):
        """初始化机械臂控制选项卡"""
        layout = QHBoxLayout(tab)
        layout0 = QVBoxLayout()
        layout1 = QVBoxLayout()
        
        # 连接设置部分
        connection_group = QGroupBox("连接设置")
        connection_layout = QGridLayout()
        
        self.net_id_edit = QLineEdit("10.1.176.253.1.1")
        self.port_edit = QLineEdit("851")
        
        connect_button = QPushButton("连接")
        connect_button.clicked.connect(self.connect_to_robot)
        
        connection_layout.addWidget(QLabel("AMS Net ID:"), 0, 0)
        connection_layout.addWidget(self.net_id_edit, 0, 1)
        connection_layout.addWidget(QLabel("端口:"), 1, 0)
        connection_layout.addWidget(self.port_edit, 1, 1)
        connection_layout.addWidget(connect_button, 2, 0, 1, 2)
        
        connection_group.setLayout(connection_layout)
        layout0.addWidget(connection_group)
        
        # 状态显示部分
        status_group = QGroupBox("机械臂状态")
        status_layout = QGridLayout()
        
        # 创建状态标签
        self.position_labels = []
        self.velocity_labels = []
        self.torque_labels = []
        self.state_labels = []
        self.profile_labels = []
        
        for i in range(self.motor_count):
            motor_num = i + 1
            status_layout.addWidget(QLabel(f"电机 {motor_num}:"), i, 0)
            
            # 位置
            pos_label = QLabel("未知")
            self.position_labels.append(pos_label)
            status_layout.addWidget(QLabel("位置:"), i, 1)
            status_layout.addWidget(pos_label, i, 2)
            
            # 速度
            vel_label = QLabel("未知")
            self.velocity_labels.append(vel_label)
            status_layout.addWidget(QLabel("速度:"), i, 3)
            status_layout.addWidget(vel_label, i, 4)
            
            # 扭矩
            tq_label = QLabel("未知")
            self.torque_labels.append(tq_label)
            status_layout.addWidget(QLabel("扭矩:"), i, 5)
            status_layout.addWidget(tq_label, i, 6)
            
            # 状态
            state_label = QLabel("未知")
            self.state_labels.append(state_label)
            status_layout.addWidget(QLabel("状态:"), i, 7)
            status_layout.addWidget(state_label, i, 8)
            
            # 轮廓状态
            profile_label = QLabel("未知")
            self.profile_labels.append(profile_label)
            status_layout.addWidget(QLabel("轮廓:"), i, 9)
            status_layout.addWidget(profile_label, i, 10)
        
        status_group.setLayout(status_layout)
        layout1.addWidget(status_group)
        
        # 控制按钮部分
        control_group = QGroupBox("电机控制")
        control_layout = QGridLayout()
        
        # 为每个电机创建控制按钮
        self.enable_buttons = []
        self.disable_buttons = []
        self.clear_fault_buttons = []
        self.jog_positive_buttons = []
        self.jog_negative_buttons = []
        self.stop_buttons = []
        self.target_pos_edits = []
        self.target_vel_edits = []
        self.target_acc_edits = []
        self.confirm_buttons = []
        
        for i in range(self.motor_count):
            motor_num = i + 1
            row = i * 2
            
            # 电机标签
            control_layout.addWidget(QLabel(f"电机 {motor_num}:"), row, 0)
            
            # 使能按钮
            enable_btn = QPushButton("使能")
            enable_btn.clicked.connect(lambda _, m=motor_num: self.enable_motor(m))
            self.enable_buttons.append(enable_btn)
            control_layout.addWidget(enable_btn, row, 1)
            
            # 禁止按钮
            disable_btn = QPushButton("禁止")
            disable_btn.clicked.connect(lambda _, m=motor_num: self.disable_motor(m))
            self.disable_buttons.append(disable_btn)
            control_layout.addWidget(disable_btn, row, 2)
            
            # 清除故障按钮
            clear_btn = QPushButton("清除故障")
            clear_btn.clicked.connect(lambda _, m=motor_num: self.clear_motor_fault(m))
            self.clear_fault_buttons.append(clear_btn)
            control_layout.addWidget(clear_btn, row, 3)
            
            # 点动正按钮
            jog_pos_btn = QPushButton("点动+")
            jog_pos_btn.clicked.connect(lambda _, m=motor_num: self.jog_motor(m, True))
            self.jog_positive_buttons.append(jog_pos_btn)
            control_layout.addWidget(jog_pos_btn, row, 4)
            
            # 点动负按钮
            jog_neg_btn = QPushButton("点动-")
            jog_neg_btn.clicked.connect(lambda _, m=motor_num: self.jog_motor(m, False))
            self.jog_negative_buttons.append(jog_neg_btn)
            control_layout.addWidget(jog_neg_btn, row, 5)
            
            # 停止按钮
            stop_btn = QPushButton("停止")
            stop_btn.clicked.connect(lambda _, m=motor_num: self.stop_motor(m))
            self.stop_buttons.append(stop_btn)
            control_layout.addWidget(stop_btn, row, 6)
            
            # 下一行：目标位置、速度、加速度输入
            row += 1
            
            # 目标位置
            pos_edit = QLineEdit("0")
            self.target_pos_edits.append(pos_edit)
            control_layout.addWidget(QLabel("目标位置:"), row, 0)
            control_layout.addWidget(pos_edit, row, 1)
            
            # 目标速度
            vel_edit = QLineEdit("0")
            self.target_vel_edits.append(vel_edit)
            control_layout.addWidget(QLabel("速度:"), row, 2)
            control_layout.addWidget(vel_edit, row, 3)
            
            # 目标加速度
            acc_edit = QLineEdit("0")
            self.target_acc_edits.append(acc_edit)
            control_layout.addWidget(QLabel("加速度:"), row, 4)
            control_layout.addWidget(acc_edit, row, 5)
            
            # 确认按钮
            confirm_btn = QPushButton("确认")
            confirm_btn.clicked.connect(lambda _, m=motor_num: self.confirm_motor_move(m))
            self.confirm_buttons.append(confirm_btn)
            control_layout.addWidget(confirm_btn, row, 6)
        
        control_group.setLayout(control_layout)
        layout0.addWidget(control_group)
        
        # 轨迹控制部分
        trajectory_group = QGroupBox("轨迹控制")
        trajectory_layout = QGridLayout()
        
        self.file_path_edit = QLineEdit()
        browse_button = QPushButton("浏览...")
        browse_button.clicked.connect(self.browse_file)
        
        self.loop_checkbox = QCheckBox("循环执行")
        
        transfer_button = QPushButton("传输轨迹")
        transfer_button.clicked.connect(self.transfer_trajectory)
        
        start_exec_button = QPushButton("开始执行")
        start_exec_button.clicked.connect(self.start_execution)
        
        abort_button = QPushButton("中止执行")
        abort_button.clicked.connect(self.abort_execution)
        
        trajectory_layout.addWidget(QLabel("轨迹文件:"), 0, 0)
        trajectory_layout.addWidget(self.file_path_edit, 0, 1)
        trajectory_layout.addWidget(browse_button, 0, 2)
        trajectory_layout.addWidget(self.loop_checkbox, 1, 0)
        trajectory_layout.addWidget(transfer_button, 1, 1)
        trajectory_layout.addWidget(start_exec_button, 1, 2)
        trajectory_layout.addWidget(abort_button, 1, 3)
        
        trajectory_group.setLayout(trajectory_layout)
        layout0.addWidget(trajectory_group)

        # 控制状态
        output_group = QGroupBox("控制状态")
        output_layout = QGridLayout()

        self.output_list = QListWidget()

        output_layout.addWidget(self.output_list)
        output_group.setLayout(output_layout)

        layout1.addWidget(output_group)

        layout.addLayout(layout0)
        layout.addLayout(layout1) 

    def update_ctrl_value(self):
        """更新控制值数组"""
        for i in range(6):
            self.ctrl_values[i] = self.spinboxes[i].value()

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

        except Exception as e:
            self.show_list.addItem(f"运行仿真失败: {str(e)}")
            self.show_list.scrollToBottom()

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
        else:
            self.show_list.addItem("没有运行中的仿真")
            self.show_list.scrollToBottom()    

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
            self.progress_bar.setValue(0)

            # 显示当前动作标签
            self.show_list.addItem("执行闭环控制")
            self.show_list.scrollToBottom() 

            # 启动进度条定时器
            self.show_timer.start(200)

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
        self.show_timer.stop()
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

            print(f"已移动到位置 {idx + 1}/{total_points}: {point}")

        # 完成循环
        if self.closed_loop_active:
            self.show_list.addItem("闭环控制已完成")
            self.show_list.scrollToBottom() 

        self.closed_loop_active = False

    def update_progress(self):
        """更新进度条显示"""
        self.progress_bar.setValue(self.progress_value)

    ################机械臂控制功能######################
    def connect_to_robot(self):
        """连接到机械臂控制器"""
        net_id = self.net_id_edit.text()
        port_text = self.port_edit.text().strip()
        
        try:
            # 检查是否是十六进制格式（以0x或0X开头）
            if port_text.lower().startswith('0x'):
                # 处理十六进制格式
                port = int(port_text, 16)
            else:
                # 处理十进制格式
                port = int(port_text)
        except ValueError:
            QMessageBox.warning(self, "错误", "端口号必须是整数或十六进制格式（如0x1234）")
            return
            
        try:
            self.plc = pyads.Connection(net_id, port)
            self.plc.open()
            self.connected = True
        except pyads.ADSError as e:
            print(f"连接失败: {e}")
            return
        
        self.status_timer.start(200)  # 每200ms更新一次状态

        self.output_list.addItem(f"已连接到 {net_id}:{port} (0x{port:x})")
        self.output_list.scrollToBottom()
        
    def _read_plc_data(self, var_name_template, plc_type):
        """统一读取PLC数据的模板函数"""
        if not self.plc:
            return [-1.0, -1.0, -1.0, -1.0]

        try:
            values = []
            for i in range(self.motor_count):
                var_name = var_name_template.format(i)
                value = self.plc.read_by_name(var_name, plc_type)
                values.append(value)
            return values
        except pyads.ADSError as e:
            print(f"读取{var_name_template}出错: {e}")
            return [-1.0, -1.0, -1.0, -1.0]
        
    def update_robot_status(self):
        """更新机械臂状态显示"""
        # 获取并显示位置
        positions = self._read_plc_data('MAIN.Position[{}]', pyads.PLCTYPE_DINT)
        for i, pos in enumerate(positions):
            self.position_labels[i].setText(str(pos))
        
        # 获取并显示速度
        velocities = self._read_plc_data('MAIN.Velocity[{}]', pyads.PLCTYPE_REAL)
        for i, vel in enumerate(velocities):
            self.velocity_labels[i].setText(str(vel))
        
        # 获取并显示扭矩
        torques = self._read_plc_data('MAIN.Torque[{}]', pyads.PLCTYPE_REAL)
        for i, tq in enumerate(torques):
            self.torque_labels[i].setText(str(tq))
        
        # 获取并显示状态
        states = self._read_plc_data('MAIN.State[{}]', pyads.PLCTYPE_DINT)
        for i, state in enumerate(states):
            self.state_labels[i].setText(str(state))
        
        # 获取并显示轮廓状态
        profile_states = self._read_plc_data('MAIN.ProfileState[{}]', pyads.PLCTYPE_DINT)
        for i, profile in enumerate(profile_states):
            self.profile_labels[i].setText(str(profile))

    def _execute_command(self, motor_number, command_name, value=1):
        if not self.plc:
            return False
            
        try:
            # 构建变量名：MAIN.CommandName[MotorNumber]
            var_name = f"MAIN.{command_name}[{motor_number}]"
            # 写入命令值（通常1表示执行）
            self.plc.write_by_name(var_name, value, pyads.PLCTYPE_INT)
            return True
        except pyads.ADSError as e:
            print(f"执行{command_name}命令出错: {e}")
            return False
        
    def enable_motor(self, motor_number):
        if self._execute_command(motor_number, "EnableDrive"):
            self.output_list.addItem(f"电机 {motor_number} 已使能")           
        else:
            self.output_list.addItem(f"电机 {motor_number} 使能失败")
        self.output_list.scrollToBottom()

    def disable_motor(self, motor_number):
        if self.communication.disable_drive(motor_number):
            self.output_list.addItem(f"电机 {motor_number} 已禁止")
        else:
            self.output_list.addItem(f"电机 {motor_number} 禁止失败")
        self.output_list.scrollToBottom()

    def clear_motor_fault(self, motor_number):
        if self.communication.clear_drive_fault(motor_number):
            self.output_list.addItem(f"电机 {motor_number} 故障已清除")
        else:
            self.output_list.addItem(f"电机 {motor_number} 故障清除失败")
        self.output_list.scrollToBottom()

    def jog_motor(self, motor_number, is_positive):
        pos = 10.0 if is_positive else -10.0  # 点动距离
        vel = 5.0  # 点动速度
        acc = 10.0  # 加速度
        
        if self.communication.move_drive(motor_number, False, pos, vel, acc):
            direction = "正转" if is_positive else "反转"
            self.output_list.addItem(f"电机 {motor_number} {direction}点动中...")
        else:
            self.output_list.addItem(f"电机 {motor_number} 点动启动失败")
        self.output_list.scrollToBottom()

    def stop_motor(self, motor_number):
        if self.communication.stop_drive(motor_number):
            self.output_list.addItem(f"电机 {motor_number} 已停止")
        else:
            self.output_list.addItem(f"电机 {motor_number} 停止失败")
        self.output_list.scrollToBottom()


    def confirm_motor_move(self, motor_number):
        try:
            idx = motor_number - 1
            pos = float(self.target_pos_edits[idx].text())
            vel = float(self.target_vel_edits[idx].text())
            acc = float(self.target_acc_edits[idx].text())
            
            if self.communication.move_drive(motor_number, False, pos, vel, acc):
                self.output_list.addItem(f"电机 {motor_number} 移动到位置 {pos}°, 速度 {vel}°/s, 加速度 {acc}°/s²")
                self.output_list.scrollToBottom()
        except ValueError:
            QMessageBox.warning(self, "错误", "请输入有效的数字")

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择轨迹文件", "", "所有文件 (*.*);;文本文件 (*.txt)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def transfer_trajectory(self):
        file_path = self.file_path_edit.text()
        if not file_path:
            QMessageBox.warning(self, "警告", "请先选择轨迹文件")
            return
        
        try:
            with open(file_path, 'r') as f:
                lines = f.readlines()
            
            # 解析轨迹数据
            trajectory = []
            for line in lines:
                values = line.strip().split(',')
                if len(values) >= self.motor_count:
                    trajectory.append([
                        float(values[0]), 
                        float(values[1]), 
                        float(values[2]), 
                        float(values[3]),
                        float(values[4]),
                        float(values[5]),
                        float(values[6])
                    ])
            
            if not trajectory:
                QMessageBox.warning(self, "警告", "轨迹文件为空")
                return
            
            # 传输轨迹到所有电机
            for i in range(self.motor_count):
                motor_trajectory = [point[i] for point in trajectory]
                self.communication.input_trajectory(i+1, motor_trajectory)
            
            # 显示起始点
            start_point = trajectory[0]
            self.output_list.addItem(f"轨迹文件: {file_path}")
            self.output_list.addItem(f"起始点: {start_point[0]}, {start_point[1]}, {start_point[2]}, {start_point[3]}")
            self.output_list.scrollToBottom()
            
            # 更新目标位置显示
            for i in range(self.motor_count):
                self.target_pos_edits[i].setText(str(start_point[i]))
                
        except Exception as e:
            QMessageBox.critical(self, "错误", f"传输轨迹失败: {str(e)}")

    def start_execution(self):
        """开始执行轨迹"""
        is_loop = self.loop_checkbox.isChecked()
        if self.communication.start_execution(is_loop):
            self.output_list.addItem("轨迹执行命令已发送")
            self.output_list.scrollToBottom()

    def abort_execution(self):
        """中止轨迹执行"""
        if self.communication.abort_execution():
            self.output_list.addItem("轨迹执行已中止")
            self.output_list.scrollToBottom()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MainWindow()
    window.setGeometry(400, 50, 400, 600) 
    window.show()
    sys.exit(app.exec())