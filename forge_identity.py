from app import app
from models import db, User

def forge_identity():
    with app.app_context():
        existing = User.query.filter_by(username='Stark').first()
        if existing:
            print("Stark Identity already pulse-synced in the database.")
            return
            
        user = User(username='Stark', email='stark@stark.com')
        user.set_password('make')
        db.session.add(user)
        db.session.commit()
        print("✓ Identity Successfully Forged: Stark Administrator initialized.")

if __name__ == "__main__":
    forge_identity()
