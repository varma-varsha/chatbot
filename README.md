# OneLearn - Learning Management System

OneLearn is a Flask-based web application for interactive learning with AI-powered chatbot assistance.

## Prerequisites

- Python 3.8 or higher
- pip (Python package installer)

## Installation Steps

### 1. Clone or Navigate to the Project

```bash
cd OneLearn
```

### 2. Create a Virtual Environment (Recommended)

Create a virtual environment to isolate project dependencies:

**Windows:**
```powershell
python -m venv venv
.\venv\Scripts\Activate.ps1
```

**macOS/Linux:**
```bash
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies

Install all required Python packages:

```bash
pip install -r requirements.txt
```

If you encounter any issues, try upgrading pip first:

```bash
pip install --upgrade pip
pip install -r requirements.txt
```

### 4. Initialize the Database

The application will automatically create the database on first run. However, you can manually initialize it:

```bash
python -c "from app import app, db; app.app_context().push(); db.create_all()"
```

### 5. Run the Application

Start the Flask development server:

```bash
python app.py
```

The application will be available at: **http://localhost:5000** or **http://127.0.0.1:5000**

## Usage

1. **Sign Up**: Create a new account by clicking "Sign Up"
2. **Login**: Log in with your credentials
3. **Dashboard**: Access your learning dashboard
4. **Chat**: Interact with the AI chatbot for learning assistance
5. **Courses**: Browse and take courses in various programming languages

## Project Structure

```
OneLearn/
├── app.py                  # Main Flask application
├── models.py               # Database models
├── chatbot.py              # AI chatbot logic
├── forms.py                # WTForms for user registration/login
├── code_highlighter.py     # Code syntax highlighting
├── requirements.txt        # Python dependencies
├── knowledge_base.json     # Chatbot knowledge base
├── courses.json            # Course content
├── templates/              # HTML templates
├── static/                 # CSS, JS, images
└── instance/               # Database files (created automatically)
```

## Technologies Used

- **Flask** - Web framework
- **Flask-SQLAlchemy** - ORM for database
- **Flask-Login** - User session management
- **Flask-WTF** - Forms and CSRF protection
- **spaCy** - NLP for chatbot
- **ReportLab** - PDF generation
- **WTForms** - Form validation

## Troubleshooting

### Issue: Package installation fails

**Solution**: Try installing packages individually:
```bash
pip install Flask Flask-SQLAlchemy Flask-Login Flask-WTF spacy python-dotenv
```

### Issue: Database errors

**Solution**: Delete the `instance` folder and restart the application:
```bash
rm -rf instance  # On Windows: rmdir /s instance
python app.py
```

### Issue: Port already in use

**Solution**: Change the port in `app.py` (last line):
```python
app.run(debug=True, host='0.0.0.0', port=8080)  # Use any available port
```

## Notes

- The secret key in `models.py` should be changed for production use
- Default database is SQLite (stored in `instance/users.db`)
- Debug mode is enabled for development
