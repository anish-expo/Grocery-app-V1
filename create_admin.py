from app import app, db, Role, User

def create_admin_user():
    with app.app_context():
        admin_role = Role.query.filter_by(name='Admin').first()
        if admin_role:
            admin_user = User(username='anish', role=admin_role)
            admin_user.set_password('1234')  # Set the admin user's password
            db.session.add(admin_user)
            db.session.commit()

if __name__ == '__main__':
    create_admin_user()
