git pull;
source ../python_env/bin/activate;
pip install -r requirements.txt;
python manage.py collectstatic --noinput;
python manage.py migrate;
sudo systemctl restart gunicorn;
sudo systemctl restart nginx;

