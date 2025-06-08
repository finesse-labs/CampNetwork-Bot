# ========================= ОСНОВНЫЕ НАСТРОЙКИ =========================

CAPTCHA_API_KEY = "" # Ключ для антикапчи

SHUFFLE_ACCOUNTS = True              # Перемешивать аккаунты перед запуском
ACCOUNT_LAUNCH_DELAY = [1, 10]        # Задержка между запуском аккаунтов (в минутах)

# ========================= НАСТРОЙКИ КВЕСТОВ =========================

SHUFFLE_QUESTS = True               # Перемешать порядок выполнения квестов на акк
QUEST_DELAY = [1, 10]                 # Задержка между выполнением квестов (в минутах)
CLAIM_DELAY = [0, 1]                # Задержка перед клеймом (в минутах)

ALLOWED_QUEST_TYPES = ["follow", "social", "custom", "faucet"]  # Разрешенные типы квестов
#                      подписка   сошиал     ончейн    кран  
TASKS = ["follow", "social", "custom", "faucet"]         # Выполнять квесты этих типов 






















# ========================= НАСТРОЙКИ СОФТА =========================

QUEST_API_URL = "https://testnet.campnetwork.xyz/api/snag/rules/complete"
TWITTER_API_URL = "https://twitter.com/i/api/1.1/friendships/create.json"
BEARER_TOKEN = "AAAAAAAAAAAAAAAAAAAAANRILgAAAAAAnNwIzUejRCOuH5E6I8xnZz4puTs%3D1Zv7ttfk8LF81IUq16cHjhLTvJu4FA33AGWWjCpTnA"
