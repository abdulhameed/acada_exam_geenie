"""
Enhanced AI question generation using expert questions as templates
Create this file at: exams/enhanced_ai_utils.py
"""

import logging
import re
import random
from typing import List, Dict, Tuple, Optional
from django.conf import settings
from django.db.models import Q
from openai import AzureOpenAI

from .models import Question, Exam, MCQOption
from courses.models import ExpertQuestion, EnhancedCourseContent, QuestionGenerationTemplate
from courses.content_processors import ContentProcessor

logger = logging.getLogger(__name__)


class EnhancedQuestionGenerator:
    """Enhanced question generator that uses expert questions as templates"""
    
    def __init__(self):
        self.client = AzureOpenAI(
            api_key=settings.AZURE_OPENAI_API_KEY,
            api_version="2024-02-01",
            azure_endpoint=settings.AZURE_OPENAI_ENDPOINT
        )
        self.deployment_name = 'gpt-35-turbo-instruct-0914'
    
    def generate_exam_questions(self, exam_id: int) -> str:
        """
        Enhanced exam question generation using expert questions as templates
        """
        logger.info(f"Starting enhanced question generation for exam {exam_id}")
        
        try:
            exam = Exam.objects.get(id=exam_id)
            
            # Get course content
            course_contents = self._get_course_content(exam.course)
            if not course_contents:
                return "No course content found for question generation"
            
            # Get expert questions for templates
            expert_questions = self._get_expert_questions(exam)
            
            # Get or create generation template
            generation_template = self._get_generation_template(exam)
            
            # Calculate target questions
            multiplier = 3 if exam.unique_questions else 1
            target_mcq = exam.mcq_questions * multiplier
            target_essay = exam.essay_questions * multiplier
            
            generated_mcq = 0
            generated_essay = 0
            
            # Process each content chunk
            for content in course_contents:
                if generated_mcq >= target_mcq and generated_essay >= target_essay:
                    break
                
                # Generate MCQ questions if needed
                if generated_mcq < target_mcq:
                    mcq_count = self._generate_mcq_questions(
                        exam, content, expert_questions, generation_template,
                        target_count=min(3, target_mcq - generated_mcq)
                    )
                    generated_mcq += mcq_count
                
                # Generate Essay questions if needed
                if generated_essay < target_essay:
                    essay_count = self._generate_essay_questions(
                        exam, content, expert_questions, generation_template,
                        target_count=min(2, target_essay - generated_essay)
                    )
                    generated_essay += essay_count
            
            total_generated = generated_mcq + generated_essay
            status_message = (
                f"Generated {total_generated} questions for exam {exam.title}:\n"
                f"- MCQ: {generated_mcq}/{target_mcq}\n"
                f"- Essay: {generated_essay}/{target_essay}\n"
                f"{'(Using expert question templates)' if expert_questions else '(No expert templates available)'}"
            )
            
            logger.info(status_message)
            return status_message
            
        except Exception as e:
            error_msg = f"Error generating questions for exam {exam_id}: {str(e)}"
            logger.error(error_msg, exc_info=True)
            return error_msg
    
    def _get_course_content(self, course) -> List[str]:
        """Get all processed course content"""
        content_list = []
        
        # Get enhanced course content (multiple formats)
        enhanced_contents = EnhancedCourseContent.objects.filter(
            course=course, 
            is_processed=True,
            processing_status='completed'
        )
        
        for content in enhanced_contents:
            if content.extracted_text:
                content_list.append(content.extracted_text)
        
        # Fallback to original PDF content if no enhanced content
        if not content_list:
            from courses.models import CourseContent
            from langchain_community.document_loaders import PyPDFLoader
            from langchain.text_splitter import CharacterTextSplitter
            
            course_contents = CourseContent.objects.filter(course=course)
            for content in course_contents:
                try:
                    loader = PyPDFLoader(content.pdf_file.path)
                    pages = loader.load_and_split()
                    text_splitter = CharacterTextSplitter(chunk_size=1000, chunk_overlap=0)
                    docs = text_splitter.split_documents(pages)
                    content_list.extend([doc.page_content for doc in docs])
                except Exception as e:
                    logger.warning(f"Error processing PDF {content.title}: {str(e)}")
        
        return content_list
    
    def _get_expert_questions(self, exam) -> List[ExpertQuestion]:
        """Get relevant expert questions for the exam"""
        # Try to find expert questions that match the course domain/subject
        course_keywords = [
            exam.course.name.lower(),
            exam.course.code.lower(),
            exam.course.description.lower() if exam.course.description else ''
        ]
        
        # Build query to find relevant expert questions
        query = Q()
        
        # Search by domain
        for keyword in course_keywords:
            if keyword:
                query |= Q(domain__icontains=keyword)
        
        # Filter by question type if needed
        question_types = []
        if exam.mcq_questions > 0:
            question_types.append('MCQ')
        if exam.essay_questions > 0:
            question_types.append('ESSAY')
        
        if question_types:
            query &= Q(question_type__in=question_types)
        
        # Get expert questions
        expert_questions = list(ExpertQuestion.objects.filter(query)[:20])
        
        # If no domain-specific questions found, get general questions
        if not expert_questions:
            expert_questions = list(ExpertQuestion.objects.filter(
                question_type__in=question_types
            )[:10])
        
        logger.info(f"Found {len(expert_questions)} expert questions for templates")
        return expert_questions
    
    def _get_generation_template(self, exam) -> Optional[QuestionGenerationTemplate]:
        """Get or create a generation template for the exam"""
        template = QuestionGenerationTemplate.objects.filter(
            course=exam.course,
            is_active=True
        ).first()
        
        if not template:
            # Create default template
            template = QuestionGenerationTemplate.objects.create(
                course=exam.course,
                name=f"Default Template - {exam.course.code}",
                description="Auto-generated template for question generation",
                use_expert_questions=True,
                expert_question_types='MIXED',
                similarity_threshold=0.7,
                max_expert_examples=5,
                created_by=exam.course.lecturer,
                is_active=True
            )
        
        return template
    
    def _generate_mcq_questions(self, exam, content: str, expert_questions: List[ExpertQuestion], 
                               template: QuestionGenerationTemplate, target_count: int) -> int:
        """Generate MCQ questions using expert templates"""
        
        # Filter expert MCQ questions
        mcq_experts = [q for q in expert_questions if q.question_type == 'MCQ']
        
        # Select random examples
        example_questions = random.sample(
            mcq_experts, 
            min(len(mcq_experts), template.max_expert_examples)
        ) if mcq_experts else []
        
        # Build prompt with expert examples
        prompt = self._build_mcq_prompt(
            content, example_questions, exam.difficulty, 
            target_count, template.custom_prompt_prefix
        )
        
        try:
            response = self.client.completions.create(
                model=self.deployment_name,
                prompt=prompt,
                max_tokens=800,
                temperature=0.7,
                top_p=1,
                n=1
            )
            
            generated_text = response.choices[0].text.strip() if response.choices else ""
            
            if generated_text:
                return self._parse_and_save_mcq_questions(exam, generated_text)
            
        except Exception as e:
            logger.error(f"Error generating MCQ questions: {str(e)}")
        
        return 0
    
    def _generate_essay_questions(self, exam, content: str, expert_questions: List[ExpertQuestion], 
                                 template: QuestionGenerationTemplate, target_count: int) -> int:
        """Generate essay questions using expert templates"""
        
        # Filter expert essay questions
        essay_experts = [q for q in expert_questions if q.question_type == 'ESSAY']
        
        # Select random examples
        example_questions = random.sample(
            essay_experts, 
            min(len(essay_experts), template.max_expert_examples)
        ) if essay_experts else []
        
        # Build prompt with expert examples
        prompt = self._build_essay_prompt(
            content, example_questions, exam.difficulty, 
            target_count, template.custom_prompt_prefix
        )
        
        try:
            response = self.client.completions.create(
                model=self.deployment_name,
                prompt=prompt,
                max_tokens=600,
                temperature=0.7,
                top_p=1,
                n=1
            )
            
            generated_text = response.choices[0].text.strip() if response.choices else ""
            
            if generated_text:
                return self._parse_and_save_essay_questions(exam, generated_text)
            
        except Exception as e:
            logger.error(f"Error generating essay questions: {str(e)}")
        
        return 0
    
    def _build_mcq_prompt(self, content: str, example_questions: List[ExpertQuestion], 
                         difficulty: str, target_count: int, custom_prefix: str = "") -> str:
        """Build prompt for MCQ generation with expert examples"""
        
        prompt = f"""You are an expert educator creating high-quality multiple choice questions.

{custom_prefix}

EXPERT QUESTION EXAMPLES:
Here are examples of well-crafted educational questions to guide your style and quality:

"""
        
        # Add expert examples
        for i, expert_q in enumerate(example_questions, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {expert_q.question_text}\n"
            if expert_q.source_material:
                # Truncate source material for brevity
                source_preview = expert_q.source_material[:200] + "..." if len(expert_q.source_material) > 200 else expert_q.source_material
                prompt += f"Based on: {source_preview}\n"
            prompt += "\n"
        
        prompt += f"""
TASK:
Based on the following course content, generate {target_count} {difficulty}-level multiple choice questions.

REQUIREMENTS:
- Follow the style and quality of the expert examples above
- Each question should have exactly 4 options (A, B, C, D)
- Clearly indicate the correct answer
- Questions should test understanding, not just memorization
- Make distractors plausible but clearly incorrect
- Use clear, unambiguous language

COURSE CONTENT:
{content[:1500]}

Generate {target_count} multiple choice questions:

"""
        return prompt
    
    def _build_essay_prompt(self, content: str, example_questions: List[ExpertQuestion], 
                           difficulty: str, target_count: int, custom_prefix: str = "") -> str:
        """Build prompt for essay generation with expert examples"""
        
        prompt = f"""You are an expert educator creating high-quality essay questions.

{custom_prefix}

EXPERT QUESTION EXAMPLES:
Here are examples of well-crafted educational essay questions:

"""
        
        # Add expert examples
        for i, expert_q in enumerate(example_questions, 1):
            prompt += f"Example {i}:\n"
            prompt += f"Question: {expert_q.question_text}\n"
            if expert_q.source_material:
                source_preview = expert_q.source_material[:200] + "..." if len(expert_q.source_material) > 200 else expert_q.source_material
                prompt += f"Based on: {source_preview}\n"
            prompt += "\n"
        
        prompt += f"""
TASK:
Based on the following course content, generate {target_count} {difficulty}-level essay questions.

REQUIREMENTS:
- Follow the style and depth of the expert examples above
- Questions should require critical thinking and analysis
- Encourage detailed explanations and examples
- Should be answerable in 200-500 words
- Test deep understanding of concepts

COURSE CONTENT:
{content[:1500]}

Generate {target_count} essay questions:

"""
        return prompt
    
    def _parse_and_save_mcq_questions(self, exam, generated_text: str) -> int:
        """Parse and save generated MCQ questions"""
        questions = generated_text.split('\n\n')
        saved_count = 0
        
        for question_text in questions:
            question_text = question_text.strip()
            if not question_text:
                continue
            
            try:
                # Parse question and options
                parsed_data = self._parse_mcq_text(question_text)
                if not parsed_data:
                    continue
                
                question_obj = Question.objects.create(
                    exam=exam,
                    order=str(Question.objects.filter(exam=exam).count() + 1),
                    question_text=parsed_data['question'],
                    question_type='MCQ',
                    points=1
                )
                
                # Create options
                for option_data in parsed_data['options']:
                    MCQOption.objects.create(
                        question=question_obj,
                        option_text=option_data['text'],
                        is_correct=option_data['is_correct']
                    )
                
                saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving MCQ question: {str(e)}")
                continue
        
        return saved_count
    
    def _parse_and_save_essay_questions(self, exam, generated_text: str) -> int:
        """Parse and save generated essay questions"""
        questions = generated_text.split('\n\n')
        saved_count = 0
        
        for question_text in questions:
            question_text = question_text.strip()
            if not question_text:
                continue
            
            try:
                # Clean up question text
                question_text = re.sub(r'^(\d+\.?\s*|Q\d+\.?\s*|Question\s+\d+\.?\s*)', '', question_text).strip()
                
                if len(question_text) > 10:  # Minimum question length
                    Question.objects.create(
                        exam=exam,
                        order=str(Question.objects.filter(exam=exam).count() + 1),
                        question_text=question_text,
                        question_type='ESSAY',
                        points=5  # Default essay points
                    )
                    saved_count += 1
                
            except Exception as e:
                logger.error(f"Error saving essay question: {str(e)}")
                continue
        
        return saved_count
    
    def _parse_mcq_text(self, question_text: str) -> Optional[Dict]:
        """Parse MCQ text to extract question and options"""
        try:
            lines = question_text.strip().split('\n')
            
            # Find the main question
            question = ""
            options = []
            correct_answer = None
            
            for i, line in enumerate(lines):
                line = line.strip()
                if not line:
                    continue
                
                # Check if this is an option line
                option_match = re.match(r'^([A-D])[.)]\s*(.+)', line, re.IGNORECASE)
                if option_match:
                    option_letter = option_match.group(1).upper()
                    option_text = option_match.group(2).strip()
                    options.append({
                        'letter': option_letter,
                        'text': option_text,
                        'is_correct': False
                    })
                elif 'correct answer' in line.lower() or 'answer:' in line.lower():
                    # Extract correct answer
                    answer_match = re.search(r'([A-D])', line, re.IGNORECASE)
                    if answer_match:
                        correct_answer = answer_match.group(1).upper()
                elif not options and not re.match(r'^([A-D])[.)]', line):
                    # This is part of the question
                    if question:
                        question += " " + line
                    else:
                        question = line
            
            # Set correct answer
            if correct_answer and options:
                for option in options:
                    if option['letter'] == correct_answer:
                        option['is_correct'] = True
                        break
            
            # Validate we have question and 4 options
            if question and len(options) == 4:
                return {
                    'question': question.strip(),
                    'options': options
                }
            
        except Exception as e:
            logger.error(f"Error parsing MCQ text: {str(e)}")
        
        return None
#  

# For backward compatibility, create an instance function
def generate_exam_questions_enhanced(exam_id: int) -> str:
    """Enhanced question generation function for external use"""
    generator = EnhancedQuestionGenerator()
    return generator.generate_exam_questions(exam_id)
# Example usage:
# generator = EnhancedQuestionGenerator()
# result = generator.generate_exam_questions(1)
# print(result)
# This will generate questions for the exam with ID 1 using expert templates if available.