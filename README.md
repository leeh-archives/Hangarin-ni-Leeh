# Hangarin: Task & To-Do Manager

Hangarin is a small Django app for keeping track of what you need to do. You can
sort tasks by priority and category, jot notes on them, and break big goals into
smaller steps. It can also be installed on your phone like an app (PWA).

## What's in it

- Sign up, log in, and a profile page with a picture
- Dashboard with counts for pending, in progress, completed and overdue tasks
- Search, filter (status, category, priority) and sort your tasks
- One-click "Done" on the list, or switch status from the task page
- Steps (subtasks) with a progress bar, plus notes on every task, all editable
- Your own categories and priorities: add, rename and delete them from the sidebar
- Sign in with Google or GitHub (or a normal username and password)
- Installable as an app on phone or desktop, with an offline page
- Django admin set up for every model (list columns, filters and search)
- `seed_basics` and `generate_data` commands to fill the database

Models: `Priority`, `Category`, `Task`, `Note`, `SubTask` (all inherit
`BaseModel` with `created_at` and `updated_at`), plus a `Profile` for avatars.

## Running it on your computer

```bash
# 1. virtual environment
python -m venv hangarinenv
hangarinenv\Scripts\activate          # Windows
# source hangarinenv/bin/activate     # Mac / Linux

# 2. install packages
pip install -r requirements.txt

# 3. create the database
python manage.py migrate

# 4. add the starter priorities and categories
python manage.py seed_basics

# 5. make an admin account
python manage.py createsuperuser

# 6. (optional) fill it with fake tasks, notes and subtasks
python manage.py generate_data --count 10

# 7. start the server
python manage.py runserver
```

Then open http://127.0.0.1:8000/ for the app, or http://127.0.0.1:8000/admin/
for the admin site.

`generate_data` gives the tasks to the first account by default. Use
`--user yourname` to pick someone else.

Priorities are Critical, High, Medium, Low and Optional. Categories are Work,
School, Personal, Finance and Projects. These are shared defaults that everybody
sees and nobody can change. Each person can add their own on the **Categories**
and **Priorities** pages and rename or delete them later. A category or priority
that's still used by a task can't be deleted (so tasks never disappear by
accident), so move those tasks first.

### Sign in with Google and GitHub

The buttons only appear once the keys are filled in, so the app works fine
without them. Copy `.env.example` to `.env` (same folder as `manage.py`) and
fill in the values.

