import json
import sys

import markdown
import requests
from PySide6.QtWidgets import (
    QApplication, QMainWindow, QPushButton, QVBoxLayout, QWidget,
    QLineEdit, QListWidget, QLabel, QHBoxLayout, QMessageBox, QInputDialog,
    QListWidgetItem, QMenu, QStyledItemDelegate, QStyleOptionViewItem
)
from PySide6.QtGui import QPainter, QTextDocument
from PySide6.QtCore import Qt, QThread, Signal, QRect, QSize


class MarkdownDelegate(QStyledItemDelegate):
    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index):
        """
        自定义绘制函数，用于将Markdown文本渲染为HTML显示在界面上。
        """
        text = index.data()
        html = markdown.markdown(text)  # 将 Markdown 转换为 HTML

        painter.save()
        doc = QTextDocument()
        doc.setHtml(html)
        doc.setTextWidth(option.rect.width())

        painter.translate(option.rect.left(), option.rect.top())
        clip = QRect(0, 0, option.rect.width(), option.rect.height())
        painter.setClipRect(clip)
        doc.drawContents(painter)
        painter.restore()

    def sizeHint(self, option, index):
        """
        提供项的大小提示，基于Markdown转换后的HTML内容。
        """
        text = index.data()
        html = markdown.markdown(text)

        doc = QTextDocument()
        doc.setHtml(html)
        doc.setTextWidth(option.rect.width())
        return QSize(doc.idealWidth(), doc.size().height())


class Worker(QThread):
    finished = Signal(str)  # 成功时发送响应数据
    error = Signal(str)  # 错误时发送错误信息

    def __init__(self, url, params):
        """
        初始化Worker线程，用于处理网络请求。
        """
        super().__init__()
        self.url = url
        self.params = params

    def run(self):
        """
        线程执行的主函数，发送网络请求并处理响应。
        """
        try:
            response = requests.post(self.url, json=self.params)
            if response.status_code == 200:
                self.finished.emit(response.text)  # 发送成功信号
            else:
                self.error.emit("Failed to send message")
        except requests.exceptions.Timeout:
            self.error.emit("Request timed out")


