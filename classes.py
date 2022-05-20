import telebot
import tweepy
import asyncio
import mysql.connector
from decouple import config
from telebot.types import ReplyKeyboardMarkup

class TelegramBot:
    def __init__(self):
        self.TELEGRAM_API_KEY = config('TELEGRAM_API_KEY')
        self.twitterRequester = TwitterRequester()
        self.database = Database()
        self.chatID = None
        self.bot = telebot.TeleBot(self.TELEGRAM_API_KEY)
        self._init_handlers()
        self.bot.polling()

    def _extract_arg(self, arg):
        return arg.split()[1:]

    def initButtons(self):
        keyboard = ReplyKeyboardMarkup(resize_keyboard=True, one_time_keyboard=False).add('/show', '/help')
        self.bot.send_message(self.chatID, 'something', reply_markup=keyboard)

    def createAccount(self, givenData):
        user = givenData[0][0]
        return Account(user.id, user.name, user.username)

    async def findDiff(self):
        url = 'https://twitter.com/'
        while True:
            print('start')
            await asyncio.sleep(10)
            all_accounts = self.database.getAllUsers()
            print(all_accounts)
            for id, name, username, twitter_id  in all_accounts:
                refreshed_user_following = self.twitterRequester.getFollowings(twitter_id)
                actual_followings = list(map(lambda x: x[1], self.database.getFollowings(id)))
                intersection = list(map(lambda x: url + x, list(filter(lambda x: x not in actual_followings, refreshed_user_following))))
                if intersection != []:
                    res = 'Account: ' + name + ' starts following: \n'
                    for value in intersection:
                        res += value + '\n'
                    self.bot.send_message(self.chatID, res)
                self.database.deleteFollowings(id)
                self.database.add_following(refreshed_user_following, id)

    def _init_handlers(self):

        @self.bot.message_handler(commands=['start'])
        def showAccounts(message):
            self.chatID = message.chat.id
            self.initButtons()
            self.bot.reply_to(message, 'Ready to use')
            asyncio.run(self.findDiff())

        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            result = 'Commands: \n' \
                     '/add <name ID>\n' \
                     '/delete <name ID>\n' \
                     '/show\n'
            self.bot.reply_to(message, result)

        @self.bot.message_handler(commands=['show'])
        def showAccounts(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            text = '\n'.join(list(map(lambda x: x[2], self.database.getAllUsers())))
            text = 'Accounts you are following:\n' + text
            self.bot.reply_to(message, text)

        @self.bot.message_handler(commands=['delete'])
        def showAccounts(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            username = self._extract_arg(message.text)
            if username == []:
                self.bot.reply_to(message, 'Parameter is needed')
                return
            self.database.deleteUser(username)
            self.bot.reply_to(message, username + ' successfully deleted.')


        @self.bot.message_handler(commands=['add'])
        def addAccounnt(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            name = self._extract_arg(message.text)
            if name == []:
                self.bot.reply_to(message, 'Parameter is needed')
                return
            retrievedUser = self.twitterRequester.getUser(name)
            if 'errors' in retrievedUser:
                self.bot.reply_to(message, 'Account with given username probably not exist')
            else:
                if self.database.checkAccountIfExists(retrievedUser[0][0]):
                    self.bot.reply_to(message, 'Account is already added to tracking')
                    return
                account = self.createAccount(retrievedUser)
                id = self.database.add_account(account)
                followings = self.twitterRequester.getFollowings(account.id)
                self.database.add_following(followings, id)
                account._setFollowings(followings)
                self.bot.reply_to(message, 'Account added to tracking')

"""
Account class for storing users who have to be tracked
"""
class Account:
    def __init__(self,id, name, username):
        self.id = id
        self.name = name
        self.username = username
        self.link = 'https://twitter.com/' + self.username
        self.following_usernames = []

    def _setFollowings(self, followings):
        for following in followings:
            if following not in self.following_usernames:
                self.following_usernames.append(following)

"""
TwitterRequester class for sending requests
"""
class TwitterRequester:
    def __init__(self):
        self.TWITTER_API_KEY = config('TWITTER_API_KEY')
        self.TWITTER_API_KEY_SECRET = config('TWITTER_API_KEY_SECRET')
        self.TWITTER_ACCESS_TOKEN = config('TWITTER_ACCESS_TOKEN')
        self.TWITTER_ACCESS_TOKEN_SECRET = config('TWITTER_ACCESS_TOKEN_SECRET')
        self.TWITTER_BEARER_TOKEN = config('TWITTER_BEARER_TOKEN')

        self.client = tweepy.Client(self.TWITTER_BEARER_TOKEN, self.TWITTER_API_KEY,
                       self.TWITTER_API_KEY_SECRET, self.TWITTER_ACCESS_TOKEN,
                       self.TWITTER_ACCESS_TOKEN_SECRET, wait_on_rate_limit = True)

    def getUser(self, username):
        return self.client.get_users(usernames = username)

    def getFollowings(self, userID):
        blocks = tweepy.Paginator(self.client.get_users_following, int(userID), max_results = 100, limit = 200)
        result = []
        for block in blocks:
            print(block)
            for following in ([] if block[0] == None else block[0]):
                print(following)
                result.append(following.username)
        return result


class Database:
    SQL_INSERT_USER = "INSERT INTO users (name, username, twitter_id) VALUES (%s, %s, %s)"
    SQL_INSERT_FOLLOWING = "INSERT INTO followings (username, user_id) VALUES (%s, %s)"
    SQL_CHECK_ACCOUNT = "SELECT * FROM users WHERE username = %s"
    SQL_DELETE_FOLLOWINGS = "DELETE FROM followings WHERE user_id = %s"
    SQL_GET_ALL_USERS = "SELECT * FROM users"
    SQL_GET_SPECIFIC_FOLLOWINGS = "SELECT * FROM followings WHERE user_id = %s"
    SQL_CHECK_FOLLOWING = "SELECT * FROM followings WHERE username = %s"
    SQL_DELETE_USER = "DELETE FROM users WHERE username = %s"
    def __init__(self):
        self.db = mysql.connector.connect(host = config('DB_HOST'), user = config('DB_USERNAME'), password = config('DB_PASSWORD'), database = config('DB_NAME'))
        self.cursor = self.db.cursor(buffered=True)

    def add_account(self, account):
        print('id:', account.id)
        self.cursor.execute(self.SQL_INSERT_USER, ("" + account.name, "" + account.username, account.id))
        last_id = self.cursor.lastrowid
        self.db.commit()
        return last_id

    def deleteUser(self, username):
        self.cursor.execute(self.SQL_DELETE_USER, (username,))
        self.db.commit()

    def deleteFollowings(self, user_id):
        self.cursor.execute(self.SQL_DELETE_FOLLOWINGS, (user_id,))
        self.db.commit()

    def getAllUsers(self):
        self.cursor.execute(self.SQL_GET_ALL_USERS)
        result = self.cursor.fetchall()
        return result

    def add_following(self, followings, user_id):
        for following in followings:
            if not self.checkFollowingIfExists(following):
                self.cursor.execute(self.SQL_INSERT_FOLLOWING, (following, user_id))
        self.db.commit()

    def getFollowings(self, userID):
        self.cursor.execute(self.SQL_GET_SPECIFIC_FOLLOWINGS, (userID,))
        result = self.cursor.fetchall()
        return result

    def checkFollowingIfExists(self, username):
        self.cursor.execute(self.SQL_CHECK_FOLLOWING, (username,))
        result = self.cursor.fetchall()
        return result != []

    def checkAccountIfExists(self, account):
        self.cursor.execute(self.SQL_CHECK_ACCOUNT, (account.username,))
        result = self.cursor.fetchall()
        print(result != [])
        return result != []
