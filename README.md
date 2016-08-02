<b>Author</b> : Chuan Zhang <br>
<b>Date</b> : March 2016 <br>
<b>Description</b> : This toy webservice is used to demonstrate how to use Flask + redis + celery to build a webservice to implement asynchronous tasks/jobs scheduling
<br>

## Instructions for get the webservices running on server:

1. get python, flask, celery, and redis installed on the server;
2. copy the folders including webservices onto the server (you can put it anywhere you want);
3. start the flask virtual environment by running the followsing command:

	<path to the flask virtual environment>/bin/activate

4. in virtual environment, start redis server as broker on any machine (can be the same machine on which webservice will 
   be running, also can be a different machine), then goto the python source code (for app-celery-sqlite3, it is __init__.py,
   for flask-celery, it is app.py), change the following two environment variables accordingly:

	CELERY_BROKER_URL
	CELERY_RESULT_BACKEND

   if you run redis server on the same machine with webservice, you can simply set them as follows:

	app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
	app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

5. in virtual environment, start celery worker(s) by typing the following command:

	celery worker -A <your project name>.celery --loglevel=info

   should run this command with a user which is not root, but if you have to run it with root, then before running it,
   type the following command:

	export C_FORCE_ROOT = True

   also, if you don't want celery automatically assign processes for your workers, you can set it by using the -c option
   when starting celery worker(s).

6. in virtual environment, start the webservice server program:

	for app-celery-sqlite3:
	
		cd <path to the file __init__.py>
		python __init__.py

	for flask-celery:

		cd <path to the file app.py>
		python app.py

Now, the webservice should be up and running, you can simply open a web browser, and type the following link to access the
webservice:

	http://<ip address of the server on which webservice is running>: 5000/

Here the port 5000 is usually automatically assigned.
