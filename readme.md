Getting Started
---

# Get the code
## Install Mercurial
## Clone the Mercurial repository forkbomb-3.0-master to somewhere
# Set up the python environment
## Install python
## Install virtualenv: pip install virtualenv
## cd to the folder you cloned the repo to (rest of the commands assume you're there).
## Create a new virtualenv: virtualenv pythonenv
## Enter the virtualenv: source start.sh
## Install the relevant files: pip install -r requirements.txt
# Set up the config file
## copy main/config_template.py to main/config.py and edit it appropriately. Consider replacing path with ""
## make sure the log directory is right. Also make sure it exists: mkdir logs
# Obtain a copy of the database
## Probably the easiest way is to copy the one from the production server:
mkdir data;
scp user@garhdony.com:/home/django/forkbomb-3.0-master/data/garhdony.db data/garhdony.db
# Run the server: python manage.py runserver