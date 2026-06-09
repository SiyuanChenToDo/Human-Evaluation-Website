"""PythonAnywhere WSGI entry point"""
import sys
import os

# Add the app directory to the path
project_home = '/home/{username}/Human-Evaluation-Website'
if project_home not in sys.path:
    sys.path.insert(0, project_home)

from app import app as application

# Set database path
import db
db.DB_PATH = os.path.join(project_home, 'eval.db')
