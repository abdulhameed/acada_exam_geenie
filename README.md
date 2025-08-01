# 🧞‍♂️ ExamGenie - AI-Powered Exam Management System

[![Django](https://img.shields.io/badge/Django-5.1-green.svg)](https://djangoproject.com/)
[![Python](https://img.shields.io/badge/Python-3.8+-blue.svg)](https://python.org/)
[![License](https://img.shields.io/badge/License-CC0%201.0-lightgrey.svg)](LICENSE)
[![Azure OpenAI](https://img.shields.io/badge/AI-Azure%20OpenAI-orange.svg)](https://azure.microsoft.com/en-us/products/ai-services/openai-service)

> **Revolutionize your exam process with AI-powered question generation, automated grading, and real-time exam administration.**

ExamGenie is a comprehensive examination management platform designed for educational institutions. It leverages artificial intelligence to automate the entire exam lifecycle - from generating questions from course materials to providing detailed analytics on student performance.

## 🌟 Key Features

### 🎓 **Multi-Tenant School Management**
- **School Isolation**: Each institution operates independently with custom domains
- **Role-Based Access**: School Admin, Head of Department, Lecturer, and Student roles
- **Invitation System**: Streamlined onboarding with email-based invitations
- **Department Management**: Organize users by academic departments

### 🤖 **AI-Powered Question Generation**
- **Intelligent Content Analysis**: Upload PDFs and let AI extract meaningful questions
- **Mixed Question Types**: Support for Multiple Choice Questions (MCQ) and Essay questions
- **Difficulty Scaling**: Generate Easy, Medium, or Hard questions based on requirements
- **Unique Questions**: Option to generate different questions for each student
- **Azure OpenAI Integration**: Powered by GPT-3.5-turbo for high-quality question generation

### 📝 **Advanced Exam Administration**
- **Real-Time Exam Rooms**: WebSocket-powered live exam environments
- **Automated Scheduling**: Exams start and end automatically based on configured times
- **Live Monitoring**: Track student progress in real-time
- **Late Entry Prevention**: Configurable deadlines to maintain exam integrity
- **Auto-Save**: Student answers are saved automatically as they type

### 📊 **Intelligent Grading & Analytics**
- **AI Grading**: Automated evaluation of both MCQ and essay responses
- **Performance Analytics**: Detailed insights into student and course performance
- **Grade Management**: Review and adjust AI-generated grades before publishing
- **Export Capabilities**: Generate reports for institutional records

### 🔐 **Security & Compliance**
- **Secure Authentication**: Django's robust authentication system
- **Session Management**: Secure exam sessions with timeout handling
- **CAPTCHA Protection**: Prevent automated registrations
- **Data Isolation**: Complete separation between different schools

## 🛠️ Technology Stack

### Backend
- **Framework**: Django 5.1 + Django REST Framework
- **Database**: SQLite3 (Production: PostgreSQL/MySQL)
- **AI Processing**: Azure OpenAI API + LangChain
- **Real-time Communication**: Django Channels (WebSockets)
- **Background Tasks**: Celery + Redis
- **Email Service**: SMTP with Zoho Mail

### Frontend
- **Templates**: Django Templates
- **Styling**: Halfmoon CSS + Bootstrap 5
- **Icons**: Font Awesome 6
- **JavaScript**: Vanilla JS + jQuery
- **Real-time Updates**: WebSocket connections

### DevOps & Deployment
- **Static Files**: WhiteNoise (Production)
- **Environment Management**: python-decouple
- **Task Queue**: Redis
- **File Processing**: PyPDF for document parsing

## 🚀 Quick Start

### Prerequisites
- Python 3.8+
- Redis Server
- Azure OpenAI API access

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/yourusername/exam_geenie.git
   cd exam_geenie
   ```

2. **Create virtual environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

3. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

4. **Environment Configuration**
   Create a `.env` file in the project root:
   ```env
   SECRET_KEY=your-django-secret-key
   DEBUG=True
   ALLOWED_HOSTS=localhost,127.0.0.1
   
   # Azure OpenAI Configuration
   AZURE_OPENAI_API_KEY=your-azure-openai-key
   AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com/
   
   # Email Configuration
   EMAIL_HOST_USER=your-email@domain.com
   EMAIL_HOST_PASSWORD=your-email-password
   ```

5. **Database Setup**
   ```bash
   python manage.py makemigrations
   python manage.py migrate
   python manage.py createsuperuser
   ```

6. **Start Redis Server**
   ```bash
   redis-server
   ```

7. **Run Celery Worker** (In a new terminal)
   ```bash
   celery -A exam_geenie worker --loglevel=info
   ```

8. **Start Development Server**
   ```bash
   python manage.py runserver
   ```

Visit `http://localhost:8000` to access the application.

## 📖 Usage Guide

### For School Administrators

1. **School Setup**
   - Visit the homepage and click "Get Started"
   - Fill in school details and create admin account
   - Verify email and complete setup

2. **User Management**
   - Navigate to school management dashboard
   - Invite lecturers, HODs, and staff via email
   - Monitor user activity and permissions

### For Lecturers

1. **Course Management**
   - Create courses with detailed descriptions
   - Upload course materials (PDF format)
   - Assign students to courses

2. **Exam Creation**
   - Create new exams with custom parameters
   - Choose question types (MCQ/Essay) and difficulty
   - Generate questions automatically from course materials
   - Review and edit AI-generated questions

3. **Exam Administration**
   - Monitor real-time exam progress
   - Handle student queries during exams
   - Review and adjust grades post-exam

### For Students

1. **Course Registration**
   - Register for available courses
   - Access course materials
   - Track upcoming exams

2. **Taking Exams**
   - Enter exam lobby before exam time
   - Take exams in real-time monitored environment
   - Submit answers with automatic saving

## 🔧 Configuration

### AI Configuration
Configure Azure OpenAI settings in `settings.py`:
```python
AZURE_OPENAI_API_KEY = config('AZURE_OPENAI_API_KEY')
AZURE_OPENAI_ENDPOINT = config('AZURE_OPENAI_ENDPOINT')
```

### Email Configuration
Set up email delivery for notifications:
```python
EMAIL_BACKEND = 'django.core.mail.backends.smtp.EmailBackend'
EMAIL_HOST = 'smtp.zoho.com'
EMAIL_USE_TLS = True
EMAIL_PORT = 587
EMAIL_HOST_USER = config('EMAIL_HOST_USER')
EMAIL_HOST_PASSWORD = config('EMAIL_HOST_PASSWORD')
```

### Celery Configuration
Configure background task processing:
```python
CELERY_BROKER_URL = 'redis://localhost:6379/0'
CELERY_RESULT_BACKEND = 'redis://localhost:6379/0'
```

## 🚀 Deployment

### Azure App Service Deployment

1. **Prepare for Production**
   ```bash
   pip freeze > requirements.txt
   python manage.py collectstatic --noinput
   ```

2. **Configure Production Settings**
   Set environment variables:
   - `DEBUG=False`
   - `ALLOWED_HOSTS=your-domain.com`
   - Database configuration
   - Azure OpenAI credentials

3. **Deploy to Azure**
   - Use Azure CLI or GitHub Actions
   - Configure static files with WhiteNoise
   - Set up Redis for production

### Docker Deployment (Optional)
```dockerfile
FROM python:3.9
WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]
```

## 📚 API Documentation

### Authentication Endpoints
- `POST /login/` - User authentication
- `POST /logout/` - User logout
- `POST /register/` - New user registration

### Exam Management
- `GET /api/exams/` - List exams
- `POST /api/exams/` - Create exam
- `GET /api/exam-content/{exam_id}/` - Get exam questions
- `POST /api/save-answer/{exam_id}/` - Save student answer

### WebSocket Endpoints
- `/ws/exam/{exam_id}/` - Real-time exam communication
- `/ws/exam_lobby/` - Exam lobby updates

## 🧪 Testing

Run the test suite:
```bash
python manage.py test
```

For specific app testing:
```bash
python manage.py test exams
python manage.py test users
python manage.py test courses
```

## 🤝 Contributing

We welcome contributions! Please follow these steps:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit changes (`git commit -m 'Add amazing feature'`)
4. Push to branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

### Development Guidelines
- Follow PEP 8 style guidelines
- Write comprehensive tests for new features
- Update documentation for API changes
- Use meaningful commit messages

## 📋 Project Structure

```
exam_geenie/
├── exam_geenie/          # Main project settings
├── users/                # User management & authentication
├── schools/              # Multi-tenant school management
├── courses/              # Course and content management
├── exams/                # Exam creation and administration
├── analytics/            # Performance analytics
├── notifications/        # Notification system
├── core/                 # Shared utilities and base templates
├── static/               # CSS, JS, and media files
├── templates/            # HTML templates
└── requirements.txt      # Python dependencies
```

## 🐛 Troubleshooting

### Common Issues

**Q: AI question generation is failing**
- Verify Azure OpenAI API credentials
- Check API quota and limits
- Ensure PDF files are readable

**Q: WebSocket connections not working**
- Confirm Redis is running
- Check firewall settings
- Verify ASGI configuration

**Q: Email notifications not sending**
- Validate SMTP settings
- Check email provider security settings
- Verify Celery worker is running

**Q: Static files not loading in production**
- Run `python manage.py collectstatic`
- Check WhiteNoise configuration
- Verify STATIC_ROOT setting

## 📄 License

This project is licensed under the CC0 1.0 Universal License - see the [LICENSE](LICENSE) file for details.

## 🙏 Acknowledgments

- Azure OpenAI for AI capabilities
- Django community for the robust framework
- Bootstrap and Halfmoon for UI components
- All contributors and testers

## 📞 Support

For support and questions:
- Create an issue on GitHub
- Email: support@examgenie.com
- Documentation: [Wiki](https://github.com/yourusername/exam_geenie/wiki)

---

**Built with ❤️ for the education community**

*ExamGenie - Where AI meets Education*

