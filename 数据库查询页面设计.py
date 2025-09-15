import sys
import mysql.connector
from mysql.connector import Error
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout,
                             QHBoxLayout, QGridLayout,
                             QLabel, QTextEdit,
                             QTableWidget, QTableWidgetItem,
                             QMessageBox, QSplitter, QGroupBox,
                             QTabWidget, QMenuBar, QMenu, QFileDialog,
                             QProgressBar, QStatusBar, QGraphicsDropShadowEffect,
                             QStyle, QLineEdit)
from PyQt6.QtCore import Qt, QThread, pyqtSignal, QRegularExpression
from PyQt6.QtGui import QFont, QAction, QSyntaxHighlighter, QTextCharFormat, QColor, QPalette
import pandas as pd
import csv
import os
from datetime import datetime

# 可选：Fluent 主题与组件支持（PyQt6-Fluent-Widgets）
try:
    from qfluentwidgets import setTheme, Theme, setThemeColor
    from qfluentwidgets import PushButton as QPushButtonBase, LineEdit as LineEditBase, ComboBox as ComboBoxBase
    FLUENT_AVAILABLE = True
except Exception:
    from PyQt6.QtWidgets import QPushButton as QPushButtonBase, QLineEdit as LineEditBase, QComboBox as ComboBoxBase
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
        self.host_edit.setText("localhost")
        self.user_edit.setText("root")
        self.password_edit.setText("liu@423615")
        self.dbname_edit.setText("spider_database")
        
        # UI组件
        self.status_label = QLabel("未连接到数据库")
        self.result_table = QTableWidget()
        self.sql_edit = QTextEdit()
        self.connect_btn = None
        self.execute_btn = None
        self.clear_btn = None
        
        # 查询历史
        self.sql_history = []
        self.history_combo = ComboBoxBase()
        
        # 初始化UI
        self.init_ui()
        # 应用样式与细节优化（不改变功能）
        self.apply_app_styles()
        self.current_theme = 'light'

    def init_ui(self):
        # 窗口基本设置
        self.setWindowTitle("MySQL数据库查询工具 - 基金数据分析")
        self.setGeometry(100, 100, 1400, 900)

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

        # 创建标签页
        tab_widget = QTabWidget()
        tab_widget.setDocumentMode(True)
        tab_widget.setTabBarAutoHide(False)
        self.create_query_tab(tab_widget)
        self.create_table_management_tab(tab_widget)
        main_layout.addWidget(tab_widget)

        # 主布局边距与间距
        main_layout.setContentsMargins(12, 12, 12, 12)
        main_layout.setSpacing(10)

    def create_menu_bar(self):
        """创建菜单栏"""
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
        
        # 工具菜单
        tools_menu = menubar.addMenu('工具')
        
        clear_history_action = QAction('清除查询历史', self)
        clear_history_action.triggered.connect(self.clear_history)
        tools_menu.addAction(clear_history_action)

        # 外观菜单
        appearance_menu = menubar.addMenu('外观')
        light_action = QAction('浅色主题', self)
        dark_action = QAction('深色主题', self)
        light_action.triggered.connect(self.apply_light_theme)
        dark_action.triggered.connect(self.apply_dark_theme)
        appearance_menu.addAction(light_action)
        appearance_menu.addAction(dark_action)
        
        # 帮助菜单
        help_menu = menubar.addMenu('帮助')
        
        about_action = QAction('关于', self)
        about_action.triggered.connect(self.show_about)
        help_menu.addAction(about_action)

    def create_status_bar(self):
        """创建状态栏"""
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("就绪")

    def create_query_tab(self, parent):
        """创建查询标签页"""
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        
        # 分割器：上部分为查询区，下部分为结果区
        splitter = QSplitter(Qt.Orientation.Vertical)
        self.create_query_area(splitter)
        self.create_result_area(splitter)
        splitter.setChildrenCollapsible(False)
        splitter.setHandleWidth(6)
        splitter.setSizes([420, 480])
        query_layout.addWidget(splitter)
        
        parent.addTab(query_widget, "SQL查询")


    def create_table_management_tab(self, parent):
        """创建表管理标签页"""
        table_widget = QWidget()
        table_layout = QVBoxLayout(table_widget)
        
        # 表列表区域
        table_group = QGroupBox("数据库表")
        table_group_layout = QVBoxLayout(table_group)
        # 阴影效果
        effect1 = QGraphicsDropShadowEffect(self)
        effect1.setBlurRadius(18)
        effect1.setOffset(0, 2)
        effect1.setColor(QColor(0, 0, 0, 50))
        table_group.setGraphicsEffect(effect1)
        
        self.table_list = QTableWidget()
        self.table_list.setColumnCount(3)
        self.table_list.setHorizontalHeaderLabels(["表名", "记录数", "创建时间"])
        # 表格展示优化
        self.table_list.setAlternatingRowColors(True)
        self.table_list.setSortingEnabled(True)
        self.table_list.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.table_list.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        header = self.table_list.horizontalHeader()
        header.setStretchLastSection(True)
        header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        # 图标列（可选，将来可扩展）
        table_group_layout.addWidget(self.table_list)
        
        refresh_tables_btn = QPushButtonBase("刷新表列表")
        refresh_tables_btn.clicked.connect(self.refresh_tables)
        refresh_tables_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_BrowserReload))
        table_group_layout.addWidget(refresh_tables_btn)
        
        table_layout.addWidget(table_group)
        
        # 表结构区域
        structure_group = QGroupBox("表结构")
        structure_group_layout = QVBoxLayout(structure_group)
        effect2 = QGraphicsDropShadowEffect(self)
        effect2.setBlurRadius(18)
        effect2.setOffset(0, 2)
        effect2.setColor(QColor(0, 0, 0, 50))
        structure_group.setGraphicsEffect(effect2)
        
        self.structure_table = QTableWidget()
        self.structure_table.setColumnCount(4)
        self.structure_table.setHorizontalHeaderLabels(["字段名", "类型", "是否为空", "键"])
        self.structure_table.setAlternatingRowColors(True)
        self.structure_table.setSortingEnabled(True)
        self.structure_table.setSelectionBehavior(QTableWidget.SelectionBehavior.SelectRows)
        self.structure_table.setEditTriggers(QTableWidget.EditTrigger.NoEditTriggers)
        s_header = self.structure_table.horizontalHeader()
        s_header.setStretchLastSection(True)
        s_header.setDefaultAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        structure_group_layout.addWidget(self.structure_table)
        
        table_layout.addWidget(structure_group)
        
        parent.addTab(table_widget, "表管理")

    def create_connection_group(self, parent_layout):
        """创建数据库连接设置区域"""
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

        conn_layout.addWidget(QLabel("用户名:"), 0, 2)
        conn_layout.addWidget(self.user_edit, 0, 3)

        conn_layout.addWidget(QLabel("密码:"), 1, 0)
        self.password_edit.setEchoMode(QLineEdit.EchoMode.Password)
        conn_layout.addWidget(self.password_edit, 1, 1)

        conn_layout.addWidget(QLabel("数据库名:"), 1, 2)
        conn_layout.addWidget(self.dbname_edit, 1, 3)

        # 连接按钮 - 只在初始化时连接一次信号
        self.connect_btn = QPushButtonBase("连接数据库")
        # 正确的信号连接：控件.信号.connect(槽函数)
        self.connect_btn.clicked.connect(self.on_connect_button_clicked)
        self.connect_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogYesButton))
        conn_layout.addWidget(self.connect_btn, 1, 4)

        parent_layout.addWidget(conn_group)

    def create_query_area(self, parent):
        """创建SQL查询区域"""
        query_widget = QWidget()
        query_layout = QVBoxLayout(query_widget)
        query_layout.setSpacing(8)
        query_layout.setContentsMargins(4, 4, 4, 4)

        # 查询模板区域
        template_group = QGroupBox("查询模板")
        template_layout = QVBoxLayout(template_group)
        template_layout.setSpacing(6)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(18)
        effect.setOffset(0, 2)
        effect.setColor(QColor(0, 0, 0, 50))
        template_group.setGraphicsEffect(effect)
        
        template_btn_layout = QHBoxLayout()
        template_btn_layout.setSpacing(6)
        
        # 常用查询模板按钮
        templates = [
            ("查看所有表", "SHOW TABLES;"),
            ("查看表结构", "DESCRIBE dayfund_spider_data;"),
            ("查看前10条记录", "SELECT * FROM dayfund_spider_data LIMIT 10;"),
            ("统计记录数", "SELECT COUNT(*) as 总记录数 FROM dayfund_spider_data;"),
            ("按日增长排序", "SELECT `基金名称`, `日增长(%)` FROM dayfund_spider_data ORDER BY `日增长(%)` DESC LIMIT 10;"),
            ("按近1年排序", "SELECT `基金名称`, `近1年(%)` FROM dayfund_spider_data ORDER BY `近1年(%)` DESC LIMIT 10;"),
            ("按近1周排序", "SELECT `基金名称`, `近1周(%)` FROM dayfund_spider_data ORDER BY `近1周(%)` DESC LIMIT 10;"),
            ("按近1月排序", "SELECT `基金名称`, `近1月(%)` FROM dayfund_spider_data ORDER BY `近1月(%)` DESC LIMIT 10;"),
            ("查看正收益基金", "SELECT `基金名称`, `日增长(%)`, `近1周(%)`, `近1月(%)` FROM dayfund_spider_data WHERE `日增长(%)` > 0 ORDER BY `日增长(%)` DESC LIMIT 20;"),
            ("查看负收益基金", "SELECT `基金名称`, `日增长(%)`, `近1周(%)`, `近1月(%)` FROM dayfund_spider_data WHERE `日增长(%)` < 0 ORDER BY `日增长(%)`  LIMIT 20;")
        ]
        
        for name, sql in templates:
            btn = QPushButtonBase(name)
            btn.clicked.connect(lambda checked, s=sql: self.insert_template(s))
            btn.setCursor(Qt.CursorShape.PointingHandCursor)
            btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_FileDialogToParent))
            template_btn_layout.addWidget(btn)
        
        template_layout.addLayout(template_btn_layout)
        query_layout.addWidget(template_group)

        # SQL编辑区域
        query_group = QGroupBox("SQL查询")
        query_group_layout = QVBoxLayout(query_group)
        effectq = QGraphicsDropShadowEffect(self)
        effectq.setBlurRadius(18)
        effectq.setOffset(0, 2)
        effectq.setColor(QColor(0, 0, 0, 50))
        query_group.setGraphicsEffect(effectq)

        # 查询历史下拉框
        history_layout = QHBoxLayout()
        history_layout.addWidget(QLabel("查询历史:"))
        history_layout.addWidget(self.history_combo)
        self.history_combo.currentTextChanged.connect(self.load_history_query)
        query_group_layout.addLayout(history_layout)

        self.sql_edit.setFont(QFont("Consolas", 10))
        self.sql_edit.setPlaceholderText("请输入SQL查询语句...\n例如: SELECT * FROM dayfund_spider_data LIMIT 10;")
        self.sql_edit.setMinimumHeight(140)
        self.sql_edit.setLineWrapMode(QTextEdit.LineWrapMode.NoWrap)
        # 语法高亮
        try:
            self.sql_highlighter = SQLHighlighter(self.sql_edit.document())
        except Exception:
            pass
        query_group_layout.addWidget(self.sql_edit)

        # 按钮区域
        btn_layout = QHBoxLayout()
        self.execute_btn = QPushButtonBase("执行查询")
        self.execute_btn.clicked.connect(self.on_execute_clicked)
        self.execute_btn.setEnabled(False)  # 初始禁用
        self.execute_btn.setDefault(True)
        self.execute_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

        self.clear_btn = QPushButtonBase("清除")
        self.clear_btn.clicked.connect(self.sql_edit.clear)
        self.clear_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogResetButton))

        save_query_btn = QPushButtonBase("保存查询")
        save_query_btn.clicked.connect(self.save_query_to_history)
        save_query_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_DialogSaveButton))

        btn_layout.addWidget(self.execute_btn)
        btn_layout.addWidget(self.clear_btn)
        btn_layout.addWidget(save_query_btn)
        btn_layout.addStretch()
        query_group_layout.addLayout(btn_layout)

        query_layout.addWidget(query_group)
        parent.addWidget(query_widget)

    def create_result_area(self, parent):
        """创建结果显示区域"""
        result_widget = QWidget()
        result_layout = QVBoxLayout(result_widget)

        result_group = QGroupBox("查询结果")
        result_group_layout = QVBoxLayout(result_group)
        effect = QGraphicsDropShadowEffect(self)
        effect.setBlurRadius(18)
        effect.setOffset(0, 2)
        effect.setColor(QColor(0, 0, 0, 50))
        result_group.setGraphicsEffect(effect)

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
        
        result_btn_layout.addWidget(export_csv_btn)
        result_btn_layout.addWidget(export_excel_btn)
        result_btn_layout.addWidget(copy_btn)
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

        result_layout.addWidget(result_group)
        parent.addWidget(result_widget)

    def apply_app_styles(self):
        """应用统一样式（不改动功能）"""
        # 统一字体
        base_font = QFont("Microsoft YaHei", 10)
        self.setFont(base_font)

        # 如果启用 Fluent，则不再叠加自定义浅色 QSS，避免与 Fluent 冲突
        if FLUENT_AVAILABLE:
            return

        # 否则应用原有浅色样式
        light_style = """
        QWidget { font-size: 10pt; }
        QMainWindow { background: #f7f9fc; }
        QGroupBox { border: 1px solid #e6eaf0; border-radius: 10px; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 2px 6px; color: #3c3f43; background: transparent; }
        QTabBar::tab { padding: 8px 14px; border: 1px solid #e6eaf0; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; background: #ffffff; }
        QTabBar::tab:selected { background: #eaf2ff; color: #0d47a1; }
        QTabWidget::pane { border: 1px solid #e6eaf0; top: -1px; border-radius: 8px; }
        QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1976d2, stop:1 #42a5f5); color: white; border: none; padding: 7px 14px; border-radius: 8px; }
        QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1565c0, stop:1 #2196f3); }
        QPushButton:pressed { background: #1565c0; }
        QPushButton:disabled { background: #bdbdbd; color: #eeeeee; }
        QLineEdit, QTextEdit, QComboBox { background: #ffffff; border: 1px solid #d3dae6; border-radius: 8px; padding: 6px 8px; }
        QTextEdit { font-family: Consolas, "Courier New", monospace; }
        QTableView { gridline-color: #e0e0e0; selection-background-color: #e3f2fd; selection-color: #0d47a1; background: #ffffff; border: 1px solid #e6eaf0; border-radius: 8px; }
        QHeaderView::section { background: #f0f3f7; padding: 8px; border: 1px solid #e6eaf0; border-radius: 0px; }
        QStatusBar { background: #f0f3f7; }
        QProgressBar { background: #e9eef5; border: 1px solid #d0d7e2; border-radius: 8px; height: 10px; }
        QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #42a5f5, stop:1 #64b5f6); border-radius: 8px; }
        """
        self.setStyleSheet(light_style)

    def apply_dark_theme(self):
        """切换到深色主题（仅外观）"""
        # 若启用 Fluent：设置 Fluent 深色与主色，但仍需对 Qt 原生控件应用深色调色板+QSS
        self.current_theme = 'dark'
        if FLUENT_AVAILABLE:
            try:
                setTheme(Theme.DARK)
                setThemeColor(QColor("#0B5CAD"))
            except Exception:
                pass
        dark_palette = QPalette()
        dark_palette.setColor(QPalette.ColorRole.Window, QColor(30, 32, 35))
        dark_palette.setColor(QPalette.ColorRole.WindowText, QColor(220, 223, 228))
        dark_palette.setColor(QPalette.ColorRole.Base, QColor(22, 24, 28))
        dark_palette.setColor(QPalette.ColorRole.AlternateBase, QColor(30, 32, 35))
        dark_palette.setColor(QPalette.ColorRole.ToolTipBase, QColor(220, 223, 228))
        dark_palette.setColor(QPalette.ColorRole.ToolTipText, QColor(220, 223, 228))
        dark_palette.setColor(QPalette.ColorRole.Text, QColor(220, 223, 228))
        dark_palette.setColor(QPalette.ColorRole.Button, QColor(45, 47, 52))
        dark_palette.setColor(QPalette.ColorRole.ButtonText, QColor(220, 223, 228))
        dark_palette.setColor(QPalette.ColorRole.BrightText, Qt.GlobalColor.red)
        dark_palette.setColor(QPalette.ColorRole.Highlight, QColor(66, 133, 244))
        dark_palette.setColor(QPalette.ColorRole.HighlightedText, QColor(0, 0, 0))
        QApplication.instance().setPalette(dark_palette)

        dark_style = """
        QWidget { font-size: 10pt; color: #dce0e6; }
        QMainWindow { background: #1e2023; }
        QGroupBox { border: 1px solid #2c2f33; border-radius: 10px; margin-top: 10px; }
        QGroupBox::title { subcontrol-origin: margin; left: 12px; padding: 2px 6px; color: #cfd3da; }
        QTabBar::tab { padding: 8px 14px; border: 1px solid #2c2f33; border-bottom: none; border-top-left-radius: 8px; border-top-right-radius: 8px; background: #2a2d31; }
        QTabBar::tab:selected { background: #0f172a; color: #8ab4ff; }
        QTabWidget::pane { border: 1px solid #2c2f33; top: -1px; border-radius: 8px; }
        QPushButton { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1e88e5, stop:1 #64b5f6); color: white; border: none; padding: 7px 14px; border-radius: 8px; }
        QPushButton:hover { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #1565c0, stop:1 #42a5f5); }
        QPushButton:pressed { background: #1565c0; }
        QPushButton:disabled { background: #555b66; color: #9aa1ac; }
        QLineEdit, QTextEdit, QComboBox { background: #1a1c1f; border: 1px solid #2f343a; border-radius: 8px; padding: 6px 8px; color: #dce0e6; }
        QTextEdit { font-family: Consolas, "Courier New", monospace; }
        QTableView { gridline-color: #2f343a; selection-background-color: #263238; selection-color: #90caf9; background: #1a1c1f; border: 1px solid #2c2f33; border-radius: 8px; }
        QHeaderView::section { background: #2a2d31; padding: 8px; border: 1px solid #2c2f33; color: #cfd3da; }
        QStatusBar { background: #2a2d31; }
        QProgressBar { background: #121417; border: 1px solid #2f343a; border-radius: 8px; height: 10px; }
        QProgressBar::chunk { background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #42a5f5, stop:1 #64b5f6); border-radius: 8px; }
        """
        self.setStyleSheet(dark_style)

    def apply_light_theme(self):
        """切换到浅色主题（仅外观）"""
        self.current_theme = 'light'
        if FLUENT_AVAILABLE:
            try:
                setTheme(Theme.LIGHT)
                setThemeColor(QColor("#0B5CAD"))
            except Exception:
                pass
        # 恢复标准调色板并清除深色QSS，然后按原逻辑应用浅色样式
        QApplication.instance().setPalette(QApplication.instance().style().standardPalette())
        self.setStyleSheet("")
        self.apply_app_styles()

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
                self.execute_btn.setEnabled(True)
                self.is_connected = True
                
                # 连接成功后刷新表列表
                self.refresh_tables()

        except Error as e:
            QMessageBox.critical(self, "连接失败", f"数据库连接失败:\n{str(e)}")
            self.status_label.setText("连接失败")
            self.status_bar.showMessage("连接失败")
        finally:
            self.progress_bar.setVisible(False)

    def disconnect_database(self):
        """断开数据库连接"""
        if self.connection and self.connection.is_connected():
            self.connection.close()
            self.status_label.setText("已断开连接")
            self.status_bar.showMessage("已断开数据库连接")
            self.connect_btn.setText("连接数据库")
            self.execute_btn.setEnabled(False)
            self.is_connected = False
            
            # 清空表列表
            self.table_list.setRowCount(0)
            self.structure_table.setRowCount(0)
            
            QMessageBox.information(self, "断开成功", "已断开数据库连接")

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
            # 显示执行进度
            self.progress_bar.setVisible(True)
            self.progress_bar.setRange(0, 0)
            self.status_bar.showMessage("正在执行查询...")
            self.execute_btn.setEnabled(False)
            
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

            cursor.close()
            
            # 保存查询到历史记录
            if sql not in self.sql_history:
                self.sql_history.append(sql)
                self.history_combo.addItem(sql[:50] + "..." if len(sql) > 50 else sql)

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
            self.execute_btn.setEnabled(True)

    def insert_template(self, sql_template):
        """插入查询模板"""
        self.sql_edit.setPlainText(sql_template)
        self.sql_edit.setFocus()

    def save_query_to_history(self):
        """保存查询到历史记录"""
        sql = self.sql_edit.toPlainText().strip()
        if sql and sql not in self.sql_history:
            self.sql_history.append(sql)
            self.history_combo.addItem(sql[:50] + "..." if len(sql) > 50 else sql)
            QMessageBox.information(self, "保存成功", "查询已保存到历史记录")

    def load_history_query(self, query_text):
        """加载历史查询"""
        if query_text:
            # 从历史记录中找到完整的SQL
            for sql in self.sql_history:
                if sql.startswith(query_text) or query_text in sql:
                    self.sql_edit.setPlainText(sql)
                    break

    def clear_history(self):
        """清除查询历史"""
        self.sql_history.clear()
        self.history_combo.clear()
        QMessageBox.information(self, "清除完成", "查询历史已清除")

    def refresh_tables(self):
        """刷新表列表"""
        if not self.connection or not self.connection.is_connected():
            return

        try:
            cursor = self.connection.cursor()
            cursor.execute("SHOW TABLES")
            tables = cursor.fetchall()
            
            self.table_list.setRowCount(len(tables))
            
            for i, (table_name,) in enumerate(tables):
                # 表名
                self.table_list.setItem(i, 0, QTableWidgetItem(table_name))
                
                # 记录数
                try:
                    cursor.execute(f"SELECT COUNT(*) FROM `{table_name}`")
                    count = cursor.fetchone()[0]
                    self.table_list.setItem(i, 1, QTableWidgetItem(str(count)))
                except:
                    self.table_list.setItem(i, 1, QTableWidgetItem("未知"))
                
                # 创建时间
                try:
                    cursor.execute(f"SELECT CREATE_TIME FROM information_schema.TABLES WHERE TABLE_SCHEMA='{self.dbname_edit.text()}' AND TABLE_NAME='{table_name}'")
                    create_time = cursor.fetchone()
                    if create_time:
                        self.table_list.setItem(i, 2, QTableWidgetItem(str(create_time[0])))
                    else:
                        self.table_list.setItem(i, 2, QTableWidgetItem("未知"))
                except:
                    self.table_list.setItem(i, 2, QTableWidgetItem("未知"))
            
            self.table_list.resizeColumnsToContents()
            
            # 连接表选择事件
            self.table_list.itemSelectionChanged.connect(self.show_table_structure)
            
            cursor.close()
            
        except Error as e:
            QMessageBox.critical(self, "错误", f"刷新表列表失败: {str(e)}")

    def show_table_structure(self):
        """显示表结构"""
        current_row = self.table_list.currentRow()
        if current_row < 0:
            return
            
        table_name = self.table_list.item(current_row, 0).text()
        
        try:
            cursor = self.connection.cursor()
            cursor.execute(f"DESCRIBE `{table_name}`")
            columns = cursor.fetchall()
            
            self.structure_table.setRowCount(len(columns))
            self.structure_table.setColumnCount(4)
            
            for i, (field, type_info, null, key, default, extra) in enumerate(columns):
                self.structure_table.setItem(i, 0, QTableWidgetItem(field))
                self.structure_table.setItem(i, 1, QTableWidgetItem(type_info))
                self.structure_table.setItem(i, 2, QTableWidgetItem(null))
                self.structure_table.setItem(i, 3, QTableWidgetItem(key))
            
            self.structure_table.resizeColumnsToContents()
            cursor.close()
            
        except Error as e:
            QMessageBox.critical(self, "错误", f"获取表结构失败: {str(e)}")

    def export_results(self, format_type='csv'):
        """导出查询结果"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有数据可导出")
            return

        # 获取保存路径
        if format_type == 'csv':
            file_path, _ = QFileDialog.getSaveFileName(self, "保存CSV文件", f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv", "CSV文件 (*.csv)")
        else:
            file_path, _ = QFileDialog.getSaveFileName(self, "保存Excel文件", f"query_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx", "Excel文件 (*.xlsx)")

        if not file_path:
            return

        try:
            # 准备数据
            data = []
            headers = []
            
            # 获取表头
            for col in range(self.result_table.columnCount()):
                headers.append(self.result_table.horizontalHeaderItem(col).text())
            
            # 获取数据
            for row in range(self.result_table.rowCount()):
                row_data = []
                for col in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            # 创建DataFrame
            df = pd.DataFrame(data, columns=headers)
            
            # 导出文件
            if format_type == 'csv':
                df.to_csv(file_path, index=False, encoding='utf-8-sig')
            else:
                df.to_excel(file_path, index=False, engine='openpyxl')
            
            QMessageBox.information(self, "导出成功", f"数据已导出到: {file_path}")
            
        except Exception as e:
            QMessageBox.critical(self, "导出失败", f"导出文件失败: {str(e)}")

    def copy_results(self):
        """复制结果到剪贴板"""
        if self.result_table.rowCount() == 0:
            QMessageBox.warning(self, "警告", "没有数据可复制")
            return

        try:
            # 获取所有数据
            data = []
            headers = []
            
            # 获取表头
            for col in range(self.result_table.columnCount()):
                headers.append(self.result_table.horizontalHeaderItem(col).text())
            
            # 获取数据
            for row in range(self.result_table.rowCount()):
                row_data = []
                for col in range(self.result_table.columnCount()):
                    item = self.result_table.item(row, col)
                    row_data.append(item.text() if item else "")
                data.append(row_data)
            
            # 创建DataFrame并转换为CSV格式
            df = pd.DataFrame(data, columns=headers)
            csv_data = df.to_csv(index=False)
            
            # 复制到剪贴板
            from PyQt6.QtWidgets import QApplication
            clipboard = QApplication.clipboard()
            clipboard.setText(csv_data)
            
            QMessageBox.information(self, "复制成功", "数据已复制到剪贴板")
            
        except Exception as e:
            QMessageBox.critical(self, "复制失败", f"复制数据失败: {str(e)}")

    def show_about(self):
        """显示关于对话框"""
        QMessageBox.about(self, "关于", 
                         "MySQL数据库查询工具 v2.0\n\n"
                         "功能特点:\n"
                         "• 支持MySQL数据库连接\n"
                         "• 提供常用查询模板\n"
                         "• 查询历史记录\n"
                         "• 表结构查看\n"
                         "• 结果导出(CSV/Excel)\n"
                         "• 基金数据分析专用\n\n"
                         "适用于基金数据爬虫项目")


class SQLHighlighter(QSyntaxHighlighter):
    """简易 SQL 语法高亮（仅外观）"""
    def __init__(self, document):
        super().__init__(document)
        self.highlight_rules = []

        keyword_format = QTextCharFormat()
        keyword_format.setForeground(QColor('#2962ff'))
        keyword_format.setFontWeight(QFont.Weight.Bold)
        keywords = [
            'SELECT', 'FROM', 'WHERE', 'AND', 'OR', 'NOT', 'IN', 'IS', 'NULL',
            'LIKE', 'LIMIT', 'ORDER', 'BY', 'GROUP', 'HAVING', 'AS', 'ON',
            'JOIN', 'INNER', 'LEFT', 'RIGHT', 'FULL', 'OUTER', 'UNION', 'ALL',
            'INSERT', 'INTO', 'VALUES', 'UPDATE', 'SET', 'DELETE', 'CREATE', 'TABLE',
            'PRIMARY', 'KEY', 'FOREIGN', 'REFERENCES', 'DESC', 'DESCRIBE', 'SHOW', 'EXPLAIN'
        ]
        for word in keywords:
            pattern = QRegularExpression(rf"\\b{word}\\b", QRegularExpression.PatternOption.CaseInsensitiveOption)
            self.highlight_rules.append((pattern, keyword_format))

        string_format = QTextCharFormat()
        string_format.setForeground(QColor('#43a047'))
        self.highlight_rules.append((QRegularExpression("'[^']*'"), string_format))
        self.highlight_rules.append((QRegularExpression('"[^"]*"'), string_format))

        number_format = QTextCharFormat()
        number_format.setForeground(QColor('#e53935'))
        self.highlight_rules.append((QRegularExpression(r"\b\d+\b"), number_format))

        comment_format = QTextCharFormat()
        comment_format.setForeground(QColor('#9e9e9e'))
        self.highlight_rules.append((QRegularExpression(r"--[^\n]*"), comment_format))

    def highlightBlock(self, text):
        for pattern, fmt in self.highlight_rules:
            it = pattern.globalMatch(text)
            while it.hasNext():
                m = it.next()
                self.setFormat(m.capturedStart(), m.capturedLength(), fmt)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    # 全局风格与字体（不改变功能）
    try:
        from PyQt6.QtWidgets import QStyleFactory
        app.setStyle("Fusion")
    except Exception:
        pass
    app.setFont(QFont("Microsoft YaHei", 10))
    # 启用 Fluent 深色金融配色（如可用）
    if FLUENT_AVAILABLE:
        try:
            setTheme(Theme.DARK)
            setThemeColor(QColor("#00C853"))
        except Exception:
            pass
    window = MySQLQueryTool()
    window.show()
    sys.exit(app.exec())


