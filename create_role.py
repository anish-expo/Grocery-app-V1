from app import app,  db

with app.app_context():
    db.create_all()
def create_roles_and_users():
    with app.app_context():
        from app import Role, User

        admin_role = Role(name='Admin')
        user_role = Role(name='User')
        db.session.add(admin_role)
        db.session.add(user_role)
        db.session.commit()

if __name__ == '__main__':
    create_roles_and_users()