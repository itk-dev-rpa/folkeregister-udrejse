"""This module contains configuration constants used across the framework"""

# The number of times the robot retries on an error before terminating.
MAX_RETRY_COUNT = 1

# Whether the robot should be marked as failed if MAX_RETRY_COUNT is reached.
FAIL_ROBOT_ON_TOO_MANY_ERRORS = True

# Error screenshot config
SMTP_SERVER = "smtp.aarhuskommune.local"
SMTP_PORT = 25
SCREENSHOT_SENDER = "robot@friend.dk"

# Constant/Credential names
ERROR_EMAIL = "Error Email"
FAELLES_SQL = "FællesSQL Udenlandske Borgere"
NOVA_API = "Nova API"
GRAPH_API = "Graph API"
SKAT_WEBSERVICE = "SKAT Webservice"
KEYVAULT_CREDENTIALS = "Keyvault"
KEYVAULT_URI = "Keyvault URI"

KEYVAULT_PATH = "Skat_webservice"

# Other configs
INCOME_MONTHS = 18
MIN_INCOME = 10_000
MAX_HANDLED_CASES = 400
