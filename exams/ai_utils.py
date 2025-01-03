# from langchain_community.llms import OpenAI, Anthropic
# from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from django.conf import settings
# import openai
from openai import AzureOpenAI
from .models import MCQOption, Question, Exam, Answer, StudentExam, Result
from courses.models import CourseContent
import logging
import re
from decouple import config

logger = logging.getLogger(__name__)


api_key = None
# Configure Azure OpenAI
api_key = settings.AZURE_OPENAI_API_KEY
api_base = settings.AZURE_OPENAI_ENDPOINT
api_version = "2024-02-01"

# Deployment name
deployment_name = 'gpt-35-turbo-instruct-0914'


def generate_exam_questions(exam_id):
    logger.info(f"Starting question generation for exam {exam_id}")
    exam = Exam.objects.get(id=exam_id)
    course_contents = CourseContent.objects.filter(course=exam.course)

    logger.info(f"Found {len(course_contents)} course contents for exam {exam_id}")

    # Calculate target number of questions to generate
    # If unique_questions is True, generate 3x the required questions
    multiplier = 3 if exam.unique_questions else 1
    target_mcq = exam.mcq_questions * multiplier
    target_essay = exam.essay_questions * multiplier

    # Load and process all PDFs
    all_texts = []
    for content in course_contents:
        loader = PyPDFLoader(content.pdf_file.path)
        pages = loader.load_and_split()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        all_texts.extend(text_splitter.split_documents(pages))

    # Track successfully generated questions
    generated_mcq = 0
    generated_essay = 0
    current_question_number = 1

    for chunk in all_texts:
        client = AzureOpenAI(
            api_key=api_key,
            api_version=api_version,
            azure_endpoint=api_base
        )

        # Generate MCQ questions
        if exam.mcq_questions > 0:
            questions_per_chunk = min(3, target_mcq - generated_mcq)  # Limit per chunk but not overall
            
            mcq_prompt = f"""
            Based on the following course content, generate {questions_per_chunk} {exam.difficulty} multiple choice questions.
            For each question, provide exactly 4 options (a, b, c, d) and indicate the correct answer.
            
            Format each question as follows:
            Question: [Question text]
            a) [Option a]
            b) [Option b]
            c) [Option c]
            d) [Option d]
            Correct: [a/b/c/d]

            Content: {chunk.page_content}
            """

            try:
                response = client.completions.create(
                    model=deployment_name,
                    prompt=mcq_prompt,
                    max_tokens=1000,
                    temperature=0.7,
                    top_p=1,
                    n=1
                )

                generated_text = response.choices[0].text.strip() if hasattr(response.choices[0], 'text') else ''

                if generated_text:
                    mcq_questions = generated_text.split('\nQuestion: ')
                    mcq_questions = [q.strip() for q in mcq_questions if q.strip()]

                    for mcq in mcq_questions:
                        try:
                            # Split question into components
                            lines = mcq.split('\n')
                            question_text = lines[0].replace('Question: ', '').strip()
                            options = [line.strip() for line in lines[1:5]]
                            correct_line = next((line for line in lines if line.startswith('Correct:')), '')
                            correct_answer = correct_line.replace('Correct:', '').strip().lower()

                            # Create the main question
                            question = Question.objects.create(
                                exam=exam,
                                order=str(current_question_number),
                                question_type='MCQ',
                                text=question_text,
                                difficulty=exam.difficulty
                            )

                            # Create options
                            for i, option_text in enumerate(options):
                                option_letter = option_text[0].lower()
                                option_content = option_text[3:].strip()  # Remove "a) ", "b) ", etc.
                                
                                MCQOption.objects.create(
                                    question=question,
                                    text=option_content,
                                    order=option_letter,
                                    is_correct=(option_letter == correct_answer)
                                )

                            generated_mcq += 1
                            current_question_number += 1
                            logger.info(f"Created MCQ question for exam {exam_id}. Created: {generated_mcq}/{target_mcq}")

                        except Exception as e:
                            logger.error(f"Error processing individual MCQ: {str(e)}")
                            continue

            except Exception as e:
                logger.error(f"Error generating MCQ questions for exam {exam_id}: {str(e)}")
                continue

        # Generate essay questions
        if exam.essay_questions > 0:
            questions_per_chunk = min(3, target_essay - generated_essay)  # Limit per chunk but not overall
            
            essay_prompt = f"""
            Based on the following course content, generate {questions_per_chunk} {exam.difficulty} essay questions 
            that require detailed explanations and critical thinking.
            
            Content: {chunk.page_content}
            """

            try:
                response = client.completions.create(
                    model=deployment_name,
                    prompt=essay_prompt,
                    max_tokens=500,
                    temperature=0.7,
                    top_p=1,
                    n=1
                )

                generated_text = response.choices[0].text.strip() if hasattr(response.choices[0], 'text') else ''

                if generated_text:
                    essay_questions = generated_text.split('\n')
                    essay_questions = [q.strip() for q in essay_questions if q.strip()]

                    for question in essay_questions:
                        # Clean up numbering or formatting
                        cleaned_question = re.sub(r'^(\d+\.?\s*|Q\d+\.?\s*|Question\s+\d+\.?\s*)', '', question, flags=re.IGNORECASE).strip()
                        
                        if cleaned_question:
                            Question.objects.create(
                                exam=exam,
                                order=str(current_question_number),
                                question_type='ESSAY',
                                text=cleaned_question,
                                difficulty=exam.difficulty
                            )
                            generated_essay += 1
                            current_question_number += 1
                            logger.info(f"Created essay question for exam {exam_id}. Created: {generated_essay}/{target_essay}")

            except Exception as e:
                logger.error(f"Error generating essay questions for exam {exam_id}: {str(e)}")
                continue

    logger.info(f"Completed question generation for exam {exam_id}")
    status_message = (
        f"Generated {generated_mcq} MCQ and {generated_essay} Essay questions for exam {exam.title}. "
        f"{'(Unique questions enabled - generated extra questions)' if exam.unique_questions else ''}"
    )
    return status_message


