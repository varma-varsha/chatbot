from app import app, db, User, Course, Chapter, init_db_data
import sys

def verify_system():
    print("Verifying system setup...")
    
    with app.app_context():
        # 1. Initialize DB
        print("Creating/Checking database tables...")
        db.create_all()
        
        # 2. Run data migration
        print("Running data migration...")
        try:
            init_db_data()
        except Exception as e:
            print(f"Migration error (might be expected if data exists): {e}")

        # 3. Check Users
        try:
            print(f"Users count: {User.query.count()}")
            # Check for role column
            user = User.query.first()
            if user:
                print(f"Sample user role: {user.role}")
            else:
                print("No users found.")
        except Exception as e:
            print(f"Error checking Users (column missing?): {e}")
            return False

        # 4. Check Courses
        try:
            course_count = Course.query.count()
            print(f"Courses count: {course_count}")
            if course_count == 0:
                print("ERROR: No courses found in DB after migration!")
                return False
            
            course = Course.query.first()
            print(f"Sample course: {course.language} - {len(course.chapters)} chapters")
        except Exception as e:
            print(f"Error checking Courses: {e}")
            return False

        # 5. Create Test Admin
        admin_email = "admin@test.com"
        admin = User.query.filter_by(email=admin_email).first()
        if not admin:
            print("Creating test admin user...")
            admin = User(username="admin", email=admin_email, role="admin")
            admin.set_password("admin123")
            db.session.add(admin)
            db.session.commit()
            print("Test admin created.")
        else:
            print("Test admin already exists.")

    print("Verification successful!")
    return True

if __name__ == "__main__":
    if verify_system():
        print("System is ready.")
        sys.exit(0)
    else:
        print("System verification failed.")
        sys.exit(1)
