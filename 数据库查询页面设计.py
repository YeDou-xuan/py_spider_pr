import sys
import mysql.connector
from mysql.connector import Error
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout,
                             QLabel, QLineEdit, QTextEdit,
                             QPushButton, QTableWidget, QTableWidgetItem,
                             QMessageBox, QSplitter, QGroupBox)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QFont


class MySQLQueryTool(QMainWindow):
    def __init__(self):
        super().__init__()
        self.status_label = QLabel("未连接到数据库")
        self.result_table = QTableWidget()
        self.sql_edit = QTextEdit()
        self.dbname_edit = QLineEdit("spider_database")
        self.password_edit = QLineEdit("liu@423615")
        self.user_edit = QLineEdit("root")
        self.host_edit = QLineEdit("localhost")
        self.connection = None
        self.is_connected = False  # 连接状态标志
        self.init_ui()  # 最后初始化UI，确保所有属性已定义
        self.connect_btn: QPushButton = QPushButton("连接数据库")
        self.execute_btn: QPushButton = QPushButton("执行查询")
        self.clear_btn: QPushButton = QPushButton("清除")

    def init_ui(self):
        # 窗口基本设置
        self.setWindowTitle("MySQL数据库查询工具")
        self.setGeometry(100, 100, 1200, 800)

        # 中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 数据库连接区域
        self.create_connection_group(main_layout)

        # 分割器：上部分为查询区，下部分为结果区
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.create_query_area(splitter)
        self.create_result_area(splitter)
        splitter.setSizes([300, 500])
        main_layout.addWidget(splitter)

    def create_connection_group(self, parent_layout):
        """创建数据库连接设置区域"""
        conn_group = QGroupBox("数据库连接设置")
        conn_layout = QGridLayout(conn_group)

        # 连接参数输入
        conn_layout.addWidget(QLabel("主机:"), 0, 0)
        conn_layout.addWidget(self.host_edit, 0, 1)

        conn_layout.addWidget(QLabel("用户名:"), 0, 2)
        conn_layout.addWidget(self.user_edit, 0, 3)

        conn_layout.addWidget(QLabel("密码:"), 1, 0)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addWidget(self.password_edit, 1, 1)

        conn_layout.addWidget(QLabel("数据库名:"), 1, 2)
        conn_layout.addWidget(self.dbname_edit, 1, 3)

        # 连接按钮 - 只在初始化时连接一次信号
        self.connect_btn = QPushButton("连接数据库")
        # 正确的信号连接：控件.信号.connect(槽函数)
        self.connect_btn.clicked.connect(self.on_connect_button_clicked)
        conn_layout.addWidget(self.connect_btn, 1, 4)

        parent_layout.addWidget(conn_group)

    def create_query_area(self, parent):
        """创建SQL查询区域"""
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)

        query_group = QGroupBox("SQL查询")
        query_group_layout = QVBoxLayout(query_group)

        self.sql_edit.setFont(QFont("Consolas", 10))
        query_group_layout.addWidget(self.sql_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.execute_btn = QPushButton("执行查询")
        self.execute_btn.clicked.connect(self.on_execute_clicked)
        self.execute_btn.setEnabled(True)  # 初始禁用

        self.clear_btn = QPushButton("清除")
        self.clear_btn.clicked.connect(self.sql_edit.clear)  # 直接连接到内置方法

        btn_layout.addWidget(self.execute_btn)
        btn_layout.addWidget(self.clear_btn)
        query_group_layout.addLayout(btn_layout)

        query_layout.addWidget(query_group)
        parent.addWidget(query_widget)

    def create_result_area(self, parent):
        """创建结果显示区域"""
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)

        result_group = QGroupBox("查询结果")
        result_group_layout = QVBoxLayout(result_group)

        result_group_layout.addWidget(self.result_table)

        result_group_layout.addWidget(self.status_label)

        result_layout.addWidget(result_group)
        parent.addWidget(result_widget)

    # 以下是所有槽函数，只作为被连接的目标，不主动调用connect/disconnect
    def on_connect_button_clicked(self):
        """连接/断开按钮点击处理"""
        if self.is_connected:
            self.disconnect_database()
        else:
            self.connect_database()

    def connect_database(self):
        """连接到数据库"""
        try:
            self.connection = mysql.connector.connect(
                host=self.host_edit.text(),
                user=self.user_edit.text(),
                password=self.password_edit.text(),
                database=self.dbname_edit.text()
            )

            if self.connection.is_connected():
                db_info = self.connection.server_info
                QMessageBox.information(self, "成功", f"连接到MySQL {db_info}")
                self.status_label.setText(f"已连接到: {self.host_edit.text()}/{self.dbname_edit.text()}")
                self.connect_btn.setText("断开连接")
                self.execute_btn.setEnabled(True)
                self.is_connected = True

            if self.connection and self.connection.is_connected():
                cursor = self.connection.cursor()
                cursor.execute("SELECT 1")  # 简单测试查询
                result = cursor.fetchone()
                cursor.close()
                print("连接测试查询结果:", result)

        except Error as e:
            QMessageBox.critical(self, "错误", f"连接失败: {str(e)}")
            self.status_label.setText("连接失败")

    def disconnect_database(self):
        """断开数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.status_label.setText("已断开连接")
            self.connect_btn.setText("连接数据库")
            self.execute_btn.setEnabled(False)
            self.is_connected = False
            QMessageBox.information(self, "成功", "已断开连接")

    def on_execute_clicked(self):
        """执行查询按钮点击处理"""
        sql = self.sql_edit.toPlainText().strip()
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL语句")
            return

        if not self.connection or not self.connection.is_connected():
            QMessageBox.warning(self, "警告", "请先连接数据库")
            return

        try:
            cursor = self.connection.cursor()
            cursor.execute(sql)

            # 处理查询结果
            if sql.lower().startswith(('select', 'show', 'desc', 'describe')):
                records = cursor.fetchall()
                columns = cursor.description

                self.result_table.setColumnCount(len(columns))
                self.result_table.setHorizontalHeaderLabels([col[0] for col in columns])
                self.result_table.setRowCount(len(records))

                for row_idx, row_data in enumerate(records):
                    for col_idx, col_data in enumerate(row_data):
                        self.result_table.setItem(row_idx, col_idx, QTableWidgetItem(str(col_data)))

                self.result_table.resizeColumnsToContents()
                self.status_label.setText(f"查询成功，返回 {len(records)} 条记录")
            else:
                self.connection.commit()
                self.status_label.setText(f"执行成功，影响 {cursor.rowcount} 行")
                QMessageBox.information(self, "成功", f"影响 {cursor.rowcount} 行")

            cursor.close()

        except Error as e:
            self.connection.rollback()
            QMessageBox.critical(self, "错误", f"执行失败: {str(e)}")
            self.status_label.setText("执行失败")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = MySQLQueryTool()
    window.show()
    sys.exit(app.exec())


