from app import app, db,User
def delete_user(username):
    with app.app_context():
        user = User.query.filter_by(username=username).first()
        if user:
            db.session.delete(user)
            db.session.commit()
            print(f"User '{username}' deleted successfully.")
        else:
            print(f"User '{username}' not found.")

if __name__ == '__main__':
    with app.app_context():
        delete_user('')
       