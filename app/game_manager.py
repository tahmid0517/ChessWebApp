import time
import sqlite3
from pathlib import Path
import chess
import chess.svg

from log_wrapper import Logger
import app_constants

_MODULE_NAME= 'game_manager'
_MOVES_TABLE_NAME = 'moves_made'
_CHECK_IN_TABLE_NAME = 'check_in'

# will prob need to add more stuff like pieces captured and time left for each player
class _Moves_Table_Columns:
    TIMESTAMP = 'timestamp'
    MOVE_NUMBER = 'move_num'
    MOVE_MADE_FROM_SQUARE = 'move_made_from'
    MOVE_MADE_TO_SQUARE = 'move_made_to'
    FEN_AFTER_MOVE = 'fen'

class _Check_In_Table_Columns:
    EQUAL_TO_ONE = 'equal_to_one'
    HOST_PLAYER_LAST_CHECK_IN_TIME = 'host_player_check_in'
    GUEST_PLAYER_LAST_CHECK_IN_TIME = 'guest_player_check_in'
    DID_HOST_WIN = 'did_host_win' # -1 means no result, 0 means no, 1 means yes
    GAME_STATUS = 'game_status'

_CHECK_IN_TABLE_CONDITION = " WHERE " + _Check_In_Table_Columns.EQUAL_TO_ONE + '=1'

class LiveGameStatus:
    ACTIVE = 0
    AUTO_RESIGNED = 1
    RESIGNED = 2
    CHECKMATED = 3
    DRAW_INSUFFICIENT = 4
    DRAW_STALEMENT = 5

