M
My Workspace


My project

Production

delta-telegram-bot

Your free instance will spin down with inactivity, which can delay requests by 50 seconds or more.
Upgrade now
Newer logs may be unavailable because a recent deploy failed. View recent events.

Application logs
Search
Search logs

Last hour



  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/opt/render/project/src/app.py", line 7, in <module>
    from telegram_bot import (
  File "/opt/render/project/src/telegram_bot.py", line 3, in <module>
    from telegram import InlineKeyboardButton, InlineKeyboardMarkup
ModuleNotFoundError: No module named 'telegram'
==> Exited with status 1
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> Running 'gunicorn app:app --workers 1 --threads 2 --timeout 120'
127.0.0.1 - - [31/Aug/2026:22:54:11 +0000] "HEAD / HTTP/1.1" 200 0 "https://delta-telegram-bot-agg7.onrender.com" "Mozilla/5.0+(compatible; UptimeRobot/2.0; http://www.uptimerobot.com/)"
==> Deploying...
==> Setting WEB_CONCURRENCY=1 by default, based on available CPUs in the instance
==> Running 'gunicorn app:app --workers 1 --threads 2 --timeout 120'
Traceback (most recent call last):
  File "/opt/render/project/src/.venv/bin/gunicorn", line 8, in <module>
    sys.exit(run())
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 66, in run
    WSGIApplication("%(prog)s [OPTIONS] [APP_MODULE]", prog=prog).run()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 235, in run
    super().run()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 71, in run
    Arbiter(self).run()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/arbiter.py", line 63, in __init__
    self.setup(app)
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/arbiter.py", line 164, in setup
    self.app.wsgi()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/base.py", line 66, in wsgi
    self.callable = self.load()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 57, in load
    return self.load_wsgiapp()
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/app/wsgiapp.py", line 47, in load_wsgiapp
    return util.import_app(self.app_uri)
  File "/opt/render/project/src/.venv/lib/python3.10/site-packages/gunicorn/util.py", line 420, in import_app
    mod = importlib.import_module(module)
  File "/opt/render/project/python/Python-3.10.11/lib/python3.10/importlib/__init__.py", line 126, in import_module
    return _bootstrap._gcd_import(name[level:], package, level)
  File "<frozen importlib._bootstrap>", line 1050, in _gcd_import
  File "<frozen importlib._bootstrap>", line 1027, in _find_and_load
  File "<frozen importlib._bootstrap>", line 1006, in _find_and_load_unlocked
  File "<frozen importlib._bootstrap>", line 688, in _load_unlocked
  File "<frozen importlib._bootstrap_external>", line 883, in exec_module
  File "<frozen importlib._bootstrap>", line 241, in _call_with_frames_removed
  File "/opt/render/project/src/app.py", line 7, in <module>
    from telegram_bot import (
  File "/opt/render/project/src/telegram_bot.py", line 7, in <module>
    from delta_api import test_delta, get_delta_balances, place_order
ImportError: cannot import name 'place_order' from 'delta_api' (/opt/render/project/src/delta_api.py)
==> Exited with status 1
==> Common ways to troubleshoot your deploy: https://render.com/docs/troubleshooting-deploys
==> Running 'gunicorn app:app --workers 1 --threads 2 --timeout 120'
0 services selected:

Move