**Google**
1. Go to the [Google Cloud credentials page](https://console.cloud.google.com/apis/credentials),
   create a project, and set up the OAuth consent screen.
2. Create credentials, choose *OAuth client ID*, type *Web application*.
3. Add these under *Authorized redirect URIs*:
   - `http://127.0.0.1:8000/accounts/google/login/callback/`
   - `https://<you>.pythonanywhere.com/accounts/google/login/callback/`
4. Copy the client ID and secret into `GOOGLE_CLIENT_ID` and `GOOGLE_CLIENT_SECRET`.

**GitHub**
1. Go to [Developer settings](https://github.com/settings/developers), *OAuth Apps*, *New OAuth App*.
2. Homepage URL: `http://127.0.0.1:8000/`
3. Authorization callback URL: `http://127.0.0.1:8000/accounts/github/login/callback/`
4. Copy the client ID, generate a client secret, and put both in `.env`.

GitHub only allows one callback URL per app, so make a second OAuth app for the
PythonAnywhere site (callback
`https://<you>.pythonanywhere.com/accounts/github/login/callback/`) and use its
keys in the `.env` file on the server.

First-time Google or GitHub users get an account created automatically.

### Installing it as an app (PWA)

django-pwa is already set up (manifest, icons, service worker). Open the site in
Chrome or Edge and use the "Install app" button in the sidebar, or the browser's
own install option. In DevTools, *Application → Manifest* shows the name and
icons. If the connection drops, the app shows a short offline page instead of an
error. Task pages are never cached, so you won't see stale data. Note that
browsers only offer installation over `https://` (or `localhost`), which
PythonAnywhere gives you.

### Tests

```bash
python manage.py test
```

## Version control

```bash
git add .
git commit -m "Describe what you changed"
git push
```

`db.sqlite3`, `media/` and your virtual environment are in `.gitignore` on
purpose, so they stay out of the repo.

## Deploying to PythonAnywhere

1. **Get the code.** Open a Bash console and clone your repo:
   `git clone https://github.com/<you>/<repo>.git hangarin`
2. **Make a virtualenv and install:**
   ```bash
   mkvirtualenv hangarinenv --python=python3.12
   cd ~/hangarin
   pip install -r requirements.txt
   ```
   (Use whichever Python version PythonAnywhere offers that Django 6.1 supports.)
3. **Create the web app.** On the *Web* tab choose *Add a new web app*, pick
   *Manual configuration*, and select the same Python version. Under
   *Virtualenv* enter `/home/<you>/.virtualenvs/hangarinenv`.
4. **Edit the WSGI file** (link on the Web tab). Replace its contents with:
   ```python
   import os
   import sys

   path = "/home/<you>/hangarin"
   if path not in sys.path:
       sys.path.append(path)

   os.environ["DJANGO_SETTINGS_MODULE"] = "hangarin.settings"
   os.environ["DJANGO_SECRET_KEY"] = "put-a-long-random-string-here"
   os.environ["DJANGO_DEBUG"] = "0"

   from django.core.wsgi import get_wsgi_application
   application = get_wsgi_application()
   ```
5. **Optional: social login keys.** Create a `.env` file in `~/hangarin`
   (copy `.env.example`) with your production Google and GitHub keys. It's read
   automatically, and it isn't in git.
6. **Set up the database and static files** in the Bash console:
   ```bash
   cd ~/hangarin
   python manage.py migrate
   python manage.py seed_basics
   python manage.py createsuperuser
   python manage.py collectstatic
   ```
   Don't forget to set `DJANGO_SECRET_KEY` and `DJANGO_DEBUG` there too if you
   want to run commands with the same settings (or just leave them, the
   defaults work for these steps).
7. **Static files mapping** (Web tab, *Static files* section):

   | URL        | Directory                       |
   |------------|---------------------------------|
   | `/static/` | `/home/<you>/hangarin/staticfiles` |
   | `/media/`  | `/home/<you>/hangarin/media`       |

8. Press the green **Reload** button. Your site is at
   `https://<you>.pythonanywhere.com`.

`ALLOWED_HOSTS` and the CSRF origin already allow `*.pythonanywhere.com`. If you
use another domain, set `DJANGO_ALLOWED_HOSTS` and `DJANGO_CSRF_ORIGINS`
(comma separated) in the WSGI file.

## Settings worth knowing about

| Setting | Where | What it does |
|---|---|---|
| `DJANGO_SECRET_KEY` | environment | secret key (a dev key is used if missing) |
| `DJANGO_DEBUG` | environment | `1` for local work, `0` on the server |
| `DJANGO_TIME_ZONE` | environment | defaults to `Asia/Manila`, change it to your own |
| `GOOGLE_CLIENT_ID` / `GOOGLE_CLIENT_SECRET` | `.env` | turns on the Google button |
| `GITHUB_CLIENT_ID` / `GITHUB_CLIENT_SECRET` | `.env` | turns on the GitHub button |

Environment variables set in the WSGI file work too. If both exist, the real
environment wins over `.env`.

## Project layout

```
hangarin/            project settings and root urls
taskmanager/
    models.py        Priority, Category, Task, Note, SubTask, Profile
    forms.py         task, note, subtask, category, priority and sign-up forms
    views.py         dashboard, tasks, notes, steps, categories, priorities, profile
    context_processors.py   tells templates which social buttons to show
    admin.py         admin configuration
    management/      seed_basics and generate_data commands
    templates/       base layout and pages
    static/          stylesheet, icons, service worker
```