# def generate_exam_questions(exam_id):
#     logger.info(f"Starting question generation for exam {exam_id}")
#     exam = Exam.objects.get(id=exam_id)
#     course_contents = CourseContent.objects.filter(course=exam.course)

#     logger.info(f"Found {len(course_contents)} course contents for exam {exam_id}")

#     # Load and process all PDFs
#     all_texts = []
#     for content in course_contents:
#         loader = PyPDFLoader(content.pdf_file.path)
#         pages = loader.load_and_split()
#         text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
#         all_texts.extend(text_splitter.split_documents(pages))

#     # Initialize AI generation variables
#     questions_to_generate = exam.number_of_questions
#     questions_per_chunk = min(5, questions_to_generate)  # Generate up to 5 questions per chunk

#     for chunk in all_texts:
#         if questions_to_generate <= 0:
#             break

#         logger.info(f"Generating questions for chunk in exam {exam_id}")

#         client = AzureOpenAI(
#             api_key=api_key,
#             api_version=api_version,
#             azure_endpoint=api_base
#             )

#         # Create prompt for current chunk
#         prompt = f"""
#         Based on the following course content, generate {questions_per_chunk} {exam.difficulty} exam questions:

#         Content: {chunk.page_content}

#         Generate {questions_per_chunk} {exam.difficulty} exam questions:
#         """

#         # Call Azure OpenAI API
#         try:
#             response = client.completions.create(
#                 model=deployment_name,
#                 prompt=prompt,
#                 max_tokens=500,
#                 temperature=0.7,
#                 top_p=1,
#                 n=1
#             )

#             # Safely extract the generated text
#             if hasattr(response, 'choices') and response.choices:
#                 generated_text = response.choices[0].text.strip() if hasattr(response.choices[0], 'text') else ''
#             else:
#                 generated_text = ''

#             # generated_text = response.choices[0].text.strip()
#             # new_questions = generated_text.split('\n')

#             # Process and save questions
#             if generated_text:
#                 new_questions = generated_text.split('\n')
#                 new_questions = [q.strip() for q in new_questions if q.strip()]

#                 for question in new_questions:
#                     if question and questions_to_generate > 0:
#                         # Clean up numbering or formatting
#                         cleaned_question = re.sub(r'^(\d+\.?\s*|Q\d+\.?\s*|Question\s+\d+\.?\s*)', '', question, flags=re.IGNORECASE).strip()
                        
#                         if cleaned_question:
#                             Question.objects.create(
#                                 exam=exam,
#                                 text=cleaned_question,
#                                 difficulty=exam.difficulty
#                             )
#                             questions_to_generate -= 1
#                             logger.info(f"Created question for exam {exam_id}. Remaining: {questions_to_generate}")

#         except Exception as e:
#             logger.error(f"Error generating questions for exam {exam_id}: {str(e)}")
#             continue

#     logger.info(f"Completed question generation for exam {exam_id}")
#     return f"Generated {exam.number_of_questions - questions_to_generate} questions for exam {exam.title} using Azure OpenAI"


