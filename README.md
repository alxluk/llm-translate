# llm-translate

**llm-translate** - это приложение для перевода текста с использованием локальных и облачных моделей LLM (Large Language Models). Он поддерживает несколько провайдеров, включая:

- LM Studio
- Ollama
- OpenRouter (с API ключом)

Приложение позволяет выбирать модель, язык перевода, загружать файл для перевода и сохранять результат. Оно также поддерживает работу с кэшем для ускорения процесса перевода.

## Установка и запуск на Linux

### 1. **Установите зависимости**:
>На Debian/Ubuntu

```bash
sudo apt update && sudo apt install -y python3 python3-pip qt6-default
```
>На Arch Linux
```bash
sudo pacman -Syu python qt6-base python-pip
```
>На RHEL/CentOS
```bash
sudo yum install -y python3 python3-pip qt6-qtbase
```
### 2. **Создайте виртуальное окружение и установите пакеты python**:
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 3. **Запустите приложение**:
```bash
python translator_app.py
```

## Установка и запуск на Windows
1. **Установите Python**:
   - Убедитесь, что установлен Python 3.x (https://www.python.org/downloads/)

2. **Создайте виртуальное окружение и установите зависимости**:
    ```powershell
    python -m venv venv
    venv\Scripts\activate.ps1
    pip install -r requirements.txt
    ```

3. **Запустите приложение**:

```powershell
python translator_app.py
```

## **OpenRouter**
Если вы используете OpenRouter, убедитесь, что вы вставили ваш API ключ в файл `.env`:
  1. Скопируйте пример `.env.example` как `.env`:
     ```bash
     cp .env.example .env
     ```
  2. Откройте файл `.env` и замените `'KEY'` на ваш реальный API ключ
