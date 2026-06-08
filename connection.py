# Connection string in one place so every file imports the same one.
# Defaults to a local SQLite file so it runs with no setup. Switching to MySQL
# is just changing the string below.

connection_string = "sqlite:///sales.db"

# MySQL version:
# user, password, host, port, schema = "root", "YOUR_PASSWORD", "127.0.0.1", 3306, "sales_tool"
# connection_string = f"mysql+pymysql://{user}:{password}@{host}:{port}/{schema}"
