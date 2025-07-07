# wies (prototype)
Interne tool voor overzicht wie, waar, wat, wanneer

## Installation

setup venv
```
python3.13 -m venv venv
```

activate venv
```
source venv/bin/activate
```

install requirements
```
pip install -r requirements.txt
```

inside src folder:
```
python manage.py migrate
```

## Run


inside src:
```
python manage.py runserver
```

available routes
- http://127.0.0.1:8000/projects/
- http://127.0.0.1:8000/colleagues/
- http://127.0.0.1:8000/admin/ (need to create superuser first)
