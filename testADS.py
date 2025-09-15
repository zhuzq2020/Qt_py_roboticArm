import sys
import pyads
from PySide6.QtWidgets import (QApplication, QMainWindow, QWidget, 
                              QVBoxLayout, QPushButton, QLabel,
                              QLineEdit, QGroupBox)
from PySide6.QtCore import QTimer

class TwinCATInterface(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("TwinCAT3 Communication")
        self.setGeometry(100, 100, 400, 350)
        
        # ADS连接参数
        self.plc_net_id = '10.1.176.253.1.1'  # 替换为你的PLC AMS Net ID
        self.plc_port = 851
        
        # 创建UI
        self.central_widget = QWidget()
        self.setCentralWidget(self.central_widget)
        layout = QVBoxLayout()
        
        # 连接控制组
        self.gb_connection = QGroupBox("Connection")
        self.btn_connect = QPushButton("Connect to PLC")
        self.lbl_status = QLabel("Status: Disconnected")
        self.gb_connection.setLayout(QVBoxLayout())
        self.gb_connection.layout().addWidget(self.btn_connect)
        self.gb_connection.layout().addWidget(self.lbl_status)
        
        # 数据交互组
        self.gb_data = QGroupBox("PLC Data")
        self.btn_toggle = QPushButton("Toggle Start/Stop")
        self.lbl_counter = QLabel("Counter: 0")
        self.btn_enable = QPushButton("Enable")
        
        # 添加Position显示标签
        self.lbl_position0 = QLabel("Position[0]: -1")
        self.lbl_position1 = QLabel("Position[1]: -1")
        self.lbl_position2 = QLabel("Position[2]: -1")
        self.lbl_position3 = QLabel("Position[3]: -1")
        
        data_layout = QVBoxLayout()
        data_layout.addWidget(self.btn_toggle)
        data_layout.addWidget(self.lbl_counter)
        data_layout.addWidget(self.btn_enable)
        data_layout.addWidget(self.lbl_position0)
        data_layout.addWidget(self.lbl_position1)
        data_layout.addWidget(self.lbl_position2)
        data_layout.addWidget(self.lbl_position3)
        self.gb_data.setLayout(data_layout)
        self.gb_data.setEnabled(False)  # 初始禁用
        
        # 添加所有组到主布局
        layout.addWidget(self.gb_connection)
        layout.addWidget(self.gb_data)
        self.central_widget.setLayout(layout)
        
        # 连接信号
        self.btn_connect.clicked.connect(self.connect_plc)
        self.btn_toggle.clicked.connect(self.toggle_start_stop)
        self.btn_enable.clicked.connect(self.enable_process)
        
        # ADS连接对象和定时器
        self.plc = None
        self.timer = QTimer()
        self.timer.timeout.connect(self.read_values)
        
    def connect_plc(self):
        try:
            self.plc = pyads.Connection(self.plc_net_id, self.plc_port)
            self.plc.open()
            self.lbl_status.setText(f"Status: Connected to {self.plc_net_id}")
            self.gb_data.setEnabled(True)
            
            # 连接成功后立即开始实时读取
            self.timer.start(100)  # 每100毫秒读取一次
            
        except pyads.ADSError as e:
            self.lbl_status.setText(f"Error: {str(e)}")

    def enable_process(self):
        if not self.plc: return
        
        try:
            self.plc.write_by_name('MAIN.Control[0]', 10, pyads.PLCTYPE_UINT)
        except pyads.ADSError as e:
            print(f"Write error: {e}")

    def toggle_start_stop(self):
        if not self.plc: return
        
        try:
            current = self.plc.read_by_name('MAIN.change', pyads.PLCTYPE_BOOL)
            new_value = not current
            self.plc.write_by_name('MAIN.change', new_value, pyads.PLCTYPE_BOOL)
        except pyads.ADSError as e:
            print(f"Write error: {e}")

    def read_values(self):
        if not self.plc: return
        
        try:
            # 读取计数器值
            counter = self.plc.read_by_name('MAIN.icount', pyads.PLCTYPE_INT)
            self.lbl_counter.setText(f"Counter: {counter}")
            
            # 读取Position数组的每个元素
            # 使用正确的数组元素访问方式
            position0 = self.plc.read_by_name('MAIN.Position[0]', pyads.PLCTYPE_DINT)
            position1 = self.plc.read_by_name('MAIN.Position[1]', pyads.PLCTYPE_DINT)
            position2 = self.plc.read_by_name('MAIN.Position[2]', pyads.PLCTYPE_DINT)
            position3 = self.plc.read_by_name('MAIN.Position[3]', pyads.PLCTYPE_DINT)
            
            # 更新UI显示
            self.lbl_position0.setText(f"Position[0]: {position0}")
            self.lbl_position1.setText(f"Position[1]: {position1}")
            self.lbl_position2.setText(f"Position[2]: {position2}")
            self.lbl_position3.setText(f"Position[3]: {position3}")
            
        except pyads.ADSError as e:
            print(f"Read error: {e}")
            # 发生错误时停止定时器
            self.timer.stop()
            self.lbl_status.setText(f"Error: {str(e)} - Reading stopped")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TwinCATInterface()
    window.show()
    sys.exit(app.exec())