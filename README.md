# Job Recommender System

A Django-based web application designed to recommend jobs to employees and candidates to employers based on compatibility scores. The application provides features for employers to post jobs, employees to apply for jobs, and view compatibility scores and reports.

---

## Table of Contents

- [Features](#features)
- [Technologies Used](#technologies-used)
- [Installation](#installation)
- [File Structure](#file-structure)
- [Usage](#usage)

---

## Features

### For Employers:
- Register as an employer and manage your profile.
- Post job listings with detailed requirements.
- Upload CSV files for bulk job applications.
- View job applications and compatibility reports for applicants.

### For Employees:
- Register as an employee and manage your profile.
- Apply for jobs by uploading a resume (PDF or DOCX format).
- View compatibility scores for job recommendations.

### General Features:
- Compatibility analysis based on predefined metrics.
- Dynamic visualization of compatibility reports using charts.
- Support for uploading resumes and CSV files.

---

## Technologies Used

- **Backend**: Django, Python
- **Frontend**: HTML, CSS, JavaScript
- **Database**: SQLite
- **Visualization**: Matplotlib, Seaborn
- **Hosting**: Localhost (development), compatible with cloud platforms

---

## Installation

### Prerequisites:
1. Python (>=3.8 <= 3.12)
2. Django (>=4.0)
3. Virtualenv (recommended)
4. Install Visual Studio Build Tools https://visualstudio.microsoft.com/


and add these paths , for eg refer

C:\Program Files\Microsoft Visual Studio\2022\Community\VC\Tools\MSVC\14.43.34808\bin\Hostx64\x64

C:\Program Files (x86)\Windows Kits\10\bin\x64

C:\Program Files\Microsoft Visual Studio\2022\Community\MSBuild\Current\Bin

### Steps:

1. Clone the repository:
   ```bash
   git clone <repository_url>
   cd job_recommender
2. Create a virtual environment and activate it:
   python -m venv venv
   
   #On Windows: venv\Scripts\activate
   
   #On Mac: source venv/bin/activate

3. Install dependencies: pip install -r requirements.txt
4.  Install Tesseract OCR
If you haven't installed Tesseract OCR itself, you'll need to do that first. pytesseract is just a wrapper and requires the actual Tesseract software to function.

For Windows:
Download the Tesseract executable from this link.
https://github.com/UB-Mannheim/tesseract/wiki

Install it and note the installation directory (e.g., C:\Program Files\Tesseract-OCR).

For macOS:
You can install Tesseract using Homebrew with the following command:

bash

brew install tesseract
For Linux:
You can install Tesseract using the package manager. For example, on Ubuntu:
bash

sudo apt update
sudo apt install tesseract-ocr
2. Add Tesseract to PATH
Once Tesseract is installed, you need to ensure it's in your system's PATH so that pytesseract can find it.

For Windows:
You can add Tesseract to your PATH manually:

Right-click on 'This PC' or 'My Computer' and select 'Properties'.

Click on 'Advanced system settings' and then 'Environment Variables'.

In the 'System variables' section, find the 'Path' variable and click 'Edit'.

Add the path to your Tesseract installation (e.g., C:\Program Files\Tesseract-OCR).

Click 'OK' to close all dialogs.

For macOS and Linux:
Generally, if installed via Homebrew or package manager, it should automatically be added to your PATH. You can verify by running tesseract --version in the terminal.

3. Configure pytesseract in Django
In your Django application, ensure that pytesseract is configured to find the Tesseract executable. You might need to explicitly set the path in your Django settings or wherever you're using pytesseract.

For example, you can specify the path in your Python code like this:

python

import pytesseract
pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'  # Update this path as per your installation

5. Apply database migrations:
   python manage.py makemigrations
python manage.py migrate

   
6. Run the development server: python manage.py runserver
   
8. Access the application at http://127.0.0.1:8000/

## File Structure
job_recommender/
├── job_recommender/
│   ├── __init__.py
│   ├── asgi.py
│   ├── settings.py
│   ├── settings_secret.py
│   ├── urls.py
│   ├── wsgi.py
├── main/
│   ├── __init__.py
│   ├── admin.py
│   ├── apps.py
│   ├── decorators.py
│   ├── forms.py
│   ├── helpers.py
│   ├── models.py
│   ├── signals.py
│   ├── tests.py
│   ├── urls.py
│   ├── utils.py
│   ├── views.py
│   ├── migrations/
│   ├── templates/
│   │   ├── base.html
│   │   ├── main/
│   │       ├── add_job.html
│   │       ├── employee_dashboard.html
│   │       ├── view_jobs.html
│   │       ├── ... (other templates)
│   ├── static/
│   │   ├── reports/
│   │       ├── clustered_bar_chart_*.png
│   │       ├── ...
├── media/
│   ├── resumes/
├── reports/
│   ├── compatibility_heatmap.png
│   ├── compatibility_report.csv
├── db.sqlite3
├── manage.py
├── .gitignore

## Key Directories and Files:
- **job_recommender/**: Project settings and configurations.
- **main/**: Contains app-specific logic, models, forms, views, and templates.
- **static/**: Static assets like images and CSS files.
- **media/**: Uploaded files like resumes.
- **reports/**: Generated reports for compatibility analysis.
- **db.sqlite3**: Development database file.

---

## Usage

### Register Users:
Employers and employees can register and set up profiles.

### Post Jobs:
Employers can post jobs and manage applications.

### Apply for Jobs:
Employees can view jobs and apply with their resumes.

### View Compatibility Reports:
Both employers and employees can analyze compatibility scores through dynamic visualizations.



