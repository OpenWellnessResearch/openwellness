import os

# Tests must never read a developer's real `.env` (it may point at live datastores).
os.environ["OPENWELLNESS_ENV_FILE"] = os.devnull
