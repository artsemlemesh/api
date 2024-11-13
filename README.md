### BUNDLEUP API

#### Dependencies

- PostgreSQL 10.4
- Python 3.6
- Django 2
- Django REST Framework
- Celery (Scheduled and Long running background Tasks)
- Amazon Simple Email Service (AWS SES)
- Amazon S3 Storage (Media files)
- Twilio (Phone number verification)
- Stripe (Invoice and payment transfer)
- Plaid (Bank verification)

#### Running it

1. Install [Docker](https://docs.docker.com/compose/install/),

2. Run `docker compose up` from the project root directory via Terminal/CMD

3. Go to [http://localhost:8000](http://localhost:8000) in your browser. (Did you wait for a while?)

#### Cleaning Docker

- stop all processes

```
   docker stop $(docker ps -aq)
```

- remove all containers

```
   docker rm $(docker ps -aq)
```

- remove all images

```
   docker rmi $(docker images -aq)
```

and then run `docker compose up`

#### Admin User

Admin user is added while deploying.<br/>

```
email: admin@bynde.com <br/>
password: admin123
```

#### Development Guidelines

Before starting on a new task, pull latest code from `staging` branch and then create a new branch for you task. <br/>
No hard rules for branch naming but it should be meaningful enough to know about the task

e.g `git checkout -b fix_migration_issue_for_talent_module`

Each time you make changes in `models.py`, run these commands from separate terminal while your app should be running in other terminal

```
docker compose exec web python ./src/manage.py makemigrations
```

Make sure you get new migrations files in relevant module migrations folder and then run

```
docker compose exec web python ./src/manage.py migrate
```

Did you run tests?

```
docker compose exec web python ./src/manage.py test
docker compose exec web python ./src/manage.py test ./src/app/tests/
docker compose exec web python ./src/manage.py test app.tests.test_e2e

Run faster with keepdb and parallel 
docker compose exec web python ./src/manage.py test ./src/app/tests --keepdb --parallel
```

After you test your changes locally, commit and push your newly created branch

e.g `git push origin fix_migration_issue_for_talent_module`

Create a pull request for your changes on remote repository. Someone will review your changes and merge into `staging` branch

#### Database Access

PostgreSQL could be access by using below credentials

```
HOST: localhost
DB NAME: bynde
USER: bynde
PASSWORD: 123
PORT: 5433
```

If you want to login into database docker, try this

```
docker compose exec db /bin/bash
```

CHEERS!


When you need to test webhooks
```
stripe listen --forward-to localhost:8000/webhooks/stripe
```


### Redis
```
docker compose run redis redis-cli -h redis
info keyspace
select 1
keys *

docker compose exec web python ./src/manage.py invalidate all
```

### Fixtures
```
docker compose exec web python ./src/manage.py dumpdata app.productbrand  --indent=4 > src/app/fixtures/brands.json
docker compose exec web python ./src/manage.py dumpdata app.productsize  --indent=4 > src/app/fixtures/sizes.json
docker compose exec web python ./src/manage.py dumpdata app.productcategory  --indent=4 > src/app/fixtures/categories.json

docker compose exec web python ./src/manage.py loaddata fixtures/categories.json --app app.productcategory
```

### Logging
```
import logging

from django.conf import settings

fmt = getattr(settings, 'LOG_FORMAT', None)
lvl = getattr(settings, 'LOG_LEVEL', logging.DEBUG)

logging.basicConfig(format=fmt, level=lvl)
logging.debug("Logging started on %s for %s" % (logging.root.name, logging.getLevelName(lvl)))
logging.debug("Oh hai!")
```


### Debugging containers in vscode
.vscode/launch.json
{
    "version": "0.2.0",
    "configurations": [
        {
            "name": "Python: Remote Attach",
            "type": "python",
            "request": "attach",
            "connect": {
                "host": "0.0.0.0",
                "port": 5678
            },
            "pathMappings": [
                {
                    "localRoot": "${workspaceFolder}",
                    "remoteRoot": "/app"
                }
            ]
        }
    ]
}

.vscode/tasks.json
{
	"version": "2.0.0",
	"tasks": [
		{
			"type": "docker-build",
			"label": "docker-build",
			"platform": "python",
			"dockerBuild": {
				"tag": "api:latest",
				"dockerfile": "${workspaceFolder}/Dockerfile",
				"context": "${workspaceFolder}",
				"pull": true
			}
		},
		{
			"type": "docker-run",
			"label": "docker-run: debug",
			"dependsOn": [
				"docker-build"
			],
			"python": {
				"args": [
					"runserver",
					"0.0.0.0:8000",
				],
				"file": "src/manage.py"
			}
		}
	]
}


