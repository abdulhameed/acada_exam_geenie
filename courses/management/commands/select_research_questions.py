#!/usr/bin/env python3
"""
Django management command to select balanced research questions
Create this file at: courses/management/commands/select_research_questions.py
"""

import random
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from django.utils import timezone
from courses.models import ExpertQuestion
from collections import defaultdict


class Command(BaseCommand):
    help = 'Select balanced sample of expert questions for research with source material'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--sample-size',
            type=int,
            default=200,
            help='Total number of questions to select (default: 200)'
        )
        parser.add_argument(
            '--batch-name',
            type=str,
            default='research_baseline_v1',
            help='Batch identifier for this selection'
        )
        parser.add_argument(
            '--domains',
            type=str,
            help='Comma-separated domains to include (e.g., "Science,Math,Social Studies")'
        )
        parser.add_argument(
            '--equal-distribution',
            action='store_true',
            help='Distribute equally across domains (default: proportional to available)'
        )
        parser.add_argument(
            '--min-source-length',
            type=int,
            default=100,
            help='Minimum source material length (default: 100 characters)'
        )
        parser.add_argument(
            '--clear-existing',
            action='store_true',
            help='Clear existing selections before making new ones'
        )
        parser.add_argument(
            '--dry-run',
            action='store_true',
            help='Show what would be selected without actually selecting'
        )
        parser.add_argument(
            '--seed',
            type=int,
            help='Random seed for reproducible selection'
        )
    
    def handle(self, *args, **options):
        # Set random seed for reproducibility
        if options['seed']:
            random.seed(options['seed'])
            self.stdout.write(f"Using random seed: {options['seed']}")
        
        sample_size = options['sample_size']
        batch_name = options['batch_name']
        min_source_length = options['min_source_length']
        
        # Clear existing selections if requested
        if options['clear_existing']:
            if not options['dry_run']:
                cleared_count = ExpertQuestion.objects.filter(is_selected_for_research=True).count()
                ExpertQuestion.objects.filter(is_selected_for_research=True).update(
                    is_selected_for_research=False,
                    selection_date=None,
                    selection_batch=''
                )
                self.stdout.write(f"Cleared {cleared_count} existing selections")
            else:
                self.stdout.write("DRY RUN: Would clear existing selections")
        
        # Get available questions with source material
        available_questions = ExpertQuestion.objects.filter(
            source_material__isnull=False,
            is_selected_for_research=False  # Not already selected
        ).exclude(source_material='')
        
        # Filter by minimum source length
        available_questions = [
            q for q in available_questions 
            if len(q.source_material.strip()) >= min_source_length
        ]
        
        if not available_questions:
            raise CommandError("No questions with adequate source material found")
        
        # Filter by domains if specified
        if options['domains']:
            specified_domains = [d.strip() for d in options['domains'].split(',')]
            available_questions = [
                q for q in available_questions 
                if q.domain in specified_domains
            ]
            
            if not available_questions:
                raise CommandError(f"No questions found for domains: {specified_domains}")
        
        # Analyze available questions by domain
        domain_questions = defaultdict(list)
        for q in available_questions:
            domain = q.domain or 'Unknown'
            domain_questions[domain].append(q)
        
        # Display availability
        self.stdout.write("AVAILABLE QUESTIONS WITH SOURCE MATERIAL:")
        total_available = 0
        for domain, questions in sorted(domain_questions.items()):
            count = len(questions)
            total_available += count
            self.stdout.write(f"  {domain:20} {count:>4} questions available")
        
        self.stdout.write(f"  {'TOTAL':20} {total_available:>4} questions available")
        self.stdout.write("")
        
        if total_available < sample_size:
            raise CommandError(f"Not enough questions available. Need {sample_size}, have {total_available}")
        
        # Calculate distribution
        if options['equal_distribution']:
            distribution = self.calculate_equal_distribution(domain_questions, sample_size)
        else:
            distribution = self.calculate_proportional_distribution(domain_questions, sample_size)
        
        # Display planned selection
        self.stdout.write("PLANNED SELECTION DISTRIBUTION:")
        total_planned = 0
        for domain, count in sorted(distribution.items()):
            available_count = len(domain_questions[domain])
            total_planned += count
            self.stdout.write(f"  {domain:20} {count:>4} selected from {available_count} available")
        
        self.stdout.write(f"  {'TOTAL':20} {total_planned:>4} questions to select")
        self.stdout.write("")
        
        # Perform selection
        selected_questions = []
        selection_details = {}
        
        for domain, target_count in distribution.items():
            available = domain_questions[domain]
            
            if len(available) < target_count:
                self.stdout.write(
                    self.style.WARNING(
                        f"Warning: Only {len(available)} questions available for {domain}, "
                        f"need {target_count}. Selecting all available."
                    )
                )
                target_count = len(available)
            
            # Randomly sample from available questions
            selected = random.sample(available, target_count)
            selected_questions.extend(selected)
            
            selection_details[domain] = {
                'selected': selected,
                'count': len(selected),
                'target': target_count
            }
        
        # Display selection results
        self.stdout.write("SELECTION RESULTS:")
        for domain, details in sorted(selection_details.items()):
            count = details['count']
            target = details['target']
            status = "✓" if count == target else "⚠"
            self.stdout.write(f"  {status} {domain:20} {count:>4} questions selected")
        
        self.stdout.write(f"  {'TOTAL':22} {len(selected_questions):>4} questions selected")
        self.stdout.write("")
        
        # Show sample of selected questions
        self.stdout.write("SAMPLE OF SELECTED QUESTIONS:")
        for i, q in enumerate(selected_questions[:5]):
            source_preview = q.source_material[:100] + "..." if len(q.source_material) > 100 else q.source_material
            self.stdout.write(f"  {i+1}. [{q.domain}] {q.question_text[:60]}...")
            self.stdout.write(f"     Source: {len(q.source_material)} chars - {source_preview}")
        
        if len(selected_questions) > 5:
            self.stdout.write(f"     ... and {len(selected_questions) - 5} more questions")
        self.stdout.write("")
        
        # Validate selection
        validation_results = self.validate_selection(selected_questions, options)
        if not validation_results['valid']:
            raise CommandError(f"Selection validation failed: {validation_results['errors']}")
        
        # Save selection
        if options['dry_run']:
            self.stdout.write(self.style.SUCCESS("DRY RUN COMPLETE - No changes made to database"))
        else:
            with transaction.atomic():
                selection_date = timezone.now()
                
                for question in selected_questions:
                    question.is_selected_for_research = True
                    question.selection_date = selection_date
                    question.selection_batch = batch_name
                    question.save()
                
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Successfully selected {len(selected_questions)} questions for research!\n"
                        f"Batch: {batch_name}\n"
                        f"Selection Date: {selection_date}\n"
                        f"Use 'python manage.py analyze_expert_questions --selected-only' to view stats"
                    )
                )
    
    def calculate_equal_distribution(self, domain_questions, sample_size):
        """Calculate equal distribution across domains"""
        domains = list(domain_questions.keys())
        per_domain = sample_size // len(domains)
        remainder = sample_size % len(domains)
        
        distribution = {}
        for domain in domains:
            distribution[domain] = per_domain
        
        # Distribute remainder to domains with most available questions
        sorted_domains = sorted(domains, key=lambda d: len(domain_questions[d]), reverse=True)
        for i in range(remainder):
            distribution[sorted_domains[i]] += 1
        
        return distribution
    
    def calculate_proportional_distribution(self, domain_questions, sample_size):
        """Calculate proportional distribution based on availability"""
        total_available = sum(len(questions) for questions in domain_questions.values())
        
        distribution = {}
        allocated = 0
        
        # Calculate proportional allocation
        for domain, questions in domain_questions.items():
            proportion = len(questions) / total_available
            count = int(sample_size * proportion)
            distribution[domain] = count
            allocated += count
        
        # Distribute any remaining slots to largest domains
        remaining = sample_size - allocated
        if remaining > 0:
            sorted_domains = sorted(
                distribution.keys(), 
                key=lambda d: len(domain_questions[d]), 
                reverse=True
            )
            for i in range(remaining):
                distribution[sorted_domains[i % len(sorted_domains)]] += 1
        
        return distribution
    
    def validate_selection(self, selected_questions, options):
        """Validate the selection meets requirements"""
        errors = []
        
        # Check all have source material
        without_source = [q for q in selected_questions if not q.source_material or len(q.source_material.strip()) < options['min_source_length']]
        if without_source:
            errors.append(f"{len(without_source)} questions lack adequate source material")
        
        # Check for duplicates
        question_ids = [q.question_id for q in selected_questions]
        if len(question_ids) != len(set(question_ids)):
            errors.append("Duplicate questions in selection")
        
        # Check sample size
        if len(selected_questions) != options['sample_size']:
            errors.append(f"Selected {len(selected_questions)} questions, expected {options['sample_size']}")
        
        return {
            'valid': len(errors) == 0,
            'errors': errors
        }
