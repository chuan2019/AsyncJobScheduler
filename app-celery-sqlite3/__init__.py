#!/usr/bin/python
"""
Author		: Chuan Zhang
Date		: March 2016
Description	: This toy webservice is used to demonstrate how to use Flask + redis + celery to build a webservice to 
			: implement asynchronous tasks/jobs scheduling
"""

#######################################################################################################################
##                          MODEL AND DATABASE OPERATIONS                                                            ##
#######################################################################################################################

import sqlite3, os, settings
from flask import *

basedir = os.path.abspath(os.path.dirname(__file__))

basedir_db = os.path.join(basedir, 'database')
DATABASE = os.path.join(basedir_db, 'app-sqlite3.db')

app = Flask(__name__)
app.config.from_object(__name__)
#app.secret_key = settings.get_secret_key()
app.secret_key = 'xsvb^zdxzqn!n$wbrcy9e_=mwmj7*t4b2^)p5nk1h4a0%i5(q#'

def connect_to_database():
	return sqlite3.connect(DATABASE)

def get_db():
	db = getattr(g, '_database', None)
	if db is None:
		db =g._database = connect_to_database()
	return db

# we have to make sure whenever the context is destroyed the database connection will be terminated
@app.teardown_appcontext 
def close_connection(exception):
	db = getattr(g, '_database', None)
	# as the teardown_request and teardown_appcontext functions are always executed, no matter if 
	# before_request handler was successfully executed or not, we have to make sure here that the 
	# database is open and connected before we close it 
	if db is not None:
		db.close()

@app.before_request
def before_request():
	g._database = connect_to_database()

@app.teardown_request
def teardown_request(exception):
	close_connection(exception)

def query_db(query, args=(), one=False):
	cur = get_db().execute(query, args)
	rv = cur.fetchall()
	cur.close()
	return (rv[0] if rv else None) if one else rv

#######################################################################################################################
##                                  HELPER FUNCTIONS                                                                 ##
#######################################################################################################################
import functools

def login_required(func):
	@functools.wraps(func)
	def wrapper(*args, **kwargs):
		if 'username' in session:
			return func(*args, **kwargs)
		else:
			flash('A login is required to access this page!!')
			return redirect(url_for('index'))
	return wrapper

#######################################################################################################################
##                            CONTROL AND VIEW OPERATIONS                                                            ##
#######################################################################################################################

from flask import views

class Index(views.MethodView):
	def get(self):
		return render_template('index.html', title='Home')

class Login(views.MethodView):
	def get(self):
		return render_template('login.html')

	def post(self):
		error = None
		if request.method == 'POST':
			user = query_db("SELECT * FROM account WHERE username=?", [request.form['username']], one=True)
			if user is None:
				flash('No such user')
				return redirect(url_for('index'))
			else:
				flash(repr(user) + ' : ' + request.form['passwd'])
				if user[1] == request.form['passwd']:
					session['logged_in'] = True
					session['username'] = user[0]
					session['passwd'] = user[1]
					flash('You are logged in')
					return redirect(url_for('remote'))
				else:
					flash('Error: incorrect password!!!')
					return redirect(url_for('index'))

class Logout(views.MethodView):
	@login_required
	def get(self):
		session.pop('username', None)
		session.pop('passwd', None)
		session['logged_in'] = False
		session.pop('logged_in', None)
		return redirect(url_for('index'))

class Remote(views.MethodView):
	@login_required
	def get(self):
		return render_template('remote.html')
	
	@login_required
	def post(self):
		result = eval(request.form['expression'])
		flash(result)
		#return self.get()
		return redirect(url_for('remote'))

class Register(views.MethodView):
	def get(self):
		return render_template('register.html')

	def post(self):
		db = get_db()
		cur = db.cursor()
		if cur.execute("SELECT COUNT(*) FROM account WHERE username=?", [request.form['username']]).fetchall()[0][0] > 0:
			flash("Error: {0} has been used, please choose a different one!".format(request.form['username']))
			cur.close()
			return self.get()
		else:
			cur.execute("INSERT INTO account (username, password, address) VALUES (?, ?, ?)", [request.form['username'], request.form['passwd'], 'no address'])
			db.commit()
			cur.close()
			db.close()
			return redirect(url_for('index'))

class CloseAccount(views.MethodView):
	@login_required
	def get(self):
		return render_template('close_account.html')

	@login_required
	def post(self):
		if 'cancel' in request.form:
			return redirect(url_for('remote'))
		if request.form['username'] == session['username'] and request.form['passwd'] == session['passwd']:
			db = get_db()
			cur = db.cursor()
			cur.execute("DELETE FROM account WHERE username=? AND password=?", [session['username'], session['passwd']])
			db.commit()
			cur.close()
			db.close()
			session.pop('username', None)
			session.pop('passwd', None)
			session['logged_in'] = False
			session.pop('logged_in', None)
			return redirect(url_for('logout'))
		else:
			flash("Error: incorrect username or password, if you are not the current user, please logout immediately!!")
			return redirect(url_for('remote'))
	
app.add_url_rule(
					'/',
					view_func=Index.as_view('index'), 
					methods=['GET']
)

app.add_url_rule(
				'/login/',
				view_func=Login.as_view('login'),
				methods=['GET', 'POST']
)

app.add_url_rule(
				'/logout/',
				view_func=Logout.as_view('logout'),
				methods=['GET']
)

app.add_url_rule(
				'/remote/',
				view_func=Remote.as_view('remote'),
				methods=['GET', 'POST']
)

app.add_url_rule(
				'/register/',
				view_func=Register.as_view('register'),
				methods=['GET','POST']
)

app.add_url_rule(
				'/close_account/',
				view_func=CloseAccount.as_view('close_account'),
				methods=['GET', 'POST']
)

#######################################################################################################################
##                            CELERY FOR ASYNCHRONOUS TASK SCHEDULING                                                ##
#######################################################################################################################

from celery import Celery

#app.config['CELERY_BROKER_URL'] = 'redis://172.17.58.146:6379/0'
#app.config['CELERY_RESULT_BACKEND'] = 'redis://172.17.58.146:6379/0'
app.config['CELERY_BROKER_URL'] = 'redis://localhost:6379/0'
app.config['CELERY_RESULT_BACKEND'] = 'redis://localhost:6379/0'

celery = Celery(app.name, broker=app.config['CELERY_BROKER_URL'])
celery.conf.update(app.config)

@celery.task(bind=True)
def background_task(self, expression):
	result = eval(expression)
	flash(result)
	return result

class ScheduleTask(views.MethodView):
	@login_required
	def get(self):
		return render_template('schedule_task.html')

	@login_required
	def post(self):
		#task = background_task.delay(request.form['expression'])
		flash('Executing ' + request.form['expression']+ ' in ' + request.form['delay'] + ' Seconds ')
		task = background_task.apply_async([request.form['expression']], countdown=int(request.form['delay']))
		return redirect(url_for('task'))


app.add_url_rule(
				'/task/',
				view_func=ScheduleTask.as_view('task'),
				methods=['GET','POST']
)

if __name__ == "__main__":
	app.run(debug=True, host='172.17.58.162')
