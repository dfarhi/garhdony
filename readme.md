Getting Started
---

# Get the code
* Clone the Mercurial repository forkbomb-3.0-master to somewhere
# Set up the python environment
* Install python (David has 3.10.11 as of 7/27/23)
* Install virtualenv: pip install virtualenv
* cd to forkbomb
* Create virtual env: python -m venv pythonenv
* Enter the virtualenv: source start.sh
  ** Windows: pythonenv\Scripts\activate.bat
* Install the relevant files: pip install -r requirements.txt
  ** If something about 2to3 fails, may require: pip install "setuptools<58.0.0"
# Set up the config file
* copy main/config_template.py to main/config.py and edit it appropriately. Consider replacing path with ""
* make sure the log directory is right. Also make sure it exists: mkdir logs
# Obtain a copy of the database
* Probably the easiest way is to copy the one from the production server:
mkdir data;
scp user@garhdony.com:/home/django/forkbomb-3.0-master/data/garhdony.db data/garhdony.db
# Run the server: python manage.py runserver
