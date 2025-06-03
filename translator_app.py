import sys
import re
import json
import os
import requests
from dotenv import load_dotenv

from PyQt6.QtWidgets import (
    QApplication, QWidget, QLabel, QPushButton, QVBoxLayout, QHBoxLayout,
    QFileDialog, QComboBox, QMessageBox, QProgressBar, QSpinBox,
    QCheckBox
)
from PyQt6.QtCore import Qt, QThread, pyqtSignal

load_dotenv()


class TranslationWorker(QThread):
    progress = pyqtSignal(int)
    done = pyqtSignal(str)
    error = pyqtSignal(str)
    chunk_info = pyqtSignal(int, int)  

    def __init__(self, provider, model, lang, input_path, output_path, start_from=0):
        super().__init__()
        self.provider = provider
        self.model = model
        self.lang = lang
        self.input_path = input_path
        self.output_path = output_path
        self.start_from = start_from
        self.cache_path = output_path + ".cache.json"

    def run(self):
        try:
            with open(self.input_path, 'r', encoding='utf-8') as f:
                text = f.read()
            chunks = self.chunk_text_sliding_window(text)
            total_chunks = len(chunks)

            cache = {}
            if os.path.exists(self.cache_path):
                with open(self.cache_path, 'r', encoding='utf-8') as f:
                    cache = json.load(f)

            translated = ""
            for i, chunk in enumerate(chunks):
                if i < self.start_from:
                    continue

                self.chunk_info.emit(i + 1, total_chunks)

                if str(i) in cache:
                    result = cache[str(i)]
                else:
                    if self.provider == "LM Studio":
                        result = self.translate_lm_studio(chunk)
                    elif self.provider == "Ollama":
                        result = self.translate_ollama(chunk)
                    elif self.provider == "OpenRouter":
                        result = self.translate_openrouter(chunk)
                    else:
                        raise Exception("Неизвестный провайдер")
                    cache[str(i)] = result
                    with open(self.cache_path, 'w', encoding='utf-8') as f:
                        json.dump(cache, f, ensure_ascii=False, indent=2)

                translated += result.strip() + "\n\n"
                self.progress.emit(i + 1)

            with open(self.output_path, 'w', encoding='utf-8') as f:
                f.write(translated)

            self.done.emit("Перевод завершён и сохранён.")
        except Exception as e:
            self.error.emit(str(e))

    def translate_lm_studio(self, text):
        url = "http://localhost:1234/v1/chat/completions"
        headers = {"Content-Type": "application/json"}
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Ты переводчик. Переводи на {self.lang}."},
                {"role": "user", "content": text}
            ],
            "temperature": 0.7,
            "max_tokens": 2048
        }
        response = requests.post(url, headers=headers, json=payload)
        return response.json()["choices"][0]["message"]["content"]

    def translate_ollama(self, text):
        url = "http://localhost:11434/api/chat"
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Ты переводчик. Переводи на {self.lang}."},
                {"role": "user", "content": text}
            ],
            "stream": False
        }
        response = requests.post(url, json=payload)
        return response.json()["message"]["content"]

    def translate_openrouter(self, text):
        api_key = os.getenv("OPENROUTER_API_KEY")
        if not api_key:
            raise Exception("OPENROUTER_API_KEY не установлен в переменных окружения")

        url = "https://openrouter.ai/api/v1/chat/completions"
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": f"Ты переводчик. Переводи на {self.lang}."},
                {"role": "user", "content": text}
            ]
        }
        response = requests.post(url, headers=headers, json=payload)
        response_json = response.json()
        if "choices" not in response_json:
            raise Exception(f"Ошибка OpenRouter: {response_json.get('error', 'Нет поля choices')}\nПолный ответ: {json.dumps(response_json, ensure_ascii=False, indent=2)}")
        return response_json["choices"][0]["message"]["content"]

    def chunk_text_sliding_window(self, text, max_tokens=800, overlap_ratio=0.2):
        paragraphs = re.split(r'\n\s*\n', text)
        approx_chars = max_tokens * 4
        chunks = []
        current = ""
        i = 0

        while i < len(paragraphs):
            while i < len(paragraphs) and len(current) + len(paragraphs[i]) < approx_chars:
                current += paragraphs[i] + "\n\n"
                i += 1
            chunks.append(current.strip())

            overlap = int(len(chunks[-1].split('\n\n')) * overlap_ratio)
            i = max(0, i - overlap)
            current = ""

        return chunks


