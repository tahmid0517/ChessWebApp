from flask import Flask
from flask import render_template
from flask import session
from flask import redirect
from flask import request
from flask import g

import sqlite3

import logging

import app_constants
from db_util import DBUtil
from log_wrapper import Logger

MODULE_NAME = "main"

def redirect_to_nickname_page(redirect_url: str, show_blank_message: bool, show_inapprop_message: bool, show_existing_message: bool):
    return render_template('pickNickname.html', redirectURL=redirect_url, showBlankNicknameMessage=show_blank_message, 
            showInappropNicknameMessage=show_inapprop_message, showExistingNicknameMessage=show_existing_message)

def get_db_connection():
    if 'db' not in g:
        g.db = sqlite3.connect(app_constants.DATABASE_NAME)         
        g.db.row_factory = sqlite3.Row
    return g.db

def get_logger():
    if 'log_wrapper' not in g:
        g.log_wrapper = Logger(MODULE_NAME)
    return g.log_wrapper

def update_last_request_column_for_user(db_connection, user_id: int):
    db_util = DBUtil(db_connection)
    db_util.update_timestamp_for_user(user_id)

def create_app():
    app = Flask(__name__, static_folder="static")
    app.secret_key = "uopivuzciovu78979879zvpvjlkdf;jalkfja;#42343243243245435345"

    with app.app_context(): 
        get_logger().debug("Initializing database tables")
        db_util = DBUtil(get_db_connection())
        db_util.init_nickname_table()

    @app.route('/setNickname', methods=['POST'])
    def set_nickname():
        logger = get_logger()

        if 'nickname' in session:
            logger.debug("Nickname already exists in session, so redirecting to home page")
            return redirect('/home')

        redirect_url = str(request.form['redirectURL'])
        if (not isinstance(redirect_url, str)) or (redirect_url == "None") or (not redirect_url.strip()):
            redirect_url = "/"
        nickname = str(request.form['nickname']).strip()
        logger.debug("Received setNickname request with parameters - redirect_url: '" + redirect_url + "', nickname: '" + nickname + "'")         
        # make user reenter nickname if it's blank 
        if not nickname:
            logger.debug("User needs to reenter nickname since it's blank")
            return redirect_to_nickname_page(redirect_url, True, False, False)

        # make user reenter nickname if it contains profanity
        lowercase_nickname = nickname.casefold()
        for bad_word in app_constants.BAD_WORDS:
            if bad_word in lowercase_nickname:
                logger.debug("User needs to reenter nickname since they used profanity")
                return redirect_to_nickname_page(redirect_url, False, True, False)

        # make user reenter nickname if it already exists
        db_util = DBUtil(get_db_connection())
        if db_util.does_nickname_exist(nickname):
            logger.debug("User needs to reenter nickname since it already exists")
            return redirect_to_nickname_page(redirect_url, False, False, True)
        
        user_id = db_util.add_user(nickname)
        logger.debug("Added user with id: " + str(user_id) + " and nickname: '" + nickname + "'")

        session['nickname'] = nickname
        session['user_id'] = user_id

        return redirect(redirect_url)

    @app.route('/')
    @app.route('/home')
    def get_home_page():
        logger = get_logger()
        if not 'nickname' in session:
            logger.debug("There is no nickname in the session, so redirecting to nickname page")
            return redirect_to_nickname_page("/home", False, False, False)
        update_last_request_column_for_user(get_db_connection(), session['user_id'])
        logger.debug("Returning home page")
        return render_template('home.html', nickname=session['nickname'])

    @app.teardown_appcontext
    def close_db_connection(exception):
        db_connection = g.pop('db', None)
        if db_connection is not None:
            db_connection.close() 

    return app

