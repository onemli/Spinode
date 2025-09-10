from core.auth import create_user
create_user("admin", "admin", is_admin=True)
print("admin/admin oluşturuldu (varsa atlanır).")