class TranslatorApp(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Local LLM translator")
        self.init_ui()

    def init_ui(self):
        layout = QVBoxLayout()

        
        self.only_free_checkbox = QCheckBox("Показывать только бесплатные модели (OpenRouter)")
        self.only_free_checkbox.stateChanged.connect(self.load_models)
        layout.addWidget(self.only_free_checkbox)

        provider_layout = QHBoxLayout()
        provider_layout.addWidget(QLabel("Провайдер:"))
        self.provider_combo = QComboBox()
        self.provider_combo.addItems(["LM Studio", "Ollama", "OpenRouter"])
        self.provider_combo.currentTextChanged.connect(self.load_models)
        provider_layout.addWidget(self.provider_combo)
        layout.addLayout(provider_layout)

        model_layout = QHBoxLayout()
        model_layout.addWidget(QLabel("Модель:"))
        self.model_combo = QComboBox()
        model_layout.addWidget(self.model_combo)
        layout.addLayout(model_layout)

        lang_layout = QHBoxLayout()
        lang_layout.addWidget(QLabel("Перевести на:"))
        self.lang_combo = QComboBox()
        self.lang_combo.addItems(["русский", "английский"])
        lang_layout.addWidget(self.lang_combo)
        layout.addLayout(lang_layout)

        file_layout = QHBoxLayout()
        self.file_label = QLabel("Файл не выбран")
        file_btn = QPushButton("Выбрать файл")
        file_btn.clicked.connect(self.select_file)
        file_layout.addWidget(file_btn)
        file_layout.addWidget(self.file_label)
        layout.addLayout(file_layout)

        save_layout = QHBoxLayout()
        self.save_label = QLabel("Место сохранения не выбрано")
        save_btn = QPushButton("Сохранить как...")
        save_btn.clicked.connect(self.select_save_location)
        save_layout.addWidget(save_btn)
        save_layout.addWidget(self.save_label)
        layout.addLayout(save_layout)

        restart_layout = QHBoxLayout()
        restart_layout.addWidget(QLabel("С фрагмента:", self))
        self.start_spin = QSpinBox()
        self.start_spin.setMinimum(0)
        self.start_spin.setMaximum(999)
        restart_layout.addWidget(self.start_spin)
        layout.addLayout(restart_layout)

        self.progress = QProgressBar()
        self.progress.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.progress)

        self.status_label = QLabel("")
        layout.addWidget(self.status_label)

        translate_btn = QPushButton("Запустить перевод")
        translate_btn.clicked.connect(self.run_translation)
        layout.addWidget(translate_btn)

        self.setLayout(layout)
        self.load_models()

    def select_file(self):
        file_path, _ = QFileDialog.getOpenFileName(self, "Выберите файл", "", "Text Files (*.txt)")
        if file_path:
            self.file_label.setText(file_path)

    def select_save_location(self):
        save_path, _ = QFileDialog.getSaveFileName(self, "Сохранить перевод", "", "Text Files (*.txt)")
        if save_path:
            self.save_label.setText(save_path)

    def load_models(self):
        provider = self.provider_combo.currentText()
        self.model_combo.clear()
        try:
            if provider == "LM Studio":
                resp = requests.get("http://localhost:1234/v1/models")
                models = [m["id"] for m in resp.json().get("data", [])]
            elif provider == "Ollama":
                resp = requests.get("http://localhost:11434/api/tags")
                models = [m["name"] for m in resp.json().get("models", [])]
            elif provider == "OpenRouter":
                api_key = os.getenv("OPENROUTER_API_KEY")
                if not api_key:
                    raise Exception("OPENROUTER_API_KEY не установлен")
                resp = requests.get("https://openrouter.ai/api/v1/models", headers={"Authorization": f"Bearer {api_key}"})
                all_models = resp.json().get("data", [])
                if self.only_free_checkbox.isChecked():
                    models = [m["id"] for m in all_models if "free" in m["id"].lower()]
                else:
                    models = [m["id"] for m in all_models]
            else:
                models = []
            self.model_combo.addItems(models)
        except Exception as e:
            self.model_combo.addItem("Ошибка загрузки моделей")

    def run_translation(self):
        provider = self.provider_combo.currentText()
        model = self.model_combo.currentText().strip()
        lang = self.lang_combo.currentText()
        input_path = self.file_label.text()
        output_path = self.save_label.text()
        start_from = self.start_spin.value()

        if not model or not input_path or not output_path:
            QMessageBox.warning(self, "Ошибка", "Укажите модель, файл и путь сохранения.")
            return

        self.worker = TranslationWorker(provider, model, lang, input_path, output_path, start_from)
        self.worker.progress.connect(self.progress.setValue)
        self.worker.chunk_info.connect(self.update_chunk_status)
        self.worker.done.connect(lambda msg: QMessageBox.information(self, "Готово", msg))
        self.worker.error.connect(lambda err: QMessageBox.critical(self, "Ошибка", err))
        self.worker.start()

    def update_chunk_status(self, current, total):
        self.status_label.setText(f"Фрагмент {current} из {total}")
        self.progress.setMaximum(total)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = TranslatorApp()
    window.resize(720, 500)
    window.show()
    sys.exit(app.exec())
