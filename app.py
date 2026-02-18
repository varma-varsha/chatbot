from flask import render_template, redirect, url_for, flash, request, jsonify, abort, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from chatbot import Chatbot
from functools import wraps
from models import app, db, User, CourseProgress, Course, Chapter
import json
from pathlib import Path
from forms import SignupForm, LoginForm
from flask_wtf.csrf import generate_csrf, CSRFProtect
from datetime import datetime
from reportlab.lib import colors
from reportlab.lib.pagesizes import letter, A4
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, PageBreak, Preformatted, Image
from reportlab.lib.units import inch
from io import BytesIO
from flask import send_file
import textwrap
import logging
from traceback import format_exc

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.init_app(app)
login_manager.login_view = 'login'

csrf = CSRFProtect(app)



@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.role != 'admin':
            flash('You do not have permission to access this page.', 'danger')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if current_user.is_authenticated:
        return redirect(url_for('dashboard'))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data)
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Signup successful! Please log in.', 'success')
        return redirect(url_for('login'))
    else:
        # Debug: Print validation errors
        print(f"Form validation failed. Errors: {form.errors}")
        print(f"Form data: username={form.username.data}, email={form.email.data}")

    return render_template('signup.html', form=form)


# Create a single chatbot instance
chatbot = Chatbot('knowledge_base.json')

@app.route('/chat', methods=['POST'])
@login_required
def chat():
    user_message = request.json.get('message', '')
    # Use current user's ID to maintain state
    bot_response = chatbot.process_message(user_message, current_user.id)

    # Generate and return the CSRF token
    csrf_token = generate_csrf()

    # Handle different response types
    if isinstance(bot_response, dict):
        return jsonify({
            'response': bot_response.get('response', ''),
            'has_code': 'code' in bot_response,
            'language': bot_response.get('language', ''),
            'code': bot_response.get('code', ''),
            'follow_up': bot_response.get('follow_up', ''),
            'csrf_token': csrf_token,
            'start_course': bot_response.get('start_course', False),
        })
    else:
        return jsonify({
            'response': bot_response,
            'has_code': False,
            'csrf_token': csrf_token
        })


@app.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        # If already logged in, redirect to the next page or dashboard
        next_page = request.args.get('next')
        if next_page:
            return redirect(next_page)
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            if user.role == 'admin':
                return redirect(next_page or url_for('admin_dashboard'))
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)


@app.route('/admin/signup', methods=['GET', 'POST'])
def admin_signup():
    if current_user.is_authenticated:
        return redirect(url_for('admin_dashboard'))

    form = SignupForm()
    if form.validate_on_submit():
        user = User(username=form.username.data, email=form.email.data, role='admin')
        user.set_password(form.password.data)
        db.session.add(user)
        db.session.commit()

        flash('Admin signup successful! Please log in.', 'success')
        return redirect(url_for('login'))

    return render_template('admin_signup.html', form=form)


@app.route('/admin/dashboard')
@login_required
@admin_required
def admin_dashboard():
    users_count = User.query.filter_by(role='customer').count()
    courses_count = Course.query.count()
    courses = Course.query.all()
    users = User.query.filter_by(role='customer').limit(5).all() # Show recent users
    return render_template('admin_dashboard.html', 
                         users_count=users_count, 
                         courses_count=courses_count,
                         courses=courses,
                         users=users)


@app.route('/admin/add_course', methods=['GET', 'POST'])
@login_required
@admin_required
def add_course():
    if request.method == 'POST':
        try:
            data = request.json
            course = Course(
                language=data['language'],
                description=data['description']
            )
            db.session.add(course)
            db.session.flush()

            for i, chapter_data in enumerate(data['chapters']):
                chapter = Chapter(
                    course_id=course.id,
                    title=chapter_data['title'],
                    description=chapter_data['description'],
                    sample_code=chapter_data.get('sampleCode', ''),
                    order=i + 1
                )
                db.session.add(chapter)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    return render_template('add_course.html')


