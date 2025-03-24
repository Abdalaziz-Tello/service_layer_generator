import sys
import os
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                            QHBoxLayout, QLabel, QPushButton, QFileDialog, 
                            QMessageBox, QLineEdit)
from PyQt6.QtCore import Qt, QMimeData
from PyQt6.QtGui import QDragEnterEvent, QDropEvent
from service_layer_generator import ServiceLayerGenerator

class DragDropLabel(QLabel):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setStyleSheet("""
            QLabel {
                border: 2px dashed #aaa;
                border-radius: 5px;
                padding: 20px;
                background: #f0f0f0;
            }
            QLabel:hover {
                border: 2px dashed #666;
                background: #e0e0e0;
            }
        """)
        self.setText("Drag and drop OpenAPI JSON file here\nor click to browse")
        self.setAcceptDrops(True)
        self.file_path = None

    def dragEnterEvent(self, event: QDragEnterEvent):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent):
        files = [url.toLocalFile() for url in event.mimeData().urls()]
        if files and files[0].endswith('.json'):
            self.file_path = files[0]
            self.setText(f"Selected: {os.path.basename(files[0])}")
        else:
            QMessageBox.warning(self, "Invalid File", "Please select a JSON file")

    def mousePressEvent(self, event):
        file_path, _ = QFileDialog.getOpenFileName(
            self,
            "Select OpenAPI JSON File",
            "",
            "JSON Files (*.json)"
        )
        if file_path:
            self.file_path = file_path
            self.setText(f"Selected: {os.path.basename(file_path)}")

class ServiceLayerGeneratorGUI(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Flutter Service Layer Generator")
        self.setMinimumSize(600, 400)
        
        # Create central widget and layout
        central_widget = QWidget()
        self.setCentralWidget(central_widget)
        layout = QVBoxLayout(central_widget)
        
        # Create drag and drop area
        self.drag_drop_label = DragDropLabel()
        layout.addWidget(self.drag_drop_label)
        
        # Create output directory selection
        output_layout = QHBoxLayout()
        output_label = QLabel("Output Directory:")
        self.output_path = QLineEdit()
        self.output_path.setReadOnly(True)
        browse_button = QPushButton("Browse")
        browse_button.clicked.connect(self.select_output_directory)
        output_layout.addWidget(output_label)
        output_layout.addWidget(self.output_path)
        output_layout.addWidget(browse_button)
        layout.addLayout(output_layout)
        
        # Create generate button
        self.generate_button = QPushButton("Generate Service Layer")
        self.generate_button.clicked.connect(self.generate_service_layer)
        self.generate_button.setEnabled(False)
        layout.addWidget(self.generate_button)
        
        # Status label
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Set default output directory
        default_output = os.path.join(os.path.expanduser("~"), "flutter_service_layer")
        self.output_path.setText(default_output)

    def select_output_directory(self):
        directory = QFileDialog.getExistingDirectory(
            self,
            "Select Output Directory",
            self.output_path.text()
        )
        if directory:
            self.output_path.setText(directory)

    def generate_service_layer(self):
        if not self.drag_drop_label.file_path:
            QMessageBox.warning(self, "Error", "Please select an OpenAPI JSON file")
            return
            
        if not self.output_path.text():
            QMessageBox.warning(self, "Error", "Please select an output directory")
            return
            
        try:
            generator = ServiceLayerGenerator(
                self.drag_drop_label.file_path,
                self.output_path.text()
            )
            generator.generate()
            self.status_label.setText("Service layer generated successfully!")
            self.status_label.setStyleSheet("color: green")
            QMessageBox.information(
                self,
                "Success",
                f"Service layer generated successfully in:\n{self.output_path.text()}"
            )
        except Exception as e:
            self.status_label.setText(f"Error: {str(e)}")
            self.status_label.setStyleSheet("color: red")
            QMessageBox.critical(self, "Error", str(e))

    def update_generate_button(self):
        self.generate_button.setEnabled(
            bool(self.drag_drop_label.file_path) and bool(self.output_path.text())
        )

def main():
    app = QApplication(sys.argv)
    window = ServiceLayerGeneratorGUI()
    window.show()
    sys.exit(app.exec())

if __name__ == '__main__':
    main() 