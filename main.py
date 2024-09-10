from flask import Flask, request, redirect, url_for, render_template, flash, session,jsonify

import sqlite3
import os
from werkzeug.utils import secure_filename
from datetime import datetime
#___________________________________
import logging
from logging import FileHandler

app = Flask(__name__)
from menu import *
from employer import *
from jobseeker import *



if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