@app.route('/admin/manage_courses')
@login_required
@admin_required
def manage_courses():
    courses = Course.query.all()
    return render_template('manage_courses.html', courses=courses)


@app.route('/admin/edit_course/<int:course_id>', methods=['GET', 'POST'])
@login_required
@admin_required
def edit_course(course_id):
    course = db.session.get(Course, course_id)
    if not course:
        flash('Course not found.', 'danger')
        return redirect(url_for('manage_courses'))

    if request.method == 'POST':
        try:
            data = request.json
            
            # Update course details
            course.language = data['language']
            course.description = data['description']
            
            # Update chapters: Simple strategy - delete all and recreate
            # This is safer to ensure order and content match exactly what user sees
            Chapter.query.filter_by(course_id=course.id).delete()
            
            for i, chapter_data in enumerate(data['chapters']):
                chapter = Chapter(
                    course_id=course.id,
                    title=chapter_data['title'],
                    description=chapter_data['description'],
                    sample_code=chapter_data.get('sampleCode', ''),
                    order=i + 1
                )
                db.session.add(chapter)
            
            db.session.commit()
            return jsonify({'success': True})
        except Exception as e:
            db.session.rollback()
            return jsonify({'error': str(e)}), 500

    return render_template('edit_course.html', course=course)


@app.route('/admin/delete_course/<int:course_id>', methods=['POST'])
@login_required
@admin_required
def delete_course(course_id):
    try:
        course = db.session.get(Course, course_id)
        if not course:
            return jsonify({'error': 'Course not found'}), 404
            
        # Delete associated chapters first (though cascade might handle it, better explicit)
        Chapter.query.filter_by(course_id=course.id).delete()
        
        # Delete course
        db.session.delete(course)
        db.session.commit()
        
        return jsonify({'success': True})
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': str(e)}), 500


@app.route('/admin/users')
@login_required
@admin_required
def admin_users():
    users = User.query.all()
    return render_template('admin_users.html', users=users)


# Add this function to load the courses data
# Add this function to load the courses data
def load_courses():
    # Keep this for backward compatibility if needed, but prefer DB
    try:
        courses_file = Path('courses.json')
        if not courses_file.exists():
            raise FileNotFoundError("courses.json not found")

        with open(courses_file, 'r') as f:
            return json.load(f)
    except json.JSONDecodeError:
        raise ValueError("Invalid JSON format in courses.json")
    except Exception as e:
        raise Exception(f"Error loading courses: {str(e)}")

def init_db_data():
    if Course.query.first() is None:
        print("Initializing database with course data...")
        try:
            data = load_courses()
            for course_data in data['courses']:
                course = Course(
                    language=course_data['language'],
                    description=course_data['description']
                )
                db.session.add(course)
                db.session.flush()  # Get course ID

                for i, chapter_data in enumerate(course_data['chapters']):
                    chapter = Chapter(
                        course_id=course.id,
                        title=chapter_data['title'],
                        description=chapter_data.get('description', ''),
                        sample_code=chapter_data.get('sampleCode', ''),
                        order=i + 1
                    )
                    db.session.add(chapter)
            
            db.session.commit()
            print("Database initialized successfully!")
        except Exception as e:
            db.session.rollback()
            print(f"Error initializing database: {e}")


# Add these new routes
@app.route('/get_course_details', methods=['GET'])
def get_course_details():
    try:
        language = request.args.get('language')
        if not language:
            return jsonify({
                'error': 'Language parameter is required'
            }), 400

        course = Course.query.filter_by(language=language).first()

        if not course:
            return jsonify({
                'error': f'No course found for language: {language}'
            }), 404
            
        course_data = {
            'language': course.language,
            'description': course.description,
            'chapters': [{
                'title': c.title,
                'description': c.description,
                'sampleCode': c.sample_code,
                'order': c.order
            } for c in course.chapters]
        }

        return jsonify(course_data)

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

