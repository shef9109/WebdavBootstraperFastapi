# WebDav Fastapi
## Запуск
1. Создайте и активируйте виртуальное окружение
    ```shell
    python -m venv venv
    venv/scripts/activate
    # source venv/bin/activate для Linux
    ```
2. Установите зависимости 
    ```shell
    pip install -r requirements.txt
    ```
3. Для запуска WebDav сервера создайте файл `wsgidav.yaml` по шаблону из файла `wsgidav.yaml.template` и выполните команду:
   ```shell
   wsgidav
   ```
4. Далее, запускаем Fastapi проект:
   ```shell
   uvicorn app.main:app --reload
   ```
5. Переходим по адресу Fastapi -  по умолчанию http://127.0.0.1:8000/