class GameManager:
    SIZE_OF_SVG = 380

    def __init__(self, external_game_id: str, pvp_game: bool):
        self.logger = Logger(_MODULE_NAME)

        # figure out name of DB file and connect to it
        PVP_GAME_PREFIX = 'PVP_'  
        COMPUTER_GAME_PREFIX = 'CPU_'
        db_file_name = ''
        if pvp_game:
            db_file_name = PVP_GAME_PREFIX + external_game_id + '.db'
        else:
            db_file_name = COMPUTER_GAME_PREFIX + external_game_id + '.db'
        file_dir = app_constants.GAMES_DATA_DIR + '/' + db_file_name
        self.creating_db_for_first_time = not Path(file_dir).is_file() 
        self.conn = sqlite3.connect(file_dir)

        if self.creating_db_for_first_time:
            # create moves table 
            moves_table_columns = list()
            moves_table_columns.append(_Moves_Table_Columns.MOVE_NUMBER + " INTEGER PRIMARY KEY AUTOINCREMENT")
            moves_table_columns.append(_Moves_Table_Columns.TIMESTAMP + " INTEGER NOT NULL")
            moves_table_columns.append(_Moves_Table_Columns.MOVE_MADE_FROM_SQUARE + " TEXT NOT NULL")
            moves_table_columns.append(_Moves_Table_Columns.MOVE_MADE_TO_SQUARE + " TEXT NOT NULL")
            moves_table_columns.append(_Moves_Table_Columns.FEN_AFTER_MOVE + " TEXT NOT NULL")
            moves_table_columns_appended = ' (' + ', '.join(moves_table_columns) + ')'
            create_script = "CREATE TABLE IF NOT EXISTS " + _MOVES_TABLE_NAME + moves_table_columns_appended + ';'
            self.logger.debug("Creating " + _MOVES_TABLE_NAME + " with script: " + create_script)
            self.conn.execute(create_script)
            initial_row_vals = list()
            initial_row_vals.append('0') # MOVE_NUMBER
            initial_row_vals.append(str(int(time.time()))) # TIMESTAMP
            initial_row_vals.append("''") # MOVE_MADE_FROM_SQUARE
            initial_row_vals.append("''") # MOVE_MADE_TO_SQUARE
            initial_row_vals.append("'" + chess.STARTING_FEN + "'") # FEN_AFTER_MOVE
            initial_row_appended = ' VALUES (' + ', '.join(initial_row_vals) + ')'
            add_first_row_script = "INSERT INTO " + _MOVES_TABLE_NAME + initial_row_appended + ';'
            self.logger.debug("Adding first row to table with script: " + add_first_row_script)
            self.conn.execute(add_first_row_script)
            self.conn.commit()
    
        self.board = None

    def get_start_of_game():
        # uses timestamp from first row of 'moves' table
        cursor = self.conn.execute("SELECT MIN(" + _Moves_Table_Columns.TIMESTAMP + ") from " + _MOVES_TABLE_NAME + ';')
        data = cursor.fetchone()
        return data[0]   

    def get_number_of_moves_made(self):
        cursor = self.conn.execute("SELECT COUNT(*) FROM " + _MOVES_TABLE_NAME)
        data = cursor.fetchone()
        moves_made = data[0] - 1
        return data[0] - 1

    def _get_data(self, move_num: int, column: str):
        script = "SELECT " + column + " FROM " + _MOVES_TABLE_NAME + " WHERE " + _Moves_Table_Columns.MOVE_NUMBER + '=' + str(move_num)
        cursor = self.conn.execute(script)
        data = cursor.fetchone()
        return data[0] 

    def _get_current_fen(self):
        number_of_moves_made = self.get_number_of_moves_made()
        return self._get_data(number_of_moves_made, _Moves_Table_Columns.FEN_AFTER_MOVE)

    def get_board(self):
        if self.board == None:
            current_fen = self._get_current_fen()
            self.board = chess.Board(current_fen)
        return self.board

    def get_current_board_svg(self, is_white: bool):
        board = self.get_board() 
        if is_white:
            return str(chess.svg.board(board, orientation=chess.WHITE, size=GameManager.SIZE_OF_SVG))
        else:
            return str(chess.svg.board(board, orientation=chess.BLACK, size=GameManager.SIZE_OF_SVG))

    def get_piece_positions(self, is_white: bool):
        board = self.get_board()
        piece_map = board.piece_map()
        pos_list = list()
        colour_to_look_for = chess.WHITE if is_white else chess.BLACK
        for pos, piece in piece_map.items():
            if piece.color == colour_to_look_for:
                pos_list.append(chess.square_name(pos))
        return pos_list

    def get_attack_from_pos_svg(self, is_white: bool, attack_from_square: str):
        positions_to_attack_from = self.get_piece_positions(is_white)
        if attack_from_square not in positions_to_attack_from:
            raise Exception("Square: " + attack_from_square + " is not one of possible squares to attack from.")
        board = self.get_board()
        squares_to_move_to = set()
        squares_to_move_to_names = list()
        for move in board.legal_moves:
            if chess.square_name(move.from_square) == attack_from_square:
                squares_to_move_to.add(move.to_square)  
                squares_to_move_to_names.append(chess.square_name(move.to_square))
        colour = chess.WHITE if is_white else chess.BLACK
        board_svg = str(chess.svg.board(board, orientation=colour, size=GameManager.SIZE_OF_SVG, squares=squares_to_move_to)) 
        return (board_svg, positions_to_attack_from, squares_to_move_to_names)

    # will raise exception somewhere if something isn't valid about the move
    def make_move(self, is_white: bool, from_square: str, to_square: str, promotion=None):
        piece_positions = self.get_piece_positions(is_white)
        if from_square not in piece_positions:
            raise Exception("Attempted to make move from a square that doesn't have one of the player's pieces.")
        square_1 = chess.parse_square(from_square)
        square_2 = chess.parse_square(to_square)
        board = self.get_board()
        move = board.find_move(square_1, square_2)
        board.push(move)
        # insert into DB table
        new_fen = board.fen()
        vals_to_insert = list()
        vals_to_insert.append('NULL')
        vals_to_insert.append(str(int(time.time())))
        vals_to_insert.append("'" + from_square + "'")
        vals_to_insert.append("'" + to_square + "'") 
        vals_to_insert.append("'" + new_fen + "'")
        vals_to_insert_appended = " VALUES ( " + ', '.join(vals_to_insert) + ')'
        script = "INSERT INTO " + _MOVES_TABLE_NAME + vals_to_insert_appended + ';'
        self.conn.execute(script)
        self.conn.commit()

