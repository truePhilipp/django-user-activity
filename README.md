[![PyPI Latest Release](https://img.shields.io/pypi/v/django-user-activity.svg)](https://pypi.org/project/django-user-activity/) [![PyPI Downloads](https://static.pepy.tech/badge/django-user-activity)](https://pepy.tech/projects/django-user-activity) [![License - MIT](https://img.shields.io/pypi/l/django-user-activity.svg)](https://github.com/rkpust/django-user-activity/blob/master/LICENSE) [![Open Source](https://badges.frapsoft.com/os/v1/open-source.svg?v=103)](https://opensource.org/)

# django-user-activity

A reusable Django app for tracking user activity on web application. This app logs user actions like url, referer, method, ip, user_agent and timestamp. It’s designed to be reusable, easy to integrate, and can be customized to fit your needs.

## Features

- Tracks user activity (e.g., URL visited, HTTP method, referer, ip, user_agent and timestamp).
- Logs activity for authenticated users.
- Easily integrates into any Django project.
- Admin interface for easy viewing and management of activity data.
- Reusable and customizable.

## Requirements

- Python 3.x
- Django 4.0 or later (recommended)
- A PostgreSQL, MySQL, SQLite or any relational database for data storage

## Installation

You can install the `django-user-activity` app in your Django project using one of the following methods.

### Option 1: Install via PyPi

1. Install the app via `pip`:
   
   ```bash
   pip install django-user-activity
   ```

  ### Option 2: Install via Github
1. Install the app via `git`:
   
   ```bash
    pip install git+https://github.com/rkpust/django-user-activity
   ```
### Option 3: Install from Local Directory
- Clone the repository or download the package.
- Navigate to the project directory and install the app locally.
    
   ```bash
    pip install -e /path/to/django-user-activity
    pip install django-user-activity-0.0.1.tar.gz
   ```

## Configuration
Add `activity` to your INSTALLED_APPS in your settings.py file:

 ```python
INSTALLED_APPS = [
    ...
    'activity',
    ...
]
```

Add `ActivityMiddleware` to your MIDDLEWARE in your settings.py file:

```python
MIDDLEWARE = [
    ...
    'django.middleware.clickjacking.XFrameOptionsMiddleware',
    'activity.middleware.ActivityMiddleware',
    ...
]
```

Run migrations to set up the necessary database tables:
```python
    python manage.py makemigrations
    python manage.py migrate
```
Or, you can run these commands for further clarification.
```python
    python manage.py makemigrations activity
    python manage.py migrate activity 0001
```

## Activity Model
The `Activity` model contains the following fields:

  `user`: The user who performed the action. <br>

  `url`: The URL visited by the user. <br>

  `referer`: The referer tells you which page the user is coming from. If its value is `None`, it means the user hits the url directly in the browser. <br>

  `method`: The HTTP method (e.g., GET, POST). <br>

  `ip`: The ip of user's device. <br>

  `user_agent`: The user_agent tells you the information of users browser, os etc information. <br>

  `timestamp`: The timestamp when the action occurred.

## Admin Interface
You can view, filter, and search user activity data in the Django Admin Interface by visiting `/admin` path. Here, you will see `Activities` option in the left side. You will
- see those field as list. <br> `user`, `url`, `referer`, `method`, `ip`, `user_agent`, `timestamp` <br>
- filter those field. <br> `method`, `timestamp`
- search those field by value. <br> `username`, `url`, `referer`, `method`, `ip`

## License
This project is licensed under the MIT License - see the LICENSE file for details.

## How to Contribute
*Contributions are welcome!* If you'd like to improve, fix bugs or add new features to the reusable `django-user-activity` app, feel free to create an issue or submit a pull request on GitHub. Ensure the code adheres to the project’s style.
- Fork the repository.
- Create a new branch for your feature or bugfix.
- Write your code and tests.
- Run the tests to ensure everything is working. (`python manage.py test activity`)
- Submit a pull request describing your changes.
