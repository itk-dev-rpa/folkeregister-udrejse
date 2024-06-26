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
INDKOMST_CREDS = "KMD Udrejse"

# Other configs
INCOME_DAYS = 545
MIN_INCOME = 10_000
MAX_HANDLED_CASES = 400