class PVPGameManager(GameManager):
    def __init__(self, external_game_id: str):
        super().__init__(external_game_id, True)
        
        if self.creating_db_for_first_time:
            # create 'check-in' table
            # this table should only have 1 row the whole time
            check_in_table_columns = list()
            check_in_table_columns.append(_Check_In_Table_Columns.EQUAL_TO_ONE + " INTEGER NOT NULL")
            check_in_table_columns.append(_Check_In_Table_Columns.HOST_PLAYER_LAST_CHECK_IN_TIME + " INTEGER NOT NULL")
            check_in_table_columns.append(_Check_In_Table_Columns.GUEST_PLAYER_LAST_CHECK_IN_TIME + " INTEGER NOT NULL")
            check_in_table_columns.append(_Check_In_Table_Columns.DID_HOST_WIN + " INTEGER NOT NULL")
            check_in_table_columns.append(_Check_In_Table_Columns.GAME_STATUS + " INTEGER NOT NULL")
            check_in_table_columns_appended = '(' + ', '.join(check_in_table_columns) + ')'
            create_script = "CREATE TABLE IF NOT EXISTS " + _CHECK_IN_TABLE_NAME + check_in_table_columns_appended + ';'
            self.conn.execute(create_script)
            row_vals = list()
            row_vals.append('1')
            current_time = str(int(time.time()))
            row_vals.append(current_time)
            row_vals.append(current_time)
            row_vals.append('-1')
            row_vals.append(str(LiveGameStatus.ACTIVE))
            row_vals_appended = ' VALUES (' + ', '.join(row_vals) + ')'
            add_row_script = "INSERT INTO " + _CHECK_IN_TABLE_NAME + row_vals_appended + ';'
            self.conn.execute(add_row_script)
            self.conn.commit()

    def receive_check_in(self, from_host: bool):
        column_to_update = _Check_In_Table_Columns.GUEST_PLAYER_LAST_CHECK_IN_TIME
        if from_host:
            column_to_update = _Check_In_Table_Columns.HOST_PLAYER_LAST_CHECK_IN_TIME
        set_statement = " SET " + column_to_update + '=' + str(int(time.time()))
        script = "UPDATE " + _CHECK_IN_TABLE_NAME + set_statement + _CHECK_IN_TABLE_CONDITION + ';'
        self.conn.execute(script)
        self.conn.commit()

    def _get_data_from_col(self, column_name: str):
        script = 'SELECT ' + column_name + " from " + _CHECK_IN_TABLE_NAME + _CHECK_IN_TABLE_CONDITION + ';'
        self.logger.debug("Getting data using script: " + script)        
        cursor = self.conn.execute(script)
        data = cursor.fetchone()
        return data[0]

    def get_time_since_last_check_in_from_opponent(self, from_host: bool):
        check_in_timestamp = 0
        if from_host:
            check_in_timestamp = self._get_data_from_col(_Check_In_Table_Columns.GUEST_PLAYER_LAST_CHECK_IN_TIME)
        else:
            check_in_timestamp = self._get_data_from_col(_Check_In_Table_Columns.HOST_PLAYER_LAST_CHECK_IN_TIME)
        current_time = int(time.time())
        return current_time - check_in_timestamp
    
    def get_game_status(self):
        return self._get_data_from_col(_Check_In_Table_Columns.GAME_STATUS) 

    def did_player_win(self, is_host: bool):
        result = self._get_data_from_col(_Check_In_Table_Columns.DID_HOST_WIN) 
        if result == -1:
            return False
        if is_host and result == 0:
            return False
        elif is_host and result == 1:
            return True
        elif not is_host and result == 0:
            return True
        elif not is_host and result == 1:
            return False 
        else:
            raise Exception("PVPGameManager.did_player_win(): Something went wrong.")

    def declare_winner(self, did_host_win: bool, from_auto_resign=False, from_resign=False, from_checkmate=False):
        new_game_status = ''
        if from_auto_resign:
            new_game_status = str(LiveGameStatus.AUTO_RESIGNED)
        elif from_resign:
            new_game_status = str(LiveGameStatus.RESIGNED)
        elif from_checkmate:
            new_game_status = str(LiveGameStatus.CHECKMATED)
        else:
            raise Exception("PVPGameManager.declare_winner(): Can't declare winner without how the game was won.") 
        vals_to_update = list()
        vals_to_update.append(_Check_In_Table_Columns.DID_HOST_WIN + '=' + ('1' if did_host_win else '0'))
        vals_to_update.append(_Check_In_Table_Columns.GAME_STATUS + '=' + new_game_status)
        set_statement = " SET " + ', '.join(vals_to_update)
        script = "UPDATE " + _CHECK_IN_TABLE_NAME + set_statement + _CHECK_IN_TABLE_CONDITION + ';'
        self.logger.debug("declare_winner() - Declaring winner by calling script: " + script)
        self.conn.execute(script)
        self.conn.commit() 

    def declare_draw(self, from_stalemate=False, from_insufficient_material=False):
        new_game_status = ''
        if from_stalemate:
            new_game_status = str(LiveGameStatus.DRAW_STALEMATE)
        elif from_insufficient_material:
            new_game_status = str(LiveGameStatus.DRAW_INSUFFICIENT)
        else:
            raise Exception("PVPGameManager.declare_draw(): Can't  declare draw without how the game let to a draw.")
        script = "UPDATE " + CHECK_IN_TABLE_NAME + " SET " + _Check_In_Table_Columns.GAME_STATUS + "=" + new_game_status + _CHECK_IN_TABLE_CONDITION + ';'
        self.logger.debug("declare_draw() - Declaring draw by calling script: " + script)
        self.conn.execute(script)
        self.conn.commit()

