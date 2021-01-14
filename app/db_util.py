import time

from log_wrapper import Logger

MODULE_NAME = 'db_util'
USERS_TABLE_NAME = 'users'
GAMES_TABLE_NAME = 'games'

class _GamesTableColumns:
    INTERNAL_GAME_ID = 'internal_game_id'
    EXTERNAL_GAME_ID = 'external_game_id'
    IS_PLAYER_VS_PLAYER = 'is_pvp'
    HOST_USER_ID = 'host_user_id'
    GUEST_USER_ID = 'guest_user_id'
    IS_HOST_PLAYING_WHITE = 'is_host_white'
    GAME_STATUS = 'game_status'
    GAME_END_METHOD = 'game_result'
    DID_HOST_WIN = 'did_host_win'
    DID_GAME_DRAW = 'did_game_draw'
    PASSWORD = 'password'
    MOVES_PLAYED = 'moves_played'

class GameStatus:
    WAITING_FOR_OPPONENT = 0
    ACTIVE = 1
    COMPLETED = 2
    CANCELLED = 3

class GameEndMethod:
    AUTO_RESIGN = 0
    RESIGN = 1
    CHECKMATE = 2
    DRAW_INSUFFICIENT = 3
    DRAW_STALEMATE = 4

class DBUtil:
    def __init__(self, connection):
        self.conn = connection
        self.logger = Logger(MODULE_NAME)

    def execute_script(self, script: str):
        self.logger.debug("Executing SQL script on DB: " + script)
        return self.conn.execute(script) 

    def commit_changes(self):
        self.logger.debug("Committing changes to DB")
        self.conn.commit()

    def init_users_table(self):
        self.logger.debug("Creating " + USERS_TABLE_NAME + " table if it doesn't exist")
        script = "CREATE TABLE IF NOT EXISTS " + USERS_TABLE_NAME + " (id INTEGER PRIMARY KEY AUTOINCREMENT, nickname TEXT UNIQUE NOT NULL, last_request INTEGER);"
        self.execute_script(script)
        self.commit_changes()

    def init_games_table(self):
        self.logger.debug("Creating " + GAMES_TABLE_NAME + " table if it doesn't exist")
        table_columns = list()
        table_columns.append(_GamesTableColumns.INTERNAL_GAME_ID + " INTEGER PRIMARY KEY AUTOINCREMENT")
        table_columns.append(_GamesTableColumns.EXTERNAL_GAME_ID + " TEXT UNIQUE NOT NULL")
        table_columns.append(_GamesTableColumns.IS_PLAYER_VS_PLAYER + " INTEGER NOT NULL")
        table_columns.append(_GamesTableColumns.HOST_USER_ID + " INTEGER NOT NULL")
        table_columns.append(_GamesTableColumns.GUEST_USER_ID + " INTEGER")
        table_columns.append(_GamesTableColumns.IS_HOST_PLAYING_WHITE + " INTEGER NOT NULL")
        table_columns.append(_GamesTableColumns.GAME_STATUS + " INTEGER NOT NULL")
        table_columns.append(_GamesTableColumns.GAME_END_METHOD + " INTEGER")
        table_columns.append(_GamesTableColumns.DID_HOST_WIN + " INTEGER")
        table_columns.append(_GamesTableColumns.DID_GAME_DRAW + " INTEGER")
        table_columns.append(_GamesTableColumns.PASSWORD + " TEXT NOT NULL")
        table_columns.append(_GamesTableColumns.MOVES_PLAYED + " TEXT NOT NULL")
        table_columns_joined = '(' + ', '.join(table_columns) + ')'
        self.execute_script("CREATE TABLE IF NOT EXISTS " + GAMES_TABLE_NAME + ' ' + table_columns_joined + ';')
        self.commit_changes()

    def does_nickname_exist(self, nickname: str):
        self.logger.debug("Checking if '" + nickname + "' already exists as a nickname") 
        # Executing scripts here differently to avoid SQL injections from nickname
        c = self.conn.cursor()
        c.execute('SELECT nickname FROM users WHERE nickname=?;', (nickname,))
        data = c.fetchone()
        return data is not None    
 
    def add_user(self, nickname: str):
        timestamp = int(time.time())
        self.logger.debug("Adding user: '" + nickname + "'") 
        # Executing scripts here differently to avoid SQL injections from nickname
        c = self.conn.cursor()
        c.execute('INSERT INTO users VALUES (NULL, ?, ?);', (nickname, str(timestamp)))
        self.commit_changes()
        c.execute('SELECT id FROM users WHERE nickname=?', (nickname,))
        data = c.fetchone()
        if data is None:
            self.logger.error("Something went wrong. Could not retrieve ID for newly created user: '" + nickname + "'")
            raise Exception("add_user(): Error when adding user, could not retrieve ID")
        return data[0]

    def update_timestamp_for_user(self, user_id: int):
        timestamp = int(time.time())
        self.logger.debug("Updating 'last_request' column for user with ID: " + str(user_id))
        self.execute_script("UPDATE " + USERS_TABLE_NAME + " SET last_request = " + str(timestamp) + " WHERE id = " + str(user_id) + ";") 
        self.commit_changes()

    def _generate_external_id(self, internal_id: int):
        # logic below is meant to be random so it's not easy to find patterns in game ID generation
        self.logger.debug("Generating external ID given internal ID: " + str(internal_id))
        ARBITRARY_INTEGER = 98546123
        ARBITRARY_STRING_1 = "$treSAExjklmnpcvx"
        hash_step_1 = hash(str(ARBITRARY_INTEGER + internal_id) + ARBITRARY_STRING_1)
        hash_step_2 = list(str(hash_step_1))
        if hash_step_1 < 0:
            if internal_id % 2 == 0:
                hash_step_2[0] = 'G'
            elif internal_id % 5 == 0:
                hash_step_2[0] = 'K'
            elif internal_id % 3 == 0:
                hash_step_2[0] = 'M'
            else:
                hash_step_2[0] = 'Z'
        else:
            hash_step_2.append(str((hash_step_1 * 10 + 7) % 10))
            if internal_id % 2 == 0:
                hash_step_2[0] = 'P'
            elif internal_id % 5 == 0:
                hash_step_2[0] = 'U'
            elif internal_id % 3 == 0:
                hash_step_2[0] = 'R'
            else:
                hash_step_2[0] = 'Q'
        if len(hash_step_2) >= 10:
            ARBITRARY_STRING_2 = 'EOMIUBVRTX'
            ARBITRARY_STRING_3 = 'ZQWPCNIVCL'
            if internal_id % 2 == 0 and hash_step_1 % 2 == 0:
                hash_step_2[2] = ARBITRARY_STRING_2[ord(hash_step_2[2]) - ord('0')]
                hash_step_2[4] = ARBITRARY_STRING_2[ord(hash_step_2[4]) - ord('0')]
                hash_step_2[7] = ARBITRARY_STRING_3[ord(hash_step_2[7]) - ord('0')]
                hash_step_2[9] = ARBITRARY_STRING_3[ord(hash_step_2[9]) - ord('0')]
            elif internal_id % 2 == 0 and hash_step_1 % 2 != 0:
                hash_step_2[1] = ARBITRARY_STRING_2[ord(hash_step_2[1]) - ord('0')]
                hash_step_2[4] = ARBITRARY_STRING_2[ord(hash_step_2[4]) - ord('0')]
                hash_step_2[5] = ARBITRARY_STRING_3[ord(hash_step_2[5]) - ord('0')]
                hash_step_2[8] = ARBITRARY_STRING_3[ord(hash_step_2[8]) - ord('0')]
            elif internal_id % 2 != 0 and hash_step_1 % 2 == 0:
                hash_step_2[3] = ARBITRARY_STRING_2[ord(hash_step_2[3]) - ord('0')]
                hash_step_2[5] = ARBITRARY_STRING_2[ord(hash_step_2[5]) - ord('0')]
                hash_step_2[6] = ARBITRARY_STRING_3[ord(hash_step_2[6]) - ord('0')]
                hash_step_2[7] = ARBITRARY_STRING_3[ord(hash_step_2[7]) - ord('0')]
            elif internal_id % 2 != 0 and hash_step_1 % 2 != 0:
                hash_step_2[9] = ARBITRARY_STRING_2[ord(hash_step_2[9]) - ord('0')]
                hash_step_2[3] = ARBITRARY_STRING_2[ord(hash_step_2[3]) - ord('0')]
                hash_step_2[2] = ARBITRARY_STRING_3[ord(hash_step_2[2]) - ord('0')]
                hash_step_2[4] = ARBITRARY_STRING_3[ord(hash_step_2[4]) - ord('0')]
        return ''.join(hash_step_2)

    def create_pvp_game(self, host_user_id: int, host_playing_white: bool, password=''):
        self.logger.debug("Adding PVP game hosted by user: " + str(host_user_id))
        cursor = self.execute_script("SELECT COUNT(*) FROM " + GAMES_TABLE_NAME)
        expected_internal_id = int(cursor.fetchone()[0]) + 1
        external_id = self._generate_external_id(expected_internal_id) 
        values_to_insert = list()
        values_to_insert.append('NULL') # INTERNAL_GAME_ID
        values_to_insert.append("'" + external_id + "'") # EXTERNAL_GAME_ID
        values_to_insert.append('1') # IS_PLAYER_VS_PLAYER
        values_to_insert.append(str(host_user_id)) # HOST_USER_ID
        values_to_insert.append('NULL') # GUEST_USER_ID
        values_to_insert.append('1' if host_playing_white else '0') # IS_HOST_PLAYING_WHITE
        values_to_insert.append(str(GameStatus.WAITING_FOR_OPPONENT)) # GAME_STATUS
        values_to_insert.append('NULL') # GAME_END_METHOD
        values_to_insert.append('NULL') # DID_HOST_WIN
        values_to_insert.append('NULL') # DID_GAME_DRAW
        values_to_insert.append("'" + password + "'") # PASSWORD
        values_to_insert.append("''") # MOVES_PLAYED
        values_to_insert_appended = ' VALUES(' + ', '.join(values_to_insert) + ')'
        self.execute_script("INSERT INTO " + GAMES_TABLE_NAME + values_to_insert_appended + ';')
        self.commit_changes()
        return external_id

    def get_game_data(self, external_game_id: str, attr: str):
        condition = " WHERE " + _GamesTableColumns.EXTERNAL_GAME_ID + "='" + external_game_id + "'"
        cursor = self.execute_script("SELECT " + attr + " FROM " + GAMES_TABLE_NAME + condition + ';')
        data = cursor.fetchone()
        if data is None:
            return None
        return data[0]

    def get_pvp_game_pass(self, external_game_id: str):
        return self.get_game_data(external_game_id, _GamesTableColumns.PASSWORD)        

    def get_game_status(self, external_game_id: str):
        return self.get_game_data(external_game_id, _GamesTableColumns.GAME_STATUS)        

    def update_game_status(self, external_game_id: str, new_status: int):
        set_statement = " SET " + _GamesTableColumns.GAME_STATUS + '=' + str(new_status) 
        condition = " WHERE " + _GamesTableColumns.EXTERNAL_GAME_ID + "='" + external_game_id + "'"
        script = "UPDATE " + GAMES_TABLE_NAME + set_statement + condition + ';'
        self.execute_script(script)
        self.commit_changes()

    def cancel_pvp_game(self, external_game_id: str):
        self.update_game_status(external_game_id, GameStatus.CANCELLED)

    def set_pvp_game_active(self, external_game_id: str, guest_user_id: int):
        self.logger.debug("Setting PVP game active: " + external_game_id)
        vals_to_update = list()
        vals_to_update.append(_GamesTableColumns.GAME_STATUS + ' = ' + str(GameStatus.ACTIVE))
        vals_to_update.append(_GamesTableColumns.GUEST_USER_ID + ' = ' + str(guest_user_id))
        set_statement = " SET " + ', '.join(vals_to_update)
        condition = " WHERE " + _GamesTableColumns.EXTERNAL_GAME_ID + " = '" + external_game_id + "'"
        script = "UPDATE " + GAMES_TABLE_NAME + set_statement + condition + ';'
        self.execute_script(script)
        self.commit_changes()
        # returns whether or not the guest is playing white
        is_host_playing_white = self.get_game_data(external_game_id, _GamesTableColumns.IS_HOST_PLAYING_WHITE)
        if is_host_playing_white == 0:
            return True
        else:
            return False
       
    def end_game(self, external_game_id: str, game_end_method: int, did_host_win: bool, did_game_draw: bool, moves_played: str):
        vals_to_update = list()
        vals_to_update.append(_GamesTableColumns.GAME_STATUS + '=' + str(GameStatus.COMPLETED))
        vals_to_update.append(_GamesTableColumns.GAME_END_METHOD + '=' + str(game_end_method))
        did_host_win_bool = '1' if did_host_win else '0'
        vals_to_update.append(_GamesTableColumns.DID_HOST_WIN + '=' + did_host_win_bool)
        did_game_draw_bool = '1' if did_game_draw else '0'
        vals_to_update.append(_GamesTableColumns.DID_GAME_DRAW + '=' + did_game_draw_bool)
        vals_to_update.append(_GamesTableColumns.MOVES_PLAYED + "='" + moves_played + "'")
        set_statement = " SET " + ', '.join(vals_to_update)
        condition = " WHERE " + _GamesTableColumns.EXTERNAL_GAME_ID + "='" + external_game_id + "'"
        script = "UPDATE " + GAMES_TABLE_NAME + set_statement + condition + ';'
        self.execute_script(script)
        self.commit_changes()

    def get_opponent_nickname(self, external_game_id: str, is_host: bool):
        opponent_user_id = 0
        if is_host:
            opponent_user_id = self.get_game_data(external_game_id, _GamesTableColumns.GUEST_USER_ID)
        else:
            opponent_user_id = self.get_game_data(external_game_id, _GamesTableColumns.HOST_USER_ID)
        cursor = self.execute_script("SELECT nickname FROM " + USERS_TABLE_NAME + " WHERE id=" + str(opponent_user_id) + ';')
        data = cursor.fetchone()
        return data[0]
            
