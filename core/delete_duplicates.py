# import sqlite3
# from db import DB_PATH
# con = sqlite3.connect(DB_PATH); cur = con.cursor()
# # keep the smallest rowid per (class_id,name), delete others
# cur.execute("""
# DELETE FROM props
# WHERE rowid NOT IN (
#   SELECT MIN(rowid) FROM props GROUP BY class_id, name
# );
# """)
# con.commit(); con.close()
# print("Duplicate props cleaned.")


from db import init_db
init_db()
print("DB schema OK")