import time
import logging
import sys

from log_wrapper import Logger

MODULE_NAME = 'db_util'
USERS_TABLE_NAME = 'users'

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

    def init_nickname_table(self):
        self.logger.debug("Creating " + USERS_TABLE_NAME + " table if it doesn't exist")
        SCRIPT = "CREATE TABLE IF NOT EXISTS " + USERS_TABLE_NAME + "(id INTEGER PRIMARY KEY AUTOINCREMENT, nickname TEXT UNIQUE NOT NULL, lastRequest INTEGER)"
        self.execute_script(SCRIPT)
        self.commit_changes()

    def does_nickname_exist(self, nickname: str):
        self.logger.debug("Checking if '" + nickname + "' already exists as a nickname") 
        cursor = self.execute_script("SELECT nickname FROM " + USERS_TABLE_NAME + ";")
        data = cursor.fetchall()
        current_nicknames = set()
        for row in data:
            current_nicknames.add(row[0])
        self.logger.debug("Current nicknames are: " + str(current_nicknames))
        if nickname in current_nicknames:
            self.logger.debug("'" + nickname + "' does already exist as a nickname")
            return True
        return False

    def add_user(self, nickname: str):
        timestamp = int(time.time())
        self.logger.debug("Adding user: '" + nickname + "'") 
        self.execute_script("INSERT INTO " + USERS_TABLE_NAME + " VALUES (NULL, '" + nickname + "', " + str(timestamp) + ");")
        self.commit_changes()
        cursor = self.execute_script("SELECT id FROM " + USERS_TABLE_NAME + " WHERE nickname='" + nickname + "';")
        data = cursor.fetchone()
        if data is None:
            self.logger.error("Something went wrong. Could not retrieve ID for newly created user: '" + nickname + "'")
            raise Exception("add_user(): Error when adding user, could not retrieve ID")
        return data[0]

    def update_timestamp_for_user(self, user_id: int):
        timestamp = int(time.time())
        self.logger.debug("Updating 'lastRequest' column for user with ID: " + str(user_id))
        self.execute_script("UPDATE " + USERS_TABLE_NAME + " SET lastRequest = " + str(timestamp) + " WHERE id = " + str(user_id) + ";") 
        self.commit_changes()

