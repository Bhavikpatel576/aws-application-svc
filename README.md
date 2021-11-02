# application-service

1. Create virtualenv with dependencies installed for service
    -  `pipenv install` or `pipenv install --dev` to install dev dependencies
        - Installs packages in virtualenv for project
2. Setup local Django environment settings
    - `cp src/core/settings/local_template.py src/core/settings/local.py`
    - Add Salesforce credentials:
      - find & copy the `NEW_SALESFORCE` credentials from [the dashboard for application-service-dev](https://dashboard.heroku.com/apps/application-service-dev/settings).
      - replace the value of `NEW_SALESFORCE` in your `local.py` file with this value
    - Add `homeward-sso` credentials:
      - find & copy the value of `HOMEWARD_SSO_AUTH_TOKEN` from [the dashboard for application-service-stage](https://dashboard.heroku.com/apps/application-service-stage/settings).
      - replace the value of `HOMEWARD_SSO_AUTH_TOKEN` in your `local.py` file with this value
3. Setup Postgres docker container
    - `docker pull postgres:11.11`
    - `docker run --name homeward-postgres -e POSTGRES_PASSWORD=docker -d -p 5432:5432 -v $HOME/docker/volumes/postgres:/var/lib/postgresql/data postgres:11.11`
        - Spins up postgres container
        - If you already have a postgres container running, you can skip the command above.
    - `docker exec -it homeward-postgres psql -U postgres -c "CREATE DATABASE \"application-service\";"`
        - Creates database 
        - Note: if you already have a postgres container running:
          - find the current postgres container name by running `docker ps`
          - change the command above to the following where `{CONTAINER_NAME}` is what you see when running `docker ps`:
            - `docker exec {CONTAINER_NAME} psql -U postgres -c "CREATE DATABASE \"application-service\";"`
    - `pipenv run python src/manage.py migrate`
        - Runs migrations
4. Start service
    - `pipenv run python src/manage.py runserver`
5. Run tests
    - To run unit and integration tests 
      - `pipenv run python src/manage.py test`
    - To reuse the test database for multiple runs, use 
      - `pipenv run python src/manage.py test --keepdb`
    - To run only unit tests
      - `src/manage.py test --testrunner="core.tests.test_runners.UnitTestRunner" --parallel`
    
<br>

#### Optional - Load fixture file into your local database for testing locally.
1. Find and replace emails in application/fixtures/app_svc_fixtures.json with your own testing emails. (Ex: rachel.peace+random_string_here)
   - Find "your-customer-email" and replace with a testing email. (Ex: rachel.peace+testcustomer)
      - Leave numbers on the Customer emails.
   - Find "your-mortgage-lender-email" and replace with a testing email (Ex: rachel.peace+mortgagelender)
   - Find "your-agent-email" and replace with a testing email (Ex: rachel.peace+testagent)
   - Find "your-isu-email" and replace with a testing email (Ex: rachel.peace+testisu)
      - Leave numbers on the Internal Support User emails
   - Find "your-homeward-owner-email" and replace with a testing email (Ex: rachel.peace+homewardowner)
2. After you migrate, run `pipenv run python src/manage.py loaddata app_svc_fixtures.json`

<br>

#### Scripts
  - `seed_salesforce`:
    - This management script will allow you to seed application-svc and salesforce with testing data through integration tests. For more information 
      on creating your own testing scenarios and how application-svc interacts with salesforce, you can refrence [this](https://www.notion.so/thehomewardway/Getting-Started-with-Salesforce-f360a11345454250b7ea264b41d317cc) document

## Using docker
1. You may need to generate a `requirements.py` file from the Pipfile. This can be done with `pipenv lock -r --dev > requirements.txt`. Be warned that the version of `psycopg2`.
2. You'll need to add the following to your application-service local settings.
```python
default_connection = dj_database_url.parse('postgresql://postgres:postgres@db:5432/application-service')
default_connection.update({'CONN_MAX_AGE': 600, })
DATABASES = {
    'default': default_connection,
}

CELERY_BACKEND = "rpc://"
CELERY_BROKER_URL = "amqp://guest:guest@host.docker.internal:5672"
CELERY_TASK_ALWAYS_EAGER = True
CELERY_TASK_DEFAULT_QUEUE = 'application-service-tasks'
CAS_SERVER_URL = '<your_local_cas_server>/cas/login'
```
3. You may want to set up the CAS docker-compose and connect it so that you have authentication.

4. Now, in the repo directory, run the following builds. The names are important as they'll be used by other dockerfiles.
```shell
# Pre-builds
docker build -t base_stage_app_svc docker_prebuilds/base_stage/
docker build -t postgres_db_app_svc docker_prebuilds/postgres_db/
# Build and start rabbitmq, which might be shared
docker run -d --hostname test-rabbit --name test-rabbit -p 5672:5672 rabbitmq:3-management

docker-compose build
docker-compose up
```
<br>

#### Troubleshooting
1. If you successfully create the application-service database, but see the following error message after running the migrate command:
   `django.db.utils.OperationalError: FATAL:  database "application-service" does not exist`
    - Go into the postgres shell: `psql postgresql://postgres:docker@localhost:5432/`
    - Run command: `CREATE DATABASE "application-service";`
    - Quit the postgres shell: `\q`
    - Now you can try the migrate command again.
