from PyQt6.QtWidgets import (QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel, 
                             QLineEdit, QGridLayout, QGroupBox, QListWidget, QFileDialog, 
                             QCheckBox)
import pyads
from PyQt6.QtCore import QTimer

class RobotControlTab(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.motor_count = 7
        self.initUI()
        self.set_button_enable_func(False)

        # 用于更新机械臂状态的定时器
        self.status_timer = QTimer(self)
        self.status_timer.timeout.connect(self.update_robot_status)

    def initUI(self):
        """初始化机械臂控制选项卡"""
        layout = QHBoxLayout(self)

        tc_box = QGroupBox("遥控")
        layout0 = QVBoxLayout()
        tc_box.setLayout(layout0)

        tm_box = QGroupBox("遥测")
        layout1 = QVBoxLayout()
        tm_box.setLayout(layout1)
        
        # 连接设置部分
        connection_group = QGroupBox("连接设置")
        connection_layout = QGridLayout()
        
        self.net_id_edit = QLineEdit("10.1.176.253.1.1")
        self.port_edit = QLineEdit("851")
        
        self.connect_button = QPushButton("连接")
        self.connect_button.clicked.connect(self.connect_to_robot)

        self.stop_connect_button = QPushButton("断开")
        self.stop_connect_button.clicked.connect(self.stop_connect_to_robot)
        
        connection_layout.addWidget(QLabel("AMS Net ID:"), 0, 0)
        connection_layout.addWidget(self.net_id_edit, 0, 1)
        connection_layout.addWidget(QLabel("端口:"), 1, 0)
        connection_layout.addWidget(self.port_edit, 1, 1)
        connection_layout.addWidget(self.connect_button, 2, 0, 1, 2)
        connection_layout.addWidget(self.stop_connect_button, 3, 0, 1, 2)
        
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
        
        self.start_exec_button = QPushButton("开始执行")
        self.start_exec_button.clicked.connect(self.start_execution)
        
        self.abort_button = QPushButton("中止执行")
        self.abort_button.clicked.connect(self.abort_execution)
        
        trajectory_layout.addWidget(QLabel("轨迹文件:"), 0, 0)
        trajectory_layout.addWidget(self.file_path_edit, 0, 1)
        trajectory_layout.addWidget(browse_button, 0, 2)
        trajectory_layout.addWidget(self.loop_checkbox, 1, 0)
        trajectory_layout.addWidget(transfer_button, 1, 1)
        trajectory_layout.addWidget(self.start_exec_button, 1, 2)
        trajectory_layout.addWidget(self.abort_button, 1, 3)
        
        trajectory_group.setLayout(trajectory_layout)
        layout0.addWidget(trajectory_group)

        # 控制状态
        output_group = QGroupBox("控制状态")
        output_layout = QGridLayout()

        clear_output_button = QPushButton("清空数据")
        clear_output_button.clicked.connect(self.clear_output_func)

        self.output_list = QListWidget()

        output_layout.addWidget(clear_output_button)
        output_layout.addWidget(self.output_list)
        output_group.setLayout(output_layout)

        layout1.addWidget(output_group)

        layout.addWidget(tc_box)
        layout.addWidget(tm_box) 

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
            self.output_list.addItem("端口号必须是整数或十六进制格式（如0x1234）")
            self.output_list.scrollToBottom()
            return
            
        try:
            self.plc = pyads.Connection(net_id, port)
            self.plc.open()
            self.connected = True
        except pyads.ADSError as e:
            self.output_list.addItem(f"连接失败: {e}")
            self.output_list.scrollToBottom()
            return
        
        self.set_button_enable_func(True)

        self.status_timer.start(200)  # 每200ms更新一次状态

        self.output_list.addItem(f"已连接到 {net_id}:{port} (0x{port:x})")
        self.output_list.scrollToBottom()

    def stop_connect_to_robot(self):
        self.plc.close()
        self.connected = False
        self.set_button_enable_func(False)
        
    def _read_plc_data(self, var_name_template, plc_type):
        """统一读取PLC数据的模板函数"""
        if not hasattr(self, 'plc') or not self.plc:
            return [-1.0] * self.motor_count

        try:
            values = []
            for i in range(self.motor_count):
                var_name = var_name_template.format(i)
                value = self.plc.read_by_name(var_name, plc_type)
                values.append(value)
            return values
        except pyads.ADSError as e:
            self.output_list.addItem(f"读取{var_name_template}出错: {e}")
            self.output_list.scrollToBottom()
            return [-1.0] * self.motor_count
        
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
        if not hasattr(self, 'plc') or not self.plc:
            self.output_list.addItem("未连接到PLC")
            self.output_list.scrollToBottom()
            return False
            
        try:
            # 构建变量名：MAIN.CommandName[MotorNumber]
            var_name = f"MAIN.{command_name}[{motor_number}]"
            # 写入命令值（通常1表示执行）
            self.plc.write_by_name(var_name, value, pyads.PLCTYPE_INT)
            return True
        except pyads.ADSError as e:
            self.output_list.addItem(f"执行{command_name}命令出错: {e}")
            self.output_list.scrollToBottom()
            return False
        
    def enable_motor(self, motor_number):
        if self._execute_command(motor_number, "EnableDrive"):
            self.output_list.addItem(f"电机 {motor_number} 已使能")           
        else:
            self.output_list.addItem(f"电机 {motor_number} 使能失败")
        self.output_list.scrollToBottom()

    def disable_motor(self, motor_number):
        if self._execute_command(motor_number, "DisableDrive"):
            self.output_list.addItem(f"电机 {motor_number} 已禁止")
        else:
            self.output_list.addItem(f"电机 {motor_number} 禁止失败")
        self.output_list.scrollToBottom()

    def clear_motor_fault(self, motor_number):
        if self._execute_command(motor_number, "ClearDriveFault"):
            self.output_list.addItem(f"电机 {motor_number} 故障已清除")
        else:
            self.output_list.addItem(f"电机 {motor_number} 故障清除失败")
        self.output_list.scrollToBottom()

    def jog_motor(self, motor_number, is_positive):
        if self._execute_command(motor_number, "JogDrive", 1 if is_positive else 2):
            direction = "正转" if is_positive else "反转"
            self.output_list.addItem(f"电机 {motor_number} {direction}点动中...")
        else:
            self.output_list.addItem(f"电机 {motor_number} 点动启动失败")
        self.output_list.scrollToBottom()

    def stop_motor(self, motor_number):
        if self._execute_command(motor_number, "StopDrive"):
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
            
            # 写入目标位置
            if self._execute_command(motor_number, "SetTargetPosition", int(pos)):
                # 写入目标速度
                self.plc.write_by_name(f"MAIN.TargetVelocity[{motor_number}]", vel, pyads.PLCTYPE_REAL)
                # 写入目标加速度
                self.plc.write_by_name(f"MAIN.TargetAcceleration[{motor_number}]", acc, pyads.PLCTYPE_REAL)
                # 启动移动
                if self._execute_command(motor_number, "StartMove"):
                    self.output_list.addItem(f"电机 {motor_number} 移动到位置 {pos}°, 速度 {vel}°/s, 加速度 {acc}°/s²")
                    self.output_list.scrollToBottom()
        except ValueError:
            self.output_list.addItem("请输入有效的数字")
            self.output_list.scrollToBottom()
        except pyads.ADSError as e:
            self.output_list.addItem(f"移动命令失败: {e}")
            self.output_list.scrollToBottom()

    def browse_file(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "选择轨迹文件", "", "所有文件 (*.*);;文本文件 (*.txt)"
        )
        if file_path:
            self.file_path_edit.setText(file_path)

    def transfer_trajectory(self):
        file_path = self.file_path_edit.text()
        if not file_path:
            self.output_list.addItem("请先选择轨迹文件")
            self.output_list.scrollToBottom()
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
                self.output_list.addItem("轨迹文件为空")
                self.output_list.scrollToBottom()
                return
            
            # 传输轨迹到所有电机
            for i in range(self.motor_count):
                motor_trajectory = [point[i] for point in trajectory]
                # 在实际应用中，这里需要实现轨迹传输逻辑
                # 这里仅做演示
                self.output_list.addItem(f"电机 {i+1} 轨迹传输完成 ({len(motor_trajectory)}点)")
            
            # 显示起始点
            start_point = trajectory[0]
            self.output_list.addItem(f"轨迹文件: {file_path}")
            self.output_list.addItem(f"起始点: {start_point[0]}, {start_point[1]}, {start_point[2]}, {start_point[3]}")
            self.output_list.scrollToBottom()
            
            # 更新目标位置显示
            for i in range(self.motor_count):
                self.target_pos_edits[i].setText(str(start_point[i]))
                
        except Exception as e:
            self.output_list.addItem(f"传输轨迹失败: {str(e)}")
            self.output_list.scrollToBottom()

    def start_execution(self):
        """开始执行轨迹"""
        is_loop = self.loop_checkbox.isChecked()
        # 在实际应用中，这里需要实现轨迹执行逻辑
        # 这里仅做演示
        self.output_list.addItem(f"轨迹执行{'（循环）' if is_loop else ''}已开始")
        self.output_list.scrollToBottom()

    def abort_execution(self):
        """中止轨迹执行"""
        # 在实际应用中，这里需要实现中止执行逻辑
        # 这里仅做演示
        self.output_list.addItem("轨迹执行已中止")
        self.output_list.scrollToBottom()

    def clear_output_func(self):
        self.output_list.clear()

    def set_button_enable_func(self, state):
        for i in range(self.motor_count):
            self.enable_buttons[i].setEnabled(state)
            self.disable_buttons[i].setEnabled(state)
            self.clear_fault_buttons[i].setEnabled(state)
            self.jog_positive_buttons[i].setEnabled(state)
            self.jog_negative_buttons[i].setEnabled(state)
            self.stop_buttons[i].setEnabled(state)
            self.confirm_buttons[i].setEnabled(state)
            self.target_pos_edits[i].setEnabled(state)
            self.target_vel_edits[i].setEnabled(state)
            self.target_acc_edits[i].setEnabled(state)
        self.start_exec_button.setEnabled(state)
        self.abort_button.setEnabled(state)