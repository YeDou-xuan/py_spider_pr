import sys
import mysql.connector
from mysql.connector import Error
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout,
                             QLabel, QTextEdit,
                             QTableWidget, QTableWidgetItem,
                             QMessageBox, QGroupBox,
                             QMenuBar, QMenu, QFileDialog,
                             QProgressBar, QStatusBar, QGraphicsDropShadowEffect,
                             QStyle, QLineEdit, QPushButton)
from PyQt6.QtCore import Qt
from PyQt6.QtGui import QAction, QColor, QIcon, QFont
import pandas as pd
import csv
import os
from datetime import datetime

# 可选：Fluent 主题与组件支持
try:
    from qfluentwidgets import setTheme, Theme, setThemeColor
    from qfluentwidgets import PushButton as QPushButtonBase, LineEdit as LineEditBase

    FLUENT_AVAILABLE = True
except Exception:
    from PyQt6.QtWidgets import QPushButton as QPushButtonBase, QLineEdit as LineEditBase

    FLUENT_AVAILABLE = False


class MySQLQueryTool(QMainWindow):
    def __init__(self):
        super().__init__()
        # 数据库连接相关
        self.connection = None
        self.is_connected = False

        # 数据库连接参数
        self.host_edit = LineEditBase()
        self.user_edit = LineEditBase()
        self.password_edit = LineEditBase()
        self.dbname_edit = LineEditBase()
        self.port_edit = LineEditBase()
        self.host_edit.setText("localhost")
        self.user_edit.setText("root")
        self.password_edit.setText("liu@423615")
        self.dbname_edit.setText("spider_database")
        self.port_edit.setText("3306")

        # 基金查询参数
        self.fund_name_edit = LineEditBase()
        self.fund_code_edit = LineEditBase()
        self.execute_query_btn = QPushButtonBase("执行查询")
        self.fund_name_edit.setPlaceholderText("输入基金名称")
        self.fund_code_edit.setPlaceholderText("输入基金代码")

        # UI组件
        self.status_label = QLabel("未连接数据库")
        self.result_table = QTableWidget()
        self.connect_btn = None
        self.execute_btn = None
        self.reconnect_btn = None

        # 初始化UI
        self.init_ui()
        # 应用样式与细节优化
        self.apply_app_styles()
        self.current_theme = 'light'

        # 移除主动连接检查，采用被动式连接管理

    def init_ui(self):
        # 窗口基本设置
        self.setWindowTitle("基金数据查询工具")
        self.setGeometry(100, 100, 1400, 900)
        self.setMinimumSize(1000, 700)

        # 创建菜单栏
        self.create_menu_bar()

        # 创建状态栏
        self.create_status_bar()

        # 中心部件和主布局
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        main_layout = QVBoxLayout(central_widget)

        # 数据库连接区域
        self.create_connection_group(main_layout)

        # 创建查询区域
        self.create_query_area(main_layout)

        # 主布局边距与间距
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

    def create_menu_bar(self):
        #创建菜单栏
        menubar = self.menuBar()

        # 文件菜单
        file_menu = menubar.addMenu('文件')

        export_action = QAction('导出结果', self)
        export_action.triggered.connect(self.export_results)
        file_menu.addAction(export_action)

        file_menu.addSeparator()

        exit_action = QAction('退出', self)
        exit_action.triggered.connect(self.close)
        file_menu.addAction(exit_action)

        # 外观菜单
        appearance_menu = menubar.addMenu('外观')
        light_action = QAction('浅色主题', self)
        dark_action = QAction('深色主题', self)
        light_action.triggered.connect(self.apply_light_theme)
        dark_action.triggered.connect(self.apply_dark_theme)
        appearance_menu.addAction(light_action)
        appearance_menu.addAction(dark_action)

        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        reconnect_action = QAction('重新连接', self)
        reconnect_action.triggered.connect(self.reconnect_database)
        tools_menu.addAction(reconnect_action)

        # 帮助菜单
        help_menu = menubar.addMenu('帮助')

        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        #创建状态栏
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

        # 添加连接状态指示器
        self.connection_status_indicator = QLabel("●")
        self.connection_status_indicator.setStyleSheet("color: red; font-weight: bold;")
        self.status_bar.addPermanentWidget(self.connection_status_indicator)

    def create_connection_group(self, parent_layout):
        #创建数据库连接设置区域
        conn_group = QGroupBox("数据库连接设置")
        conn_layout = QGridLayout(conn_group)
        conn_layout.setHorizontalSpacing(10)
        conn_layout.setVerticalSpacing(8)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(18)
        effect.setOffset(0, 2)
        effect.setColor(QColor(0, 0, 0, 50))
        conn_group.setGraphicsEffect(effect)

        # 连接参数输入
        conn_layout.addWidget(QLabel("主机:"), 0, 0)
        conn_layout.addWidget(self.host_edit, 0, 1)

        conn_layout.addWidget(QLabel("端口:"), 0, 2)
        conn_layout.addWidget(self.port_edit, 0, 3)

        conn_layout.addWidget(QLabel("用户名:"), 0, 4)
        conn_layout.addWidget(self.user_edit, 0, 5)

        conn_layout.addWidget(QLabel("密码:"), 1, 0)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addWidget(self.password_edit, 1, 1)

        conn_layout.addWidget(QLabel("数据库名:"), 1, 2)
        conn_layout.addWidget(self.dbname_edit, 1, 3)

        # 连接按钮
        self.connect_btn = QPushButtonBase("连接数据库")
        self.connect_btn.clicked.connect(self.on_connect_button_clicked)
        self.connect_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))
        conn_layout.addWidget(self.connect_btn, 1, 4)

        # 重新连接按钮
        self.reconnect_btn = QPushButtonBase("重新连接")
        self.reconnect_btn.clicked.connect(self.reconnect_database)
        self.reconnect_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        self.reconnect_btn.setEnabled(False)
        conn_layout.addWidget(self.reconnect_btn, 1, 5)

        parent_layout.addWidget(conn_group)

    def create_query_area(self, parent_layout):
        #创建查询区域
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)

        # 基金查询条件区域
        condition_group = QGroupBox("基金查询条件")
        condition_layout = QHBoxLayout(condition_group)

        condition_layout.addWidget(QLabel("基金名称:"))
        condition_layout.addWidget(self.fund_name_edit)
        condition_layout.addWidget(QLabel("基金代码:"))
        condition_layout.addWidget(self.fund_code_edit)
        condition_layout.addWidget(self.execute_query_btn)

        query_layout.addWidget(condition_group)

        # 查询模板区域
        template_group = QGroupBox("查询模板")
        template_layout = QVBoxLayout(template_group)

        template_btn_layout = QGridLayout()
        template_btn_layout.setSpacing(6)

        # 常用查询模板按钮
        templates = [
            ("查看表结构", "DESCRIBE dayfund_spider_data;"),
            ("查看表所有数据", "SELECT * FROM dayfund_spider_data;"),
            ("查看前10条记录", "SELECT * FROM dayfund_spider_data LIMIT 10;"),
            ("统计记录数", "SELECT COUNT(*) as 总记录数 FROM dayfund_spider_data;"),
            ("按日增长排序",
             "SELECT `基金名称`, `日增长(%)` FROM dayfund_spider_data ORDER BY `日增长(%)` DESC LIMIT 10;"),
            ("按近1年排序",
             "SELECT `基金名称`, `近1年(%)` FROM dayfund_spider_data ORDER BY `近1年(%)` DESC LIMIT 10;"),
            ("按近1周排序",
             "SELECT `基金名称`, `近1周(%)` FROM dayfund_spider_data ORDER BY `近1周(%)` DESC LIMIT 10;"),
            ("按近1月排序",
             "SELECT `基金名称`, `近1月(%)` FROM dayfund_spider_data ORDER BY `近1月(%)` DESC LIMIT 10;"),
            ("查看正收益基金",
             "SELECT `基金名称`, `日增长(%)`, `近1周(%)`, `近1月(%)` FROM dayfund_spider_data WHERE `日增长(%)` > 0 ORDER BY `日增长(%)` DESC LIMIT 20;"),
            ("查看负收益基金",
             "SELECT `基金名称`, `日增长(%)`, `近1周(%)`, `近1月(%)` FROM dayfund_spider_data WHERE `日增长(%)` < 0 ORDER BY `日增长(%)`  LIMIT 20;")
        ]

        for i, (name, sql) in enumerate(templates):
            btn = QPushButtonBase(name)
            btn.clicked.connect(lambda checked, s=sql: self.execute_template_query(s))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent))
            template_btn_layout.addWidget(btn, i // 2, i % 2)

        template_layout.addLayout(template_btn_layout)
        query_layout.addWidget(template_group)

        # 结果显示区域
        result_group = QGroupBox("查询结果")
        result_group_layout = QVBoxLayout(result_group)

        # 结果操作按钮
        result_btn_layout = QHBoxLayout()
        result_btn_layout.setSpacing(6)

        export_csv_btn = QPushButtonBase("导出CSV")
        export_csv_btn.clicked.connect(lambda: self.export_results('csv'))
        export_csv_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))

        export_excel_btn = QPushButtonBase("导出Excel")
        export_excel_btn.clicked.connect(lambda: self.export_results('excel'))
        export_excel_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))

        copy_btn = QPushButtonBase("复制结果")
        copy_btn.clicked.connect(self.copy_results)
        copy_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))

        clear_btn = QPushButtonBase("清空结果")
        clear_btn.clicked.connect(self.clear_results)
        clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_TrashIcon))

        result_btn_layout.addWidget(export_csv_btn)
        result_btn_layout.addWidget(export_excel_btn)
        result_btn_layout.addWidget(copy_btn)
        result_btn_layout.addWidget(clear_btn)
        result_btn_layout.addStretch()

        result_group_layout.addLayout(result_btn_layout)

        # 结果表格优化
        self.result_table.setAlternatingRowColors(True)
        self.result_table.setSortingEnabled(True)
        self.result_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.result_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        r_header = self.result_table.horizontalHeader()
        r_header.setStretchLastSection(True)
        r_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        result_group_layout.addWidget(self.result_table)

        # 状态信息
        status_layout = QHBoxLayout()
        status_layout.addWidget(self.status_label)
        status_layout.addStretch()

        # 添加进度条
        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        self.progress_bar.setTextVisible(False)
        status_layout.addWidget(self.progress_bar)

        result_group_layout.addLayout(status_layout)

        query_layout.addWidget(result_group)
        parent_layout.addWidget(query_widget)

        # 连接执行按钮
        self.execute_query_btn.clicked.connect(lambda: self.execute_template_query("SELECT * FROM dayfund_spider_data LIMIT 100"))

    def apply_app_styles(self):
        #应用统一样式
        if FLUENT_AVAILABLE:
            return
        self.setStyleSheet("""
        QWidget { font-size: 10pt; }
        QMainWindow { background: #f7f9fc; }
        QGroupBox { border: 1px solid #e6eaf0; border-radius: 10px; margin-top: 10px; }
        QPushButton { background: #1976d2; color: white; border-radius: 8px; padding: 7px 14px; }
        QPushButton:hover { background: #1565c0; }
        QLineEdit, QTextEdit { background: #ffffff; border: 1px solid #d3dae6; border-radius: 8px; padding: 6px 8px; }
        QTableWidget { gridline-color: #e0e0e0; selection-background-color: #e3f2fd; background: #ffffff; border: 1px solid #e6eaf0; border-radius: 8px; }
        QProgressBar { background: #e9eef5; border: 1px solid #d0d7e2; border-radius: 8px; height: 10px; }
        QProgressBar::chunk { background: #42a5f5; border-radius: 8px; }
        """)

    def apply_dark_theme(self):
        #切换到深色主题
        self.current_theme = 'dark'
        if FLUENT_AVAILABLE:
            setTheme(Theme.DARK)
        self.setStyleSheet("""
        QWidget { font-size: 10pt; color: #dce0e6; background: #1e2023; }
        QPushButton { background: #1976d2; color: white; border-radius: 8px; padding: 7px 14px; }
        QPushButton:hover { background: #1565c0; }
        QLineEdit, QTextEdit { background: #1a1c1f; border: 1px solid #2f343a; border-radius: 8px; padding: 6px 8px; color: #dce0e6; }
        QTableWidget { gridline-color: #2f343a; selection-background-color: #263238; background: #1a1c1f; border: 1px solid #2c2f33; border-radius: 8px; }
        QGroupBox { border: 1px solid #2c2f33; border-radius: 10px; margin-top: 10px; }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 2px 6px;
            color: #dce0e6;
            background: transparent;
        }
        QLabel { color: #dce0e6; }
        """)
        
        # 重新应用深色主题的阴影效果
        self._apply_shadow_effects()

    def apply_light_theme(self):
        #应用浅色主题
        self.current_theme = 'light'
        if FLUENT_AVAILABLE:
            setTheme(Theme.LIGHT)
        self.setStyleSheet("""
        QWidget { font-size: 10pt; color: #2c2f33; background: #ffffff; }
        QPushButton { background: #1976d2; color: white; border-radius: 8px; padding: 7px 14px; }
        QPushButton:hover { background: #1565c0; }
        QLineEdit, QTextEdit { background: #f8f9fa; border: 1px solid #d0d7e2; border-radius: 8px; padding: 6px 8px; color: #2c2f33; }
        QTableWidget { gridline-color: #e0e0e0; selection-background-color: #e3f2fd; background: #ffffff; border: 1px solid #e6eaf0; border-radius: 8px; }
        QGroupBox { border: 1px solid #e6eaf0; border-radius: 10px; margin-top: 10px; }
        QGroupBox::title {
            subcontrol-origin: margin;
            left: 12px;
            padding: 2px 6px;
            color: #2c2f33;
            background: transparent;
        }
        QLabel { color: #2c2f33; }
        """)
        
        # 重新应用所有阴影效果
        self._apply_shadow_effects()

    def _apply_shadow_effects(self):
        #统一应用阴影效果
        if FLUENT_AVAILABLE:
            return
            
        # 获取所有QGroupBox并应用阴影
        for group_box in self.findChildren(QGroupBox):
            effect = QGraphicsDropShadowEffect(self)
            effect.setBlurRadius(18)
            effect.setOffset(0, 2)
            
            # 根据当前主题设置阴影颜色
            if self.current_theme == 'light':
                effect.setColor(QColor(0, 0, 0, 80))  # 浅色主题阴影
            else:
                effect.setColor(QColor(0, 0, 0, 60))  # 深色主题阴影
                
            group_box.setGraphicsEffect(effect)

    # 移除check_connection_status方法，采用被动式连接管理

    def reconnect_database(self):
        #重新连接数据库
        self.disconnect_database()
        self.connect_database()

    def on_connect_button_clicked(self):
        #连接/断开按钮点击处理
        if self.is_connected:
            self.disconnect_database()
        else:
            self.connect_database()

    def connect_database(self):
        #连接到数据库
        try:
            # 显示连接进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)  # 不确定进度
            self.status_bar.showMessage("正在连接数据库...")
            
            self.connection = mysql.connector.connect(
                host=self.host_edit.text(),
                user=self.user_edit.text(),
                password=self.password_edit.text(),
                database=self.dbname_edit.text(),
                charset='utf8mb4',
                autocommit=True
            )

            if self.connection.is_connected():
                db_info = self.connection.server_info
                QMessageBox.information(self, "连接成功", f"成功连接到MySQL {db_info}")
                self.status_label.setText(f"已连接到: {self.host_edit.text()}/{self.dbname_edit.text()}")
                self.status_bar.showMessage(f"已连接到数据库: {self.dbname_edit.text()}")
                self.connect_btn.setText("断开连接")
                self.connection_status_indicator.setStyleSheet("color: green; font-weight: bold;")
                self.connection_status_indicator.setToolTip("数据库连接正常")
                self.is_connected = True

        except Error as e:
            QMessageBox.critical(self, "连接失败", f"数据库连接失败:\n{str(e)}")
            self.status_label.setText("连接失败")
            self.status_bar.showMessage("连接失败")
        finally:
            self.progress_bar.setVisible(False)



    def disconnect_database(self):
        #断开数据库连接
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.status_label.setText("已断开连接")
            self.status_bar.showMessage("已断开数据库连接")
            self.connect_btn.setText("连接数据库")
            self.connection_status_indicator.setStyleSheet("color: red; font-weight: bold;")
            self.connection_status_indicator.setToolTip("数据库连接已断开")
            self.is_connected = False
            
            QMessageBox.information(self, "断开成功", "已断开数据库连接")



    def execute_template_query(self, sql_template):
        #执行模板查询
        sql = sql_template
        if not sql:
            QMessageBox.warning(self, "警告", "请输入SQL语句")
            return

        try:
            if not self.connection or not self.connection.is_connected():
                QMessageBox.warning(self, "警告", "请先连接数据库")
                return
        except Exception:
            # 处理连接检查时的异常
            QMessageBox.warning(self, "警告", "数据库连接异常，请重新连接")
            self.is_connected = False
            self.connection = None
            return

        try:
            # 显示执行进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_bar.showMessage("正在执行查询...")
            
            # 获取查询条件
            fund_name = self.fund_name_edit.text().strip()
            fund_code = self.fund_code_edit.text().strip()

            # 根据条件修改SQL模板
            conditions = []
            if fund_name:
                conditions.append(f"`基金名称` LIKE '%{fund_name}%'")
            if fund_code:
                conditions.append(f"`基金代码` LIKE '%{fund_code}%'")

            if conditions:
                if "WHERE" in sql:
                    sql = sql.replace("WHERE", f"WHERE {' AND '.join(conditions)} AND ")
                else:
                    if "LIMIT" in sql:
                        sql = sql.replace("LIMIT", f"WHERE {' AND '.join(conditions)} LIMIT")
                    else:
                        sql += f" WHERE {' AND '.join(conditions)}"

            cursor = self.connection.cursor()
            cursor.execute(sql)

            # 处理查询结果
            if sql.lower().startswith(('select', 'show', 'desc', 'describe', 'explain')):
                records = cursor.fetchall()
                columns = cursor.description

                if columns:
                    self.result_table.setColumnCount(len(columns))
                    self.result_table.setHorizontalHeaderLabels([col[0] for col in columns])
                    self.result_table.setRowCount(len(records))

                    for row_idx, row_data in enumerate(records):
                        for col_idx, col_data in enumerate(row_data):
                            item = QTableWidgetItem(str(col_data) if col_data is not None else "")
                            self.result_table.setItem(row_idx, col_idx, item)

                    self.result_table.resizeColumnsToContents()
                    self.status_label.setText(f"查询成功，返回 {len(records)} 条记录")
                    self.status_bar.showMessage(f"查询完成，返回 {len(records)} 条记录")
                else:
                    self.result_table.setRowCount(0)
                    self.result_table.setColumnCount(0)
                    self.status_label.setText("查询成功，无结果")
                    self.status_bar.showMessage("查询完成，无结果")
            else:
                self.connection.commit()
                affected_rows = cursor.rowcount
                self.status_label.setText(f"执行成功，影响 {affected_rows} 行")
                self.status_bar.showMessage(f"执行完成，影响 {affected_rows} 行")
                QMessageBox.information(self, "执行成功", f"影响 {affected_rows} 行")

            # 确保所有结果都被读取，避免Unread result错误
            while cursor.nextset():
                pass
            cursor.close()
            
            # 清空输入框内容
            self.fund_name_edit.clear()
            self.fund_code_edit.clear()
            
        except Error as e:
            if self.connection:
                self.connection.rollback()
            QMessageBox.critical(self, "执行错误", f"SQL执行失败:\n{str(e)}")
            self.status_label.setText("执行失败")
            self.status_bar.showMessage("查询执行失败")
        except Exception as e:
            QMessageBox.critical(self, "未知错误", f"发生未知错误:\n{str(e)}")
            self.status_label.setText("执行失败")
            self.status_bar.showMessage("查询执行失败")
        finally:
            self.progress_bar.setVisible(False)

    def export_results(self, format_type='csv'):
        #导出查询结果
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return

        file_path, _ = QFileDialog.getSaveFileName(self, "保存文件", 
            f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.{format_type}",
            f"{'CSV文件 (*.csv)' if format_type == 'csv' else 'Excel文件 (*.xlsx)'}")
        
        if not file_path:
            return

        try:
            data = [[self.result_table.item(row, col).text() if self.result_table.item(row, col) else ""
                     for col in range(self.result_table.columnCount())]
                    for row in range(self.result_table.rowCount())]
            headers = [self.result_table.horizontalHeaderItem(col).text() 
                      for col in range(self.result_table.columnCount())]
            
            df = pd.DataFrame(data, columns=headers)
            (df.to_csv if format_type == 'csv' else df.to_excel)(file_path, index=False)
            QMessageBox.information(self, "成功", f"数据已导出到: {file_path}")

        except Exception as e:
            QMessageBox.critical(self, "失败", f"导出失败: {str(e)}")

    def copy_results(self):
        #复制结果到剪贴板
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有数据可复制")
            return

        try:
            data = [[self.result_table.item(row, col).text() if self.result_table.item(row, col) else ""
                     for col in range(self.result_table.columnCount())]
                    for row in range(self.result_table.rowCount())]
            headers = [self.result_table.horizontalHeaderItem(col).text() 
                      for col in range(self.result_table.columnCount())]
            
            QApplication.clipboard().setText(pd.DataFrame(data, columns=headers).to_csv(index=False))
            QMessageBox.information(self, "成功", "数据已复制到剪贴板")

        except Exception as e:
            QMessageBox.critical(self, "失败", f"复制失败: {str(e)}")

    def clear_results(self):
        #清空结果表格
        self.result_table.setRowCount(0)
        self.result_table.setColumnCount(0)
        self.status_label.setText("结果已清空")

    def show_about(self):
        #显示关于对话框
        QMessageBox.about(self, "关于", "基金数据查询工具 v1.0\n\n基于PyQt6的MySQL数据库查询工具\n\n功能：数据库连接、SQL查询、数据导出")







    def closeEvent(self, event):
        #窗口关闭事件处理
        if QMessageBox.question(self, '确认退出', '确定要退出程序吗？') == QMessageBox.StandardButton.Yes:
            if self.connection:
                self.connection.close()
            event.accept()
        else:
            event.ignore()


if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setFont(QFont("Microsoft YaHei", 10))
    if FLUENT_AVAILABLE:
        setTheme(Theme.DARK)
        setThemeColor(QColor("#00C853"))
    window = MySQLQueryTool()
    window.show()
    sys.exit(app.exec())