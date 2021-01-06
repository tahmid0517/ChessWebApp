from flask import Flask
from flask import render_template
from flask import session
from flask import redirect
from flask import request
from flask import g
from flask import jsonify
from flask import flash

# external non-Flask imports
import sqlite3
import logging
import random

#internal imports
import app_constants
from db_util import DBUtil
from log_wrapper import Logger

MODULE_NAME = "main"

class SessionKeys:
    NICKNAME = 'nickname'
    USER_ID = 'user_id'
    ACTIVE_GAME_ID = 'active_game_id'
    IS_GAME_HOST = 'is_game_host'

class URLs:
    HOME_PAGE = '/home'
    SET_NICKNAME = '/setNickname'
    PLAY_FRIEND_PAGE = '/playVsFriend'
    CREATE_GAME_VS_FRIEND_PAGE = '/createGameVsFriend'
    SUBMIT_GAME_SETTINGS = '/submitGameSettings'
    WAIT_FOR_OPP_PAGE = '/waitForOpponent'
    JOIN_PVP_GAME = '/joinPVPGame'
    GET_GAME_STATUS = '/getGameStatus'
    CANCEL_PVP_GAME = '/cancelPVPGame'
    GO_TO_GAME = '/goToGame'
    SUBMIT_PVP_GAME_CREDENTIALS = '/submitPVPGameCredentials' 

JSON_REQUESTS = {URLs.GET_GAME_STATUS}