class ChatWindow(QMainWindow):
    def __init__(self):
        """
        初始化聊天窗口及其组件和布局。
        """
        STYLESHEET = """
        QWidget {
            font-size: 14px;
        }

        QMainWindow {
            background-color: #f0f0f0;
        }

        QPushButton {
            background-color: #0078D7;
            color: white;
            border-style: none;
            padding: 10px;
            border-radius: 5px;
        }

        QPushButton:hover {
            background-color: #0053ba;
        }

        QPushButton:pressed {
            background-color: #00397a;
        }

        QLineEdit {
            border: 2px solid #0078D7;
            border-radius: 5px;
            padding: 5px;
        }

        QListWidget {
            border: 1px solid #0078D7;
            border-radius: 5px;
        }

        QMessageBox {
            background-color: #ffffff;
        }
        
        QMenu {
            background-color: #f0f0f0; /* 浅灰色背景，与窗口背景色一致 */
            border: 1px solid #0078D7; /* 使用主题蓝色作为边框 */
            border-radius: 5px; /* 添加圆角 */
            color: #333; /* 文字颜色 */
        }
        
        QMenu::item {
            padding: 5px 20px;
            background-color: transparent;
        }
        
        QMenu::item:selected {
            background-color: #0078D7; /* 深蓝色背景 */
            color: white; /* 白色文字 */
            border-radius: 3px; /* 选中项也添加圆角效果 */
        }
            
        QDialog {
            background-color: #f0f0f0;
        }
        
        QLabel {
            color: #333333;
            font-weight: bold;
        }
        
        QLineEdit:focus {
            border: 2px solid #0053ba;
        }
        
        QScrollBar:vertical {
            border: none;
            background: #f0f0f0;
            width: 10px;
        }
        
        QScrollBar::handle:vertical {
            background: #0078D7;
            min-height: 20px;
        }
        
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            background: none;
        }

        """

        super().__init__()
        self.setStyleSheet(STYLESHEET)
        self.setWindowTitle("MyNextChat - FastAPI Chat Application")
        self.resize(1500, 1000)

        # 主布局和控件
        main_layout = QHBoxLayout()
        self.session_list = QListWidget()
        self.chat_history = QListWidget()
        # self.chat_history.setItemDelegate(MarkdownDelegate())
        self.message_input = QLineEdit("")
        self.send_message_btn = QPushButton("Send Message")
        self.create_session_btn = QPushButton("Create New Session")
        self.delete_session_btn = QPushButton("Delete Selected Session")
        self.last_user_message_item = None

        # 会话列表和聊天区域布局
        session_layout = QVBoxLayout()
        session_layout.addWidget(self.create_session_btn)
        session_layout.addWidget(self.delete_session_btn)
        session_layout.addWidget(self.session_list)

        chat_layout = QVBoxLayout()
        chat_layout.addWidget(self.chat_history)
        chat_layout.addWidget(self.message_input)
        chat_layout.addWidget(self.send_message_btn)

        # 组合布局
        main_layout.addLayout(session_layout, 1)
        main_layout.addLayout(chat_layout, 4)

        # 设置按钮的点击事件
        self.session_list.currentItemChanged.connect(self.select_session)
        self.send_message_btn.clicked.connect(self.send_message)
        self.create_session_btn.clicked.connect(self.create_session)
        self.delete_session_btn.clicked.connect(self.delete_session)
        self.chat_history.setContextMenuPolicy(Qt.CustomContextMenu)
        self.chat_history.customContextMenuRequested.connect(self.show_context_menu)

        # 设置中心小部件
        central_widget = QWidget()
        central_widget.setLayout(main_layout)
        self.setCentralWidget(central_widget)

        # 初始化加载所有会话
        self.list_sessions()

    def list_sessions(self):
        """
        从服务器加载并显示所有会话。
        """
        self.session_list.clear()
        response = requests.get("http://localhost:8000/api/sessions/")
        if response.status_code == 200:
            sessions_data = response.json()
            sessions = sessions_data.get('sessions', [])
            for session in sessions:
                self.session_list.addItem(f"{session['session_id']} - {session['session_name']}")
        else:
            error_msg = response.json().get('detail', 'Unknown error occurred.')
            QMessageBox.critical(self, "Error", f"Failed to load sessions: {error_msg}")

    def create_session(self):
        """
        创建新的会话
        """
        name, ok = QInputDialog.getText(self, "Create Session", "Enter session name:")
        if ok and name:
            response = requests.post("http://localhost:8000/api/sessions/", params={"name": name})
            if response.status_code == 201:
                self.list_sessions()
            else:
                error_msg = response.json().get('detail', 'Unknown error occurred.')
                QMessageBox.critical(self, "Error", f"Failed to create session: {error_msg}")

    def delete_session(self):
        """
        删除一个指定会话
        """
        current = self.session_list.currentItem()
        if current:
            session_id = current.text().split(" - ")[0]
            response = requests.delete(f"http://localhost:8000/api/sessions/{session_id}")
            if response.status_code == 200:
                self.list_sessions()
            else:
                error_msg = response.json().get('detail', 'Unknown error occurred.')
                QMessageBox.critical(self, "Error", f"Failed to delete session: {error_msg}")

    def select_session(self, current, previous):
        """
        选择聊天会话时加载并显示相关消息。
        """
        if current:
            session_id = current.text().split(" - ")[0]
            response = requests.get(f"http://localhost:8000/api/messages/{session_id}")
            if response.status_code == 200:
                self.chat_history.clear()
                messages = response.json()['messages']
                for msg in messages:
                    item = QListWidgetItem(f"{msg['character_name']}: {msg['message']}")
                    item.setData(Qt.UserRole, msg['id'])  # 将消息ID存储为用户角色数据
                    self.chat_history.addItem(item)
            else:
                QMessageBox.critical(self, "Error", "Failed to load session messages")

    def send_message(self):
        """
        发送消息到当前选中的会话。
        """
        current = self.session_list.currentItem()
        if current:
            session_id = current.text().split(" - ")[0]
            message = self.message_input.text()
            params = {
                "session_id": session_id,
                "user_message": message
            }
            url = "http://localhost:8000/api/chat/"
            # 添加用户消息到界面，但暂时不包含ID
            user_message_item = QListWidgetItem(f"user: {message}")
            self.chat_history.addItem(user_message_item)
            self.last_user_message_item = user_message_item  # 保存最后一个用户消息项的引用

            self.worker = Worker(url, params)
            self.worker.finished.connect(self.handle_response)
            self.worker.error.connect(self.handle_error)
            self.worker.start()
        self.message_input.clear()

    def handle_response(self, response_text):
        """
        处理从后端接收到的响应。
        """
        response = json.loads(response_text)
        ai_message_text = f"{response['character_name']}: {response['response']}"

        # 更新最后一个用户消息项，添加ID
        if hasattr(self, 'last_user_message_item'):
            self.last_user_message_item.setData(Qt.UserRole, response['user_message_id'])
            self.last_user_message_item = None

        # 创建AI消息的列表项，包含ID
        ai_message_item = QListWidgetItem(ai_message_text)
        ai_message_item.setData(Qt.UserRole, response['ai_message_id'])
        self.chat_history.addItem(ai_message_item)

    def handle_error(self, error_msg):
        """
        处理网络请求过程中发生的错误。
        """
        QMessageBox.critical(self, "错误", error_msg)

    def show_context_menu(self, position):
        """
        在聊天历史记录中显示上下文菜单。
        """
        menu = QMenu()
        copy_action = menu.addAction("Copy Message")
        delete_action = menu.addAction("Delete Message")

        action = menu.exec(self.chat_history.mapToGlobal(position))
        if action == copy_action:
            self.copy_selected_message()
        elif action == delete_action:
            self.delete_selected_message()

    def copy_selected_message(self):
        """
        复制选中的消息到剪贴板。
        """
        selected_item = self.chat_history.currentItem()
        if selected_item:
            QApplication.clipboard().setText(selected_item.text())

    def delete_selected_message(self):
        """
        删除选中的消息。
        """
        selected_item = self.chat_history.currentItem()
        if selected_item:
            message_id = selected_item.data(Qt.UserRole)  # 从用户角色数据中获取消息ID
            response = requests.delete(f"http://localhost:8000/api/messages/{message_id}")
            if response.status_code == 200:
                self.chat_history.takeItem(self.chat_history.row(selected_item))
            else:
                error_msg = response.json().get('detail', 'Unknown error occurred.')
                QMessageBox.critical(self, "Error", f"Failed to delete message: {error_msg}")


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = ChatWindow()
    window.show()
    sys.exit(app.exec())
