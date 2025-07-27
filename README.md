# exam_geenie
An AI-powered exam management system built with Django and LangChain, enabling university lecturers to generate, conduct, mark, and disseminate exams automatically from class notes.


# AI Exam Management System

## Overview

The AI Exam Management System is designed to assist university lecturers in automating the process of setting, conducting, marking, and disseminating exams. By leveraging AI language models, this application allows lecturers to upload class notes in PDF format, automatically generate exam questions, and grade students' responses. 

## Features

- **PDF Upload**: Lecturers can upload class notes in PDF format.
- **AI-Generated Exam Questions**: Automatically generate exam questions from the uploaded PDFs using AI language models.
- **Customizable Exam Settings**: Lecturers can choose the number of questions, their difficulty, and whether all students get the same or unique questions.
- **Student Authentication**: Students can log in with their student ID and password to take the exams.
- **AI Grading**: AI grades the students' responses, with options for lecturers to review and adjust grades before dissemination.
- **Multiple LLM Support**: The system supports the use of different language models, allowing for cost-effectiveness analysis.

## Tech Stack

- **Backend**: Django, Django REST Framework
- **AI Integration**: LangChain
- **Database**: PostgreSQL or MySQL
- **Frontend**: Django Templates, Bootstrap (or any preferred front-end framework)
- **Authentication**: Django's built-in authentication system

## Project Setup

1. **Clone the repository:**
   ```bash
   git clone https://github.com/abdulhameed/exam_geenie.git
