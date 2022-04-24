import telebot
import tweepy
import asyncio
from decouple import config

class TelegramBot:
    def __init__(self):
        self.TELEGRAM_API_KEY = config('TELEGRAM_API_KEY')
        self.twitterRequester = TwitterRequester()
        self.accountWrapper = AccountWrapper()
        self.chatID = None

        self.bot = telebot.TeleBot(self.TELEGRAM_API_KEY)
        self._init_handlers()
        self.bot.polling()

    def _extract_arg(self, arg):
        # TODO: regex parser
        return arg.split()[1:]

    def createAccount(self, givenData):
        user = givenData[0][0]
        return Account(user.id, user.name, user.username)

    async def findDiff(self):
        url = 'https://twitter.com/'
        while True:
            print('start')
            await asyncio.sleep(60)
            for username_kay, account in self.accountWrapper.accounts.items():
                refreshed_user_following = self.twitterRequester.getFollowings(account.id)
                intersection = list(map(lambda x: url + x, list(filter(lambda x: x not in account.following_usernames, refreshed_user_following))))
                if intersection != []:
                    res = 'Account: ' + account.username + ' starts following: \n'
                    for value in intersection:
                        res += value + '\n'
                    self.bot.send_message(self.chatID, res)
                    account.following_usernames = refreshed_user_following

    def _init_handlers(self):

        @self.bot.message_handler(commands=['start'])
        def showAccounts(message):
            self.chatID = message.chat.id
            self.bot.reply_to(message, 'Ready to use')
            asyncio.run(self.findDiff())

        @self.bot.message_handler(commands=['help'])
        def help(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            result = 'Commands: \n' \
                     '/addAccount <name ID>\n' \
                     '/showAccounts'
            self.bot.reply_to(message, result)

        @self.bot.message_handler(commands=['showAccounts'])
        def showAccounts(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            text = self.accountWrapper.showAccounts()
            self.bot.reply_to(message, text)

        @self.bot.message_handler(commands=['deleteAccount'])
        def showAccounts(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            username = self._extract_arg(message.text)
            self.accountWrapper.delete_account(username)
            self.bot.reply_to(message, username + ' successfully deleted.')


        @self.bot.message_handler(commands=['addAccount'])
        def addAccounnt(message):
            self.chatID = message.chat.id if (self.chatID == None) else self.chatID
            name = self._extract_arg(message.text)
            retrievedUser = self.twitterRequester.getUser(name)
            if 'errors' in retrievedUser:
                self.bot.reply_to(message, 'An error occurs')
            else:
                account = self.createAccount(retrievedUser)
                followings = self.twitterRequester.getFollowings(account.id)
                account._setFollowings(followings)
                self.accountWrapper.add_account(account)
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
Account wrapper class for storing all accounts. Accounts are stored in dictionary with its ID as key and Account class as value. 
"""
class AccountWrapper:
    def __init__(self):
        self.accounts = {}

    def add_account(self, account):
        if account.username not in self.accounts:
            self.accounts[account.username] = account

    def delete_account(self, username):
        self.accounts.pop(username)

    def showAccounts(self):
        res = ''
        for _, value in self.accounts.items():
            text = "{:<8} : {:<8}"
            text = text.format(value.username, value.link)
            res += text + '\n'
        res = 'Empty' if res == '' else res
        return res


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
        blocks = tweepy.Paginator(self.client.get_users_following, userID, max_results = 100, limit = 200)
        result = []
        for block in blocks:
            for following in ([] if block[0] == None else block[0]):
                result.append(following.username)
        return result