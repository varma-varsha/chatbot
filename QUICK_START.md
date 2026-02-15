# OneLearn - Quick Start Guide

## ✅ All Dependencies Successfully Installed!

Your OneLearn project is now ready to run. Here's what was installed:

## What's Installed

- ✅ Flask and Flask extensions (SQLAlchemy, Login, WTF, CSRF)
- ✅ spaCy and NLP dependencies (pre-built wheels for Windows)
- ✅ All required packages

## Running the Application

### Step 1: Start the Server

Open PowerShell in the project directory and run:

```powershell
python app.py
```

### Step 2: Access the Application

Open your web browser and navigate to:

```
http://localhost:5000
```

### Step 3: Create an Account

1. Click "Sign Up" on the homepage
2. Fill in your details (username, email, password)
3. Log in with your credentials
4. Start exploring the learning platform!

## Key Features

- 🎓 Interactive Learning Platform
- 💬 AI-Powered Chatbot with spaCy NLP
- 📚 Multiple Programming Language Courses
- 📊 Progress Tracking
- 🔒 Secure User Authentication

## Troubleshooting

### Port 5000 Already in Use?

If you get an error about port 5000 being in use:

1. Close any other Flask applications
2. Or modify `app.py` (last line) to use a different port:
   ```python
   app.run(debug=True, host='0.0.0.0', port=8080)
   ```

### Database Issues?

If you encounter database errors:

```powershell
Remove-Item -Recurse -Force instance
python app.py
```

This will reset the database.

## Installation Summary

The following packages were successfully installed:

- **Flask** - Web framework
- **Flask-SQLAlchemy** - Database ORM
- **Flask-Login** - User authentication
- **Flask-WTF** - Forms and CSRF protection
- **spaCy** - NLP for chatbot
- **NumPy** - Numerical computing
- **Thinc** - Machine learning library
- **And many other dependencies...**

## Need Help?

Check the following files for more information:
- `README.md` - Full documentation
- `SETUP_INSTRUCTIONS.txt` - Basic setup guide

## Success! 🎉

Your OneLearn platform is now running and ready to use!
