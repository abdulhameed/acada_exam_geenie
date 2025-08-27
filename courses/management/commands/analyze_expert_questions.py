#!/usr/bin/env python3
"""
Django management command to analyze expert questions statistics
Create this file at: courses/management/commands/analyze_expert_questions.py
"""

import os
from django.core.management.base import BaseCommand
from django.db.models import Count, Avg, Min, Max, Q
from django.utils import timezone
from courses.models import ExpertQuestion, ExpertQuestionDataset
from collections import defaultdict
import json


class Command(BaseCommand):
    help = 'Analyze and display comprehensive statistics for expert questions'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--dataset-id',
            type=int,
            help='Analyze specific dataset by ID'
        )
        parser.add_argument(
            '--dataset-name',
            type=str,
            help='Analyze specific dataset by name'
        )
        parser.add_argument(
            '--export-json',
            type=str,
            help='Export statistics to JSON file'
        )
        parser.add_argument(
            '--detailed',
            action='store_true',
            help='Show detailed per-dataset breakdown'
        )
        parser.add_argument(
            '--source-analysis',
            action='store_true',
            help='Perform detailed source material analysis'
        )
    
    def handle(self, *args, **options):
        # Filter questions based on options
        questions_query = ExpertQuestion.objects.all()
        
        if options['dataset_id']:
            questions_query = questions_query.filter(dataset_id=options['dataset_id'])
            dataset_filter = f"Dataset ID: {options['dataset_id']}"
        elif options['dataset_name']:
            questions_query = questions_query.filter(dataset__name__icontains=options['dataset_name'])
            dataset_filter = f"Dataset Name: {options['dataset_name']}"
        else:
            dataset_filter = "All Datasets"
        
        questions = list(questions_query.select_related('dataset'))
        
        if not questions:
            self.stdout.write(self.style.WARNING("No questions found matching the criteria."))
            return
        
        # Generate comprehensive statistics
        stats = self.generate_statistics(questions, options)
        
        # Display results
        self.display_statistics(stats, dataset_filter, options)
        
        # Export to JSON if requested
        if options['export_json']:
            self.export_to_json(stats, options['export_json'])
    
    def generate_statistics(self, questions, options):
        """Generate comprehensive statistics"""
        stats = {
            'overview': {},
            'source_material': {},
            'domains': {},
            'question_types': {},
            'difficulty': {},
            'datasets': {},
            'quality': {},
            'usage': {},
            'temporal': {}
        }
        
        # Overview Statistics
        total_questions = len(questions)
        stats['overview'] = {
            'total_questions': total_questions,
            'total_datasets': len(set(q.dataset_id for q in questions)),
            'unique_domains': len(set(q.domain for q in questions if q.domain)),
            'analysis_date': timezone.now().isoformat()
        }
        
        # Source Material Analysis
        with_source = [q for q in questions if q.source_material and len(q.source_material.strip()) > 0]
        without_source = [q for q in questions if not q.source_material or len(q.source_material.strip()) == 0]
        
        source_lengths = [len(q.source_material) for q in with_source if q.source_material]
        
        stats['source_material'] = {
            'total_with_source': len(with_source),
            'total_without_source': len(without_source),
            'percentage_with_source': round((len(with_source) / total_questions) * 100, 2),
            'percentage_without_source': round((len(without_source) / total_questions) * 100, 2),
        }
        
        if source_lengths:
            stats['source_material'].update({
                'avg_source_length': round(sum(source_lengths) / len(source_lengths), 0),
                'min_source_length': min(source_lengths),
                'max_source_length': max(source_lengths),
                'sources_over_100_chars': len([l for l in source_lengths if l >= 100]),
                'sources_over_500_chars': len([l for l in source_lengths if l >= 500]),
                'sources_over_1000_chars': len([l for l in source_lengths if l >= 1000]),
            })
        
        # Domain Distribution
        domain_counts = defaultdict(int)
        domain_with_source = defaultdict(int)
        
        for q in questions:
            domain = q.domain or 'Unknown'
            domain_counts[domain] += 1
            if q.source_material and len(q.source_material.strip()) > 0:
                domain_with_source[domain] += 1
        
        stats['domains'] = {}
        for domain, count in domain_counts.items():
            stats['domains'][domain] = {
                'total_questions': count,
                'with_source': domain_with_source[domain],
                'percentage': round((count / total_questions) * 100, 2),
                'source_coverage': round((domain_with_source[domain] / count) * 100, 2) if count > 0 else 0
            }
        
        # Question Type Distribution
        type_counts = defaultdict(int)
        type_with_source = defaultdict(int)
        
        for q in questions:
            q_type = q.question_type or 'Unknown'
            type_counts[q_type] += 1
            if q.source_material and len(q.source_material.strip()) > 0:
                type_with_source[q_type] += 1
        
        stats['question_types'] = {}
        for q_type, count in type_counts.items():
            stats['question_types'][q_type] = {
                'total_questions': count,
                'with_source': type_with_source[q_type],
                'percentage': round((count / total_questions) * 100, 2),
                'source_coverage': round((type_with_source[q_type] / count) * 100, 2) if count > 0 else 0
            }
        
        # Difficulty Distribution
        difficulty_counts = defaultdict(int)
        for q in questions:
            difficulty = q.difficulty_level or 'unknown'
            difficulty_counts[difficulty] += 1
        
        stats['difficulty'] = {
            difficulty: {
                'count': count,
                'percentage': round((count / total_questions) * 100, 2)
            }
            for difficulty, count in difficulty_counts.items()
        }
        
        # Dataset Breakdown
        dataset_stats = defaultdict(lambda: {
            'questions': 0,
            'with_source': 0,
            'domains': defaultdict(int),
            'types': defaultdict(int)
        })
        
        for q in questions:
            dataset_name = q.dataset.name if q.dataset else 'No Dataset'
            dataset_stats[dataset_name]['questions'] += 1
            
            if q.source_material and len(q.source_material.strip()) > 0:
                dataset_stats[dataset_name]['with_source'] += 1
            
            domain = q.domain or 'Unknown'
            q_type = q.question_type or 'Unknown'
            dataset_stats[dataset_name]['domains'][domain] += 1
            dataset_stats[dataset_name]['types'][q_type] += 1
        
        stats['datasets'] = {}
        for dataset_name, data in dataset_stats.items():
            stats['datasets'][dataset_name] = {
                'total_questions': data['questions'],
                'with_source': data['with_source'],
                'source_coverage': round((data['with_source'] / data['questions']) * 100, 2),
                'top_domains': dict(sorted(data['domains'].items(), key=lambda x: x[1], reverse=True)[:5]),
                'question_types': dict(data['types'])
            }
        
        # Quality Analysis
        quality_ratings = [q.quality_rating for q in questions if q.quality_rating is not None]
        if quality_ratings:
            stats['quality'] = {
                'questions_with_rating': len(quality_ratings),
                'avg_quality': round(sum(quality_ratings) / len(quality_ratings), 2),
                'min_quality': min(quality_ratings),
                'max_quality': max(quality_ratings),
                'percentage_rated': round((len(quality_ratings) / total_questions) * 100, 2)
            }
        else:
            stats['quality'] = {
                'questions_with_rating': 0,
                'percentage_rated': 0
            }
        
        # Usage Statistics
        usage_counts = [q.times_used_as_template for q in questions if q.times_used_as_template > 0]
        stats['usage'] = {
            'questions_used_as_template': len(usage_counts),
            'total_template_uses': sum(q.times_used_as_template for q in questions),
            'avg_uses_per_question': round(sum(q.times_used_as_template for q in questions) / total_questions, 2),
            'most_used_count': max((q.times_used_as_template for q in questions), default=0)
        }
        
        # Additional Source Analysis if requested
        if options.get('source_analysis'):
            stats['detailed_source_analysis'] = self.analyze_source_material_detailed(questions)
        
        return stats
    
    def analyze_source_material_detailed(self, questions):
        """Perform detailed source material analysis"""
        analysis = {
            'source_types': defaultdict(int),
            'video_sources': 0,
            'article_sources': 0,
            'unknown_sources': 0,
            'youtube_links': 0,
            'missing_source_flags': 0
        }
        
        for q in questions:
            # Classify source type
            if 'TED-Ed' in (q.file_source or ''):
                analysis['source_types']['TED-Ed'] += 1
            elif 'Khan Academy Video' in (q.file_source or ''):
                analysis['source_types']['Khan Academy Video'] += 1
            elif 'Khan Academy Article' in (q.file_source or ''):
                analysis['source_types']['Khan Academy Article'] += 1
            else:
                analysis['source_types']['Other'] += 1
            
            # Count video vs article sources
            if q.video_id:
                analysis['video_sources'] += 1
            elif 'article' in (q.file_source or '').lower():
                analysis['article_sources'] += 1
            else:
                analysis['unknown_sources'] += 1
            
            # Count YouTube links
            if q.video_youtube_link:
                analysis['youtube_links'] += 1
            
            # Check missing source flags
            if hasattr(q, 'is_missing_source') and q.is_missing_source:
                analysis['missing_source_flags'] += 1
        
        return dict(analysis)
    
    def display_statistics(self, stats, dataset_filter, options):
        """Display formatted statistics"""
        
        self.stdout.write("=" * 80)
        self.stdout.write(self.style.SUCCESS("EXPERT QUESTIONS STATISTICS REPORT"))
        self.stdout.write("=" * 80)
        self.stdout.write(f"Filter: {dataset_filter}")
        self.stdout.write(f"Generated: {stats['overview']['analysis_date'][:19]}")
        self.stdout.write("")
        
        # Overview
        self.stdout.write(self.style.WARNING("OVERVIEW:"))
        self.stdout.write(f"  Total Questions: {stats['overview']['total_questions']:,}")
        self.stdout.write(f"  Total Datasets: {stats['overview']['total_datasets']}")
        self.stdout.write(f"  Unique Domains: {stats['overview']['unique_domains']}")
        self.stdout.write("")
        
        # Source Material
        self.stdout.write(self.style.WARNING("SOURCE MATERIAL COVERAGE:"))
        sm = stats['source_material']
        self.stdout.write(f"  With Source Material: {sm['total_with_source']:,} ({sm['percentage_with_source']}%)")
        self.stdout.write(f"  Without Source Material: {sm['total_without_source']:,} ({sm['percentage_without_source']}%)")
        
        if 'avg_source_length' in sm:
            self.stdout.write(f"  Average Source Length: {sm['avg_source_length']:,.0f} characters")
            self.stdout.write(f"  Source Length Range: {sm['min_source_length']:,} - {sm['max_source_length']:,} characters")
            self.stdout.write(f"  Sources >100 chars: {sm['sources_over_100_chars']:,}")
            self.stdout.write(f"  Sources >500 chars: {sm['sources_over_500_chars']:,}")
            self.stdout.write(f"  Sources >1000 chars: {sm['sources_over_1000_chars']:,}")
        self.stdout.write("")
        
        # Domain Distribution
        self.stdout.write(self.style.WARNING("DOMAIN DISTRIBUTION:"))
        for domain, data in sorted(stats['domains'].items(), key=lambda x: x[1]['total_questions'], reverse=True):
            self.stdout.write(f"  {domain:20} {data['total_questions']:>6,} ({data['percentage']:>5.1f}%) "
                            f"[{data['with_source']:>5,} with source ({data['source_coverage']:>5.1f}%)]")
        self.stdout.write("")
        
        # Question Types
        self.stdout.write(self.style.WARNING("QUESTION TYPE DISTRIBUTION:"))
        for q_type, data in sorted(stats['question_types'].items(), key=lambda x: x[1]['total_questions'], reverse=True):
            self.stdout.write(f"  {q_type:20} {data['total_questions']:>6,} ({data['percentage']:>5.1f}%) "
                            f"[{data['with_source']:>5,} with source ({data['source_coverage']:>5.1f}%)]")
        self.stdout.write("")
        
        # Difficulty Distribution
        self.stdout.write(self.style.WARNING("DIFFICULTY DISTRIBUTION:"))
        for difficulty, data in sorted(stats['difficulty'].items(), key=lambda x: x[1]['count'], reverse=True):
            self.stdout.write(f"  {difficulty:20} {data['count']:>6,} ({data['percentage']:>5.1f}%)")
        self.stdout.write("")
        
        # Quality Statistics
        if stats['quality']['questions_with_rating'] > 0:
            self.stdout.write(self.style.WARNING("QUALITY STATISTICS:"))
            q = stats['quality']
            self.stdout.write(f"  Questions with Rating: {q['questions_with_rating']:,} ({q['percentage_rated']}%)")
            self.stdout.write(f"  Average Quality: {q['avg_quality']:.2f}")
            self.stdout.write(f"  Quality Range: {q['min_quality']:.1f} - {q['max_quality']:.1f}")
            self.stdout.write("")
        
        # Usage Statistics
        self.stdout.write(self.style.WARNING("USAGE STATISTICS:"))
        u = stats['usage']
        self.stdout.write(f"  Questions Used as Templates: {u['questions_used_as_template']:,}")
        self.stdout.write(f"  Total Template Uses: {u['total_template_uses']:,}")
        self.stdout.write(f"  Average Uses per Question: {u['avg_uses_per_question']:.2f}")
        self.stdout.write(f"  Most Used Question Count: {u['most_used_count']:,}")
        self.stdout.write("")
        
        # Detailed Dataset Breakdown
        if options.get('detailed') and len(stats['datasets']) > 1:
            self.stdout.write(self.style.WARNING("DETAILED DATASET BREAKDOWN:"))
            for dataset_name, data in stats['datasets'].items():
                self.stdout.write(f"\n  📊 {dataset_name}:")
                self.stdout.write(f"    Questions: {data['total_questions']:,}")
                self.stdout.write(f"    With Source: {data['with_source']:,} ({data['source_coverage']:.1f}%)")
                self.stdout.write(f"    Top Domains: {', '.join([f'{d}({c})' for d, c in list(data['top_domains'].items())[:3]])}")
                self.stdout.write(f"    Question Types: {', '.join([f'{t}({c})' for t, c in data['question_types'].items()])}")
            self.stdout.write("")
        
        # Detailed Source Analysis
        if 'detailed_source_analysis' in stats:
            self.stdout.write(self.style.WARNING("DETAILED SOURCE ANALYSIS:"))
            dsa = stats['detailed_source_analysis']
            self.stdout.write(f"  Source Type Breakdown:")
            for source_type, count in sorted(dsa['source_types'].items(), key=lambda x: x[1], reverse=True):
                self.stdout.write(f"    {source_type:20} {count:>6,}")
            self.stdout.write(f"  Video Sources: {dsa['video_sources']:,}")
            self.stdout.write(f"  Article Sources: {dsa['article_sources']:,}")
            self.stdout.write(f"  YouTube Links: {dsa['youtube_links']:,}")
            if dsa['missing_source_flags'] > 0:
                self.stdout.write(f"  Flagged Missing Source: {dsa['missing_source_flags']:,}")
            self.stdout.write("")
        
        # Recommendations
        self.stdout.write(self.style.SUCCESS("RECOMMENDATIONS:"))
        if stats['source_material']['percentage_without_source'] > 10:
            self.stdout.write("  ⚠️  Consider recovering source material for questions without sources")
        if stats['quality']['percentage_rated'] < 50:
            self.stdout.write("  📈 Consider adding quality ratings to improve question selection")
        if stats['usage']['questions_used_as_template'] < stats['overview']['total_questions'] * 0.1:
            self.stdout.write("  🎯 Many questions haven't been used as templates yet")
        
        self.stdout.write("=" * 80)
    
    def export_to_json(self, stats, filename):
        """Export statistics to JSON file"""
        try:
            with open(filename, 'w') as f:
                json.dump(stats, f, indent=2, default=str)
            self.stdout.write(f"Statistics exported to: {filename}")
        except Exception as e:
            self.stdout.write(self.style.ERROR(f"Failed to export JSON: {e}"))