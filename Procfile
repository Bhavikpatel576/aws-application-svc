web: bin/qgpass python src/serve.py
beat_and_worker: bin/qgpass celery -A utils worker --beat --loglevel=info --workdir=src --without-gossip --without-mingle --without-heartbeat -Q application-service-tasks
worker: bin/qgpass celery -A utils worker --loglevel=info --workdir=src --without-gossip --without-mingle --without-heartbeat -Q application-service-tasks
release: python src/manage.py migrate
