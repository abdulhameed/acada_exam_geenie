from langchain_community.llms import OpenAI, Anthropic
# from langchain_community.document_loaders import PyPDFLoader
from langchain_community.document_loaders import PyPDFLoader
from langchain.text_splitter import CharacterTextSplitter
from langchain.prompts import PromptTemplate
from langchain.chains import LLMChain
from django.conf import settings
from .models import Question, Exam
from courses.models import CourseContent
import logging

logger = logging.getLogger(__name__)


def get_ai_model():
    if settings.AI_PROVIDER == 'openai':
        return OpenAI(openai_api_key=settings.OPENAI_API_KEY)
    elif settings.AI_PROVIDER == 'anthropic':
        return Anthropic(anthropic_api_key=settings.ANTHROPIC_API_KEY)
    else:
        raise ValueError(f"Invalid AI provider: {settings.AI_PROVIDER}")


def generate_exam_questions(exam_id):
    logger.info(f"Starting question generation for exam {exam_id}")
    exam = Exam.objects.get(id=exam_id)
    course_contents = CourseContent.objects.filter(course=exam.course)

    logger.info(f"Found {len(course_contents)} course contents for exam {exam_id}")

    # Load and process all PDFs
    all_texts = []
    for content in course_contents:
        loader = PyPDFLoader(content.pdf_file.path)
        pages = loader.load_and_split()
        text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
        all_texts.extend(text_splitter.split_documents(pages))

    # Initialize language model
    llm = get_ai_model()

    # Create prompt template
    prompt_template = """
    Based on the following course content, generate {num_questions} {difficulty} exam questions:

    Content: {content}

    Generate {num_questions} {difficulty} exam questions:
    """

    prompt = PromptTemplate(template=prompt_template, input_variables=["num_questions", "difficulty", "content"])

    # Create chain
    chain = LLMChain(llm=llm, prompt=prompt)

    # Generate questions
    questions_to_generate = exam.number_of_questions
    questions_per_chunk = min(5, questions_to_generate)  # Generate up to 5 questions per chunk

    for chunk in all_texts:
        if questions_to_generate <= 0:
            break

        logger.info(f"Generating questions for chunk in exam {exam_id}")
        response = chain.run(content=chunk.page_content, num_questions=questions_per_chunk, difficulty=exam.difficulty)

        # Process and save questions
        new_questions = response.split('\n')
        for question in new_questions:
            if question.strip() and questions_to_generate > 0:
                Question.objects.create(
                    exam=exam,
                    text=question.strip(),
                    difficulty=exam.difficulty
                )
                questions_to_generate -= 1
                logger.info(f"Created question for exam {exam_id}. Remaining: {questions_to_generate}")

    logger.info(f"Completed question generation for exam {exam_id}")
    return f"Generated {exam.number_of_questions} questions for exam {exam.title} using {settings.AI_PROVIDER}"