# def get_ai_model():
#     if settings.AI_PROVIDER == 'openai':
#         return OpenAI(openai_api_key=settings.OPENAI_API_KEY)
#     elif settings.AI_PROVIDER == 'anthropic':
#         return Anthropic(anthropic_api_key=settings.ANTHROPIC_API_KEY)
#     elif settings.AI_PROVIDER == 'gemini':
#         return Gemini(api_key=settings.GEMINI_API_KEY)
#     else:
#         raise ValueError(f"Invalid AI provider: {settings.AI_PROVIDER}")


# def generate_exam_questions(exam_id):
#     logger.info(f"Starting question generation for exam {exam_id}")
#     exam = Exam.objects.get(id=exam_id)
#     course_contents = CourseContent.objects.filter(course=exam.course)

#     logger.info(f"Found {len(course_contents)} course contents for exam {exam_id}")

#     # Load and process all PDFs
#     all_texts = []
#     for content in course_contents:
#         loader = PyPDFLoader(content.pdf_file.path)
#         pages = loader.load_and_split()
#         text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
#         all_texts.extend(text_splitter.split_documents(pages))

#     # Initialize language model
#     llm = get_ai_model()

#     # Create prompt template
#     prompt_template = """
#     Based on the following course content, generate {num_questions} {difficulty} exam questions:

#     Content: {content}

#     Generate {num_questions} {difficulty} exam questions:
#     """

#     prompt = PromptTemplate(template=prompt_template, input_variables=["num_questions", "difficulty", "content"])

#     # Create chain
#     chain = LLMChain(llm=llm, prompt=prompt)

#     # Generate questions
#     questions_to_generate = exam.number_of_questions
#     questions_per_chunk = min(5, questions_to_generate)  # Generate up to 5 questions per chunk

#     for chunk in all_texts:
#         if questions_to_generate <= 0:
#             break

#         logger.info(f"Generating questions for chunk in exam {exam_id}")
#         response = chain.run(content=chunk.page_content, num_questions=questions_per_chunk, difficulty=exam.difficulty)

#         # Process and save questions
#         new_questions = response.split('\n')
#         for question in new_questions:
#             if question.strip() and questions_to_generate > 0:

#                 question = re.sub(r'^(\d+\.?\s*|Q\d+\.?\s*|Question\s+\d+\.?\s*)', '', question, flags=re.IGNORECASE)
#                 Question.objects.create(
#                     exam=exam,
#                     text=question.strip(),
#                     difficulty=exam.difficulty
#                 )
#                 questions_to_generate -= 1
#                 logger.info(f"Created question for exam {exam_id}. Remaining: {questions_to_generate}")

#     logger.info(f"Completed question generation for exam {exam_id}")
#     return f"Generated {exam.number_of_questions} questions for exam {exam.title} using {settings.AI_PROVIDER}"


def grade_exam_answer(answer_id):
    logger.info(f"Starting grading for answer {answer_id}")
    answer = Answer.objects.get(id=answer_id)

    llm = get_ai_model()

    prompt_template = """
    Question: {question}
    Student Answer: {student_answer}

    Please grade the above answer on a scale of 0-100 and provide brief feedback.
    Format your response as follows:
    Grade: [numerical grade]
    Feedback: [your feedback here]
    """

    prompt = PromptTemplate(template=prompt_template, input_variables=["question", "student_answer"])
    chain = LLMChain(llm=llm, prompt=prompt)

    response = chain.run(question=answer.question.text, student_answer=answer.text)

    # Process the response
    grade_line, feedback_line = response.strip().split('\n')
    grade = float(grade_line.split(':')[1].strip())
    feedback = feedback_line.split(':')[1].strip()

    # Update the answer
    answer.grade = grade
    answer.ai_feedback = feedback
    answer.save()

    logger.info(f"Completed grading for answer {answer_id}")
    return grade, feedback


def grade_student_exam(student_exam_id):
    logger.info(f"Starting grading for student exam {student_exam_id}")
    student_exam = StudentExam.objects.get(id=student_exam_id)

    total_grade = 0
    number_of_questions = student_exam.answers.count()

    for answer in student_exam.answers.all():
        grade, _ = grade_exam_answer(answer.id)
        total_grade += grade

    average_grade = total_grade / number_of_questions if number_of_questions > 0 else 0

    # Create or update the Result
    result, created = Result.objects.update_or_create(
        student_exam=student_exam,
        defaults={
            'total_grade': average_grade,
            'status': 'pending_review'
        }
    )

    logger.info(f"Completed grading for student exam {student_exam_id}")
    return result


def process_completed_exams():
    logger.info("Starting processing of completed exams")
    completed_exams = StudentExam.objects.filter(status='completed', result__isnull=True)

    for student_exam in completed_exams:
        grade_student_exam(student_exam.id)

    logger.info(f"Processed {completed_exams.count()} completed exams")
