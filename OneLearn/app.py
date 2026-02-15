from flask import render_template, redirect, url_for, flash, request, jsonify, abort, current_app
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from chatbot import Chatbot
from models import app, db, User, CourseProgress
import json
from pathlib import Path
from forms import SignupForm, LoginForm
from flask_wtf.csrf import generate_csrf
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
login_manager.login_view = 'login'


@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))


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
        return redirect(url_for('dashboard'))

    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and user.check_password(form.password.data):
            login_user(user)
            next_page = request.args.get('next')
            return redirect(next_page or url_for('dashboard'))
        else:
            flash('Invalid email or password', 'danger')

    return render_template('login.html', form=form)


# Add this function to load the courses data
def load_courses():
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


# Add these new routes
@app.route('/get_course_details', methods=['GET'])
def get_course_details():
    try:
        language = request.args.get('language')
        if not language:
            return jsonify({
                'error': 'Language parameter is required'
            }), 400

        courses_data = load_courses()

        # Find the requested course
        course = next(
            (course for course in courses_data['courses']
             if course['language'].lower() == language.lower()),
            None
        )

        if not course:
            return jsonify({
                'error': f'No course found for language: {language}'
            }), 404

        return jsonify(course)

    except Exception as e:
        return jsonify({
            'error': str(e)
        }), 500

# Optional: Add a route to get list of available languages
@app.route('/get_available_languages', methods=['GET'])
def get_available_languages():
    try:
        courses_data = load_courses()
        languages = [course['language'] for course in courses_data['courses']]
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

        # Get all available courses for reference
        courses_data = load_courses()

        # Format the response
        user_courses = []
        for progress in progress_records:
            # Find the course details
            course = next(
                (c for c in courses_data['courses']
                 if c['language'].lower() == progress.course_language.lower()),
                None
            )

            if course:
                user_courses.append({
                    'language': progress.course_language,
                    'progress_percentage': progress.progress_percentage,
                    'last_accessed_chapter': progress.last_accessed_chapter,
                    'chapters_completed': progress.chapters_completed,
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

        # Load courses data
        try:
            courses_data = load_courses()
        except Exception as e:
            app.logger.error(f"Error loading courses data: {str(e)}")
            return jsonify({'error': 'Failed to load course data'}), 500

        # Find specific course
        course = next(
            (c for c in courses_data.get('courses', [])
             if c['language'].lower() == course_language.lower()),
            None
        )

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
        elements.append(Paragraph(course['description'], desc_style))
        elements.append(PageBreak())

        # Table of Contents
        elements.append(Paragraph("Table of Contents", chapter_style))
        elements.append(Spacer(1, 20))
        for i, chapter in enumerate(course['chapters'], 1):
            elements.append(Paragraph(f"Chapter {i}: {chapter['title']}", desc_style))
        elements.append(PageBreak())

        # Chapters Content
        for i, chapter in enumerate(course['chapters'], 1):
            # Chapter Title
            elements.append(Paragraph(f"Chapter {i}: {chapter['title']}", chapter_style))

            # Chapter Description
            if chapter.get('description'):
                elements.append(Paragraph(chapter['description'], desc_style))

            # Code Examples
            # In the chapter loop, update the code block creation:
            if chapter.get('sampleCode'):
                elements.append(Spacer(1, 10))
                elements.append(Paragraph("Code Example:", desc_style))

                # Format code with proper indentation
                formatted_code = textwrap.dedent(chapter['sampleCode']).strip()

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
            courses_data = load_courses()
            course = next(
                (c for c in courses_data['courses']
                 if c['language'].lower() == course_language.lower()),
                None
            )

            if course:
                total_chapters = len(course['chapters'])
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


if __name__ == '__main__':
    with app.app_context():
        db.create_all()
    app.run(debug=True, host='0.0.0.0', port=5000)