# Optional: Add a route to get list of available languages
@app.route('/get_available_languages', methods=['GET'])
def get_available_languages():
    try:
        courses = Course.query.with_entities(Course.language).all()
        languages = [c.language for c in courses]
        return jsonify({
            'languages': languages
        })
    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500


@app.route('/api/get_user_courses')
@login_required
def get_user_courses():
    try:
        # Get all course progress records for the current user
        progress_records = CourseProgress.query.filter_by(user_id=current_user.id).all()

        # Format the response
        user_courses = []
        for progress in progress_records:
            # Find the course details
            course = Course.query.filter_by(language=progress.course_language).first()

            if course:
                # Parse chapters_completed if it's a string
                chapters_completed = progress.chapters_completed
                if isinstance(chapters_completed, str):
                    try:
                        chapters_completed = json.loads(chapters_completed)
                    except:
                        chapters_completed = []
                
                # Ensure it's a list
                if not isinstance(chapters_completed, list):
                    chapters_completed = []
                
                user_courses.append({
                    'language': progress.course_language,
                    'progress_percentage': progress.progress_percentage,
                    'last_accessed_chapter': progress.last_accessed_chapter,
                    'chapters_completed': chapters_completed,
                    'chapters_completed_count': len(chapters_completed),
                    'total_chapters': len(course.chapters),
                    'started_at': progress.started_at.isoformat() if progress.started_at else None,
                    'last_updated': progress.last_updated.isoformat() if progress.last_updated else None
                })

        return jsonify({
            'courses': sorted(user_courses, key=lambda x: x['last_updated'] or '', reverse=True)
        })

    except Exception as e:
        print(f"Error fetching user courses: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/download_course_pdf/<course_language>', methods=['GET'])
@login_required
def download_course_pdf(course_language):
    try:
        # Get course progress
        progress = CourseProgress.query.filter_by(
            user_id=current_user.id,
            course_language=course_language
        ).first()

        if not progress:
            app.logger.error(f"No progress found for user {current_user.id} in {course_language}")
            return jsonify({'error': 'No course progress found'}), 404

        # Find specific course
        course = Course.query.filter_by(language=course_language).first()

        if not course:
            app.logger.error(f"Course not found: {course_language}")
            return jsonify({'error': f'Course {course_language} not found'}), 404

        # Create PDF
        buffer = BytesIO()
        doc = SimpleDocTemplate(
            buffer,
            pagesize=A4,
            rightMargin=50,
            leftMargin=50,
            topMargin=50,
            bottomMargin=50
        )

        # Styles
        styles = getSampleStyleSheet()

        # Course Title Style
        title_style = ParagraphStyle(
            'CourseTitle',
            parent=styles['Heading1'],
            fontSize=28,
            spaceAfter=30,
            alignment=1,  # Center
            textColor=colors.HexColor('#1a365d')
        )

        # Chapter Title Style
        chapter_style = ParagraphStyle(
            'ChapterTitle',
            parent=styles['Heading2'],
            fontSize=20,
            spaceBefore=20,
            spaceAfter=20,
            textColor=colors.HexColor('#2b6cb0')
        )

        # Description Style
        desc_style = ParagraphStyle(
            'Description',
            parent=styles['Normal'],
            fontSize=12,
            leading=16,
            spaceBefore=10,
            spaceAfter=15,
            textColor=colors.HexColor('#2d3748')
        )

        code_style = ParagraphStyle(
            'CodeBlock',
            parent=styles['Code'],
            fontName='Courier',
            fontSize=10,
            leading=12,
            spaceBefore=10,
            spaceAfter=10,
            textColor=colors.HexColor('#1a202c'),
            backColor=colors.HexColor('#f7fafc')
        )



        elements = []

        # Cover Page
        elements.append(Spacer(1, 100))
        elements.append(Paragraph(f"{course_language} Programming", title_style))
        elements.append(Spacer(1, 20))
        elements.append(Paragraph("Complete Course Material", chapter_style))
        elements.append(Spacer(1, 40))

        # Course Info
        elements.append(Paragraph(f"Student: {current_user.username}", desc_style))
        elements.append(Paragraph(f"Generated: {progress.last_updated.strftime('%B %d, %Y')}", desc_style))
        elements.append(Paragraph(f"Progress: {progress.progress_percentage:.1f}%", desc_style))
        elements.append(PageBreak())

        # Course Description
        elements.append(Paragraph("Course Overview", chapter_style))
        elements.append(Paragraph(course.description, desc_style))
        elements.append(PageBreak())

        # Table of Contents
        elements.append(Paragraph("Table of Contents", chapter_style))
        elements.append(Spacer(1, 20))
        for i, chapter in enumerate(course.chapters, 1):
            elements.append(Paragraph(f"Chapter {i}: {chapter.title}", desc_style))
        elements.append(PageBreak())

        # Chapters Content
        for i, chapter in enumerate(course.chapters, 1):
            # Chapter Title
            elements.append(Paragraph(f"Chapter {i}: {chapter.title}", chapter_style))

            # Chapter Description
            if chapter.description:
                elements.append(Paragraph(chapter.description, desc_style))

            # Code Examples
            # In the chapter loop, update the code block creation:
            if chapter.sample_code:
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Code Example:", desc_style))

                # Format code with proper indentation
                formatted_code = textwrap.dedent(chapter.sample_code).strip()


                # Split long lines to fit in the PDF
                wrapped_lines = []
                for line in formatted_code.split('\n'):
                    if len(line) > 80:
                        wrapped_lines.extend(textwrap.wrap(line, width=80))
                    else:
                        wrapped_lines.append(line)

                formatted_code = '\n'.join(wrapped_lines)

                # Create code block without wrap parameter
                code_block = Preformatted(
                    formatted_code,
                    code_style,
                    maxLineLength=80
                )
                elements.append(code_block)

        # Build PDF
        doc.build(elements)
        buffer.seek(0)

        return send_file(
            buffer,
            download_name=f'{course_language}_programming_course.pdf',
            mimetype='application/pdf'
        )


    except Exception as e:
        app.logger.error(f"Error generating PDF: {str(e)}")
        import traceback
        app.logger.error(traceback.format_exc())
        return jsonify({'error': str(e)}), 500

@app.route('/test/courses')
@login_required
def test_courses():
    progress_records = CourseProgress.query.filter_by(user_id=current_user.id).all()
    return jsonify({
        'count': len(progress_records),
        'courses': [
            {
                'language': p.course_language,
                'progress_percentage': p.progress_percentage,
                'chapters_completed': p.chapters_completed
            } for p in progress_records
        ]
    })

@app.route('/api/update_progress', methods=['POST'])
@login_required
def update_progress():
    try:
        data = request.json
        course_language = data.get('language')
        chapter_number = data.get('chapterNumber')

        # Input validation
        if not course_language or chapter_number is None:
            return jsonify({'error': 'Missing required parameters'}), 400

        # Convert chapter_number to int
        try:
            chapter_number = int(chapter_number)
        except ValueError:
            return jsonify({'error': 'Chapter number must be an integer'}), 400

        # Get or create progress record
        progress = CourseProgress.query.filter_by(
            user_id=current_user.id,
            course_language=course_language
        ).first()

        if not progress:
            # Create new progress record
            progress = CourseProgress(
                user_id=current_user.id,
                course_language=course_language,
                chapters_completed=[chapter_number],
                last_accessed_chapter=chapter_number,
                progress_percentage=0.0,
                started_at=datetime.utcnow(),
                last_updated=datetime.utcnow()
            )
            db.session.add(progress)
        else:
            # Update existing progress
            try:
                # Ensure chapters_completed is a list
                if progress.chapters_completed is None:
                    progress.chapters_completed = []
                elif isinstance(progress.chapters_completed, str):
                    progress.chapters_completed = json.loads(progress.chapters_completed)

                # Convert to set for deduplication, then back to sorted list
                current_chapters = set(progress.chapters_completed)
                current_chapters.add(chapter_number)
                progress.chapters_completed = sorted(list(current_chapters))

                # Update last accessed chapter
                progress.last_accessed_chapter = max(progress.last_accessed_chapter or 0, chapter_number)
                progress.last_updated = datetime.utcnow()
            except Exception as e:
                print(f"Error processing chapters_completed: {str(e)}")
                return jsonify({'error': 'Error processing chapter data'}), 500

        # Calculate progress percentage
        try:
            course = Course.query.filter_by(language=course_language).first()

            if course:
                total_chapters = len(course.chapters)
                if total_chapters > 0:  # Prevent division by zero
                    progress.progress_percentage = (len(progress.chapters_completed) / total_chapters) * 100
            else:
                return jsonify({'error': 'Course not found'}), 404

        except Exception as e:
            print(f"Error calculating progress: {str(e)}")
            return jsonify({'error': 'Error calculating progress'}), 500

        # Commit changes
        try:
            db.session.commit()
        except Exception as e:
            db.session.rollback()
            print(f"Database error: {str(e)}")
            return jsonify({'error': 'Database error'}), 500

        # Return updated progress
        return jsonify({
            'success': True,
            'progress': {
                'completed_chapters': progress.chapters_completed,
                'progress_percentage': progress.progress_percentage,
                'last_accessed_chapter': progress.last_accessed_chapter
            }
        })

    except Exception as e:
        db.session.rollback()
        print(f"Unexpected error in update_progress: {str(e)}")
        return jsonify({'error': str(e)}), 500


@app.route('/debug/course_progress/<course_language>')
@login_required
def debug_course_progress(course_language):
    progress = CourseProgress.query.filter_by(
        user_id=current_user.id,
        course_language=course_language
    ).first()

    if progress:
        return jsonify({
            'user_id': progress.user_id,
            'course_language': progress.course_language,
            'chapters_completed': progress.chapters_completed,
            'last_accessed_chapter': progress.last_accessed_chapter,
            'progress_percentage': progress.progress_percentage,
            'started_at': str(progress.started_at),
            'last_updated': str(progress.last_updated)
        })
    return jsonify({'error': 'No progress found'})

@app.route('/api/get_user_progress/<course_language>', methods=['GET'])
@login_required
def get_user_progress(course_language):
    try:
        progress = CourseProgress.query.filter_by(
            user_id=current_user.id,
            course_language=course_language
        ).first()

        if not progress:
            return jsonify({
                'completed_chapters': [],
                'progress_percentage': 0,
                'last_accessed_chapter': 1
            })

        return jsonify({
            'completed_chapters': progress.chapters_completed,
            'progress_percentage': progress.progress_percentage,
            'last_accessed_chapter': progress.last_accessed_chapter
        })

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))


@app.route('/dashboard')
@login_required
def dashboard():
    return render_template('dashboard.html')


@app.route('/progress')
@login_required
def progress():
    return render_template('progress.html')


@app.route('/learning')
@login_required
def learning():
    return render_template('learning.html')


@app.route('/review')
@login_required
def review():
    return render_template('review.html')


@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


if __name__ == '__main__':
    with app.app_context():
        try:
            db.create_all()
        except Exception as e:
            print(f"Database initialization warning: {e}")
            # Continue anyway - tables might already exist
            
        # Initialize data
        try:
            init_db_data()
        except Exception as e:
            print(f"Data initialization error: {e}")

    app.run(debug=True, host='0.0.0.0', port=5000)
