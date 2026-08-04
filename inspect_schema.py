import sqlite3

conn = sqlite3.connect('financial_analyst_copilot.db')
cur = conn.cursor()

print('TABLES:')
for row in cur.execute("SELECT name FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(row[0])

print('\nSCHEMA:')
for row in cur.execute("SELECT name, sql FROM sqlite_master WHERE type='table' ORDER BY name"):
    print(row[0])
    print(row[1])
    print()

conn.close()