def get_error_json(msg: str):
    return jsonify({'error': msg})

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
        db_util.init_users_table()
        db_util.init_games_table()

    @app.route(URLs.SET_NICKNAME, methods=['POST'])
    def set_nickname():
        logger = get_logger()

        if SessionKeys.NICKNAME in session:
            logger.debug("Nickname already exists in session, so redirecting to home page")
            return redirect(URLs.HOME_PAGE)

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

        session[SessionKeys.NICKNAME] = nickname
        session[SessionKeys.USER_ID] = user_id

        return redirect(redirect_url)

    @app.before_request
    def before_request_callback():
        if 'static' in request.path:
            return
        if SessionKeys.NICKNAME not in session:
            if request.path == URLs.SET_NICKNAME:
                return
            if request.path in JSON_REQUESTS:
                get_logger().debug("There is no nickname in the session, so returning an 'error' JSON")
                return get_error_json("There is no nickname in the session currently.")
            get_logger().debug("There is no nickname in the session, so redirecting to nickname page")
            return redirect_to_nickname_page(request.url, False, False, False)
        else:
            pass
            #update_last_request_column_for_user(get_db_connection(), session[SessionKeys.USER_ID])
        if SessionKeys.ACTIVE_GAME_ID in session and request.path != URLs.GET_GAME_STATUS and request.path != URLs.CANCEL_PVP_GAME:
            db_util = DBUtil(get_db_connection())
            game_status = db_util.get_game_status(session[SessionKeys.ACTIVE_GAME_ID])
            if game_status == DBUtil.GameStatus.CANCELLED or game_status == DBUtil.GameStatus.COMPLETED:
                session.pop(SessionKeys.ACTIVE_GAME_ID, None)
                session.pop(SessionKeys.IS_GAME_HOST, None)
                return
            if game_status == DBUtil.GameStatus.WAITING_FOR_OPPONENT and request.path != URLs.WAIT_FOR_OPP_PAGE:
                return redirect(URLs.WAIT_FOR_OPP_PAGE)
            if game_status == DBUtil.GameStatus.ACTIVE and request.path != URLs.GO_TO_GAME:
                return redirect(URLs.GO_TO_GAME)

    @app.route('/')
    @app.route(URLs.HOME_PAGE)
    def get_home_page():
        get_logger().debug("Returning home page")
        return render_template('home.html', nickname=session[SessionKeys.NICKNAME])

    @app.route(URLs.PLAY_FRIEND_PAGE)
    def get_play_vs_friend():
        get_logger().debug("Returning playVsFriend.html") 
        return render_template('playVsFriend.html')
    
    @app.route(URLs.CREATE_GAME_VS_FRIEND_PAGE)
    def get_create_game_vs_friend_page():
        get_logger().debug("Returning createGame.html") 
        return render_template('createGame.html', gameVsHuman=True, showErrorMessage=False)

    @app.route(URLs.SUBMIT_GAME_SETTINGS, methods=['POST'])
    def submit_game_settings():
        game_vs_human = str(request.form['gameVsHuman']) == 'True'
        if game_vs_human:
            RANDOM = 0
            WHITE = 1
            BLACK = 2 
            host_plays_as = -1 
            try:
                host_plays_as = int(request.form['hostPlaysAs'])
                time_limit = int(request.form['timeLimit'])
            except ValueError:
                return render_template('createGame.html', gameVsHuman=True, showErrorMessage=True, showPasswordErrorMessage=False)
            if host_plays_as not in {RANDOM, WHITE, BLACK}:
                return render_template('createGame.html', gameVsHuman=True, showErrorMessage=True, showPasswordErrorMessage=False)
            if time_limit not in app_constants.SUPPORTED_TIME_LIMITS:
                return render_template('createGame.html', gameVsHuman=True, showErrorMessage=True, showPasswordErrorMessage=False)
            if host_plays_as == RANDOM:
                host_plays_as = random.randint(WHITE, BLACK)
            game_password = ''
            if 'gamePassword' in request.form:
                game_password = str(request.form['gamePassword'])
                if len(game_password) > 0 and not game_password.isalnum():
                    return render_template('createGame.html', gameVsHuman=True, showErrorMessage=False, showPasswordErrorMessage=True)
            db_util = DBUtil(get_db_connection())
            host_user_id = session[SessionKeys.USER_ID]
            host_playing_white = host_plays_as == WHITE
            external_game_id = db_util.create_pvp_game(host_user_id, host_playing_white, game_password)
            session[SessionKeys.ACTIVE_GAME_ID] = external_game_id
            session[SessionKeys.IS_GAME_HOST] = True            
            get_logger().debug("PVP game with external ID: " + external_game_id + " has been created. Returning 'Waiting for opponent' page")
            return redirect(URLs.WAIT_FOR_OPP_PAGE)
        else:
            # handle case for playing vs computer, raise exception 404 for now
            raise Exception("temporary exception, doesn't support vs. computer games for now") 

    @app.route(URLs.WAIT_FOR_OPP_PAGE)
    def get_wait_for_opp_page():
        if SessionKeys.ACTIVE_GAME_ID not in session:
            return redirect(URLs.HOME_PAGE)
        db_util = DBUtil(get_db_connection())
        game_pass = db_util.get_pvp_game_pass(session[SessionKeys.ACTIVE_GAME_ID])
        get_logger().debug("Returning waitForOpponent.html")
        linkForJoining = app_constants.BASE_URL + URLs.JOIN_PVP_GAME + '?' + 'gameID=' + session[SessionKeys.ACTIVE_GAME_ID]
        return render_template('waitForOpponent.html', link=linkForJoining, passwordReq=(game_pass!=''), password=game_pass)

    @app.route(URLs.GET_GAME_STATUS, methods=['POST'])
    def get_game_status():
        logger = get_logger()
        if SessionKeys.ACTIVE_GAME_ID not in session:
            logger.debug("getGameStatus was called when there is no active game. Returning error message") 
            return get_error_json("Something went wrong.")
        active_game_id = session[SessionKeys.ACTIVE_GAME_ID]
        db_util = DBUtil(get_db_connection())
        game_status = db_util.get_game_status(active_game_id)
        POSSIBLE_STATUSES = ["WAITING_FOR_OPPONENT", "ACTIVE", "COMPLETED", "CANCELLED"]
        if game_status < 0 or game_status > len(POSSIBLE_STATUSES):
            logger.debug("Game status in DB is " + str(game_status) + " which should not be possible. Returning error message") 
            return get_error_json("Something went wrong.")
        jsonDict = {'gameStatus': POSSIBLE_STATUSES[game_status]}
        return jsonify(jsonDict)

    @app.route(URLs.CANCEL_PVP_GAME, methods=['POST'])
    def cancel_pvp_game():
        logger = get_logger()
        if SessionKeys.ACTIVE_GAME_ID not in session:
            logger.debug("No active game to cancel")
            return jsonify({'FAILURE': "There is no active game to cancel."})     
        if not session[SessionKeys.IS_GAME_HOST]:
            logger.debug("Can't cancel when not host")
            return jsonify({'FAILURE': "Cannot cancel as non-host."})     
        db_util = DBUtil(get_db_connection())
        active_game_id = session[SessionKeys.ACTIVE_GAME_ID]
        game_status = db_util.get_game_status(active_game_id)
        if game_status != DBUtil.GameStatus.WAITING_FOR_OPPONENT:
            logger.debug("Game status is not 'Waiting for opponent', so cannot cancel it")
            return jsonify({'FAILURE': "Game is not in a state to be able to cancel it."})
        logger.debug("Cancelling PVP game")
        db_util.cancel_pvp_game(active_game_id)
        session.pop(SessionKeys.ACTIVE_GAME_ID, None)
        session.pop(SessionKeys.IS_GAME_HOST, None)
        return jsonify({'SUCCESS': "Game has been cancelled."})         

    @app.route(URLs.JOIN_PVP_GAME)
    def get_join_pvp_game_page():
        if request.args.get('gameID') is not None:
            game_id = str(request.args.get('gameID'))
            if game_id != '' and not game_id.isalnum():
                return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
            db_util = DBUtil(get_db_connection()) 
            game_status = db_util.get_game_status(game_id)
            if game_status is None or game_status != DBUtil.GameStatus.WAITING_FOR_OPPONENT:
                return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
            password = db_util.get_pvp_game_pass(game_id)
            if password is None:
                return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
            if password == '':
                db_util.set_pvp_game_active(game_id)
                session[SessionKeys.ACTIVE_GAME_ID] = game_id
                session[SessionKeys.IS_GAME_HOST] = False
                return redirect(URLs.HOME_PAGE) 
            else:
                return render_template('joinGame.html', prefilledID=game_id, showUnsuccessfulMessage=False) 
        else:
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=False) 

    @app.route(URLs.SUBMIT_PVP_GAME_CREDENTIALS, methods=['POST'])
    def submit_pvp_game_credentials():
        if SessionKeys.ACTIVE_GAME_ID in session:
            return redirect(URLs.HOME_PAGE)        
        if request.form['gameID'] is None or request.form['password'] is None:
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
        submitted_game_id = str(request.form['gameID'])
        submitted_pass = str(request.form['password'])
        if submitted_game_id == '' or not submitted_game_id.isalnum():
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
        if submitted_pass != '' and not submitted_pass.isalnum():
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
        db_util = DBUtil(get_db_connection())
        game_status = db_util.get_game_status(submitted_game_id)
        if game_status is None or game_status != DBUtil.GameStatus.WAITING_FOR_OPPONENT:
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
        actual_pass = db_util.get_pvp_game_pass(submitted_game_id)
        if actual_pass is None or actual_pass != submitted_pass:
            return render_template('joinGame.html', prefilled_id='', showUnsuccessfulMessage=True) 
        else:
            db_util.set_pvp_game_active(submitted_game_id)
            session[SessionKeys.ACTIVE_GAME_ID] = submitted_game_id
            session[SessionKeys.IS_GAME_HOST] = False
            return redirect(URLs.HOME_PAGE) 

    @app.route(URLs.GO_TO_GAME)
    def go_to_game():
        # code here is just temporary
        if SessionKeys.ACTIVE_GAME_ID not in session:
            return redirect(URLs.HOME_PAGE)
        temp_str = 'Player: ' + session[SessionKeys.NICKNAME] + ', GameID: ' + session[SessionKeys.ACTIVE_GAME_ID] + ', Is host?:' + str(session[SessionKeys.IS_GAME_HOST])
        return render_template('game.html', tempStr=temp_str) 


    @app.teardown_appcontext
    def close_db_connection(exception):
        db_connection = g.pop('db', None)
        if db_connection is not None:
            db_connection.close() 

    return app

