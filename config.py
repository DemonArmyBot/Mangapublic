import os

# Read from actual environment variables (not hardcoded dict)
env_vars = {
    "API_HASH": os.getenv("API_HASH", "e7dd0576c5ac0ff8f90971d6bb04c8f5"),
    "API_ID": os.getenv("API_ID", "24473318"),
    "BOT_TOKEN": os.getenv("BOT_TOKEN", ""),
    "DATABASE_URL_PRIMARY": os.getenv("DATABASE_URL_PRIMARY", ""),
    "CACHE_CHANNEL": os.getenv("CACHE_CHANNEL", "-1002186907526"),
    "CHANNEL": os.getenv("CHANNEL", "demonarmy"),
    "FNAME": os.getenv("FNAME", ""),
    "THUMB": os.getenv("THUMB", "https://i.ibb.co/tp05kqR2/1327094-original-2032x3616-1739185776.jpg
https://i.ibb.co/BXgp7qL/1236977-original-3139x5000-1739185863.png
https://i.ibb.co/zW1Nw3yD/1114344-original-4320x7680-1741498798.jpg
https://i.ibb.co/HLy6TCCW/1293420-original-1928x2840-1741498811.jpg
https://i.ibb.co/yncXtYNZ/1153331-original-1440x2000-1741498740.jpg
https://i.ibb.co/FkF67ZyP/devil-anime-girl.jpg")
}

# Validate required variables
if not env_vars["BOT_TOKEN"]:
    raise ValueError("BOT_TOKEN environment variable is required!")
    
if not env_vars["DATABASE_URL_PRIMARY"]:
    raise ValueError("DATABASE_URL_PRIMARY environment variable is required!")

dbname = env_vars['DATABASE_URL_PRIMARY']

# Fix PostgreSQL URL format
if dbname.startswith('postgres://'):
    dbname = dbname.replace('postgres://', 'postgresql://', 1)

print(f"Database URL: {dbname}")
print(f"Bot Token present: {bool(env_vars['BOT_TOKEN'])}")
