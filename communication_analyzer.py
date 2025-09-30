#!/usr/bin/env python3

"""
Communication Style Analyzer
Detects and quantifies communication patterns across different sources and types
"""

import re
import json
from typing import Dict, List, Tuple
from dataclasses import dataclass
from collections import Counter

@dataclass
class CommunicationMetrics:
    formality_score: float
    authenticity_indicators: Dict[str, float]
    emotional_openness: float
    conciseness_score: float
    engagement_patterns: Dict[str, int]
    linguistic_markers: Dict[str, List[str]]

class CommunicationStyleAnalyzer:
    """Analyzes communication style patterns across different sources"""
    
    def __init__(self):
        self.formality_patterns = {
            'very_formal': [
                r'\b(dear|sincerely|regards|respectfully|kindly|please find|attached hereto)\b',
                r'\b(furthermore|moreover|consequently|therefore|nevertheless)\b',
                r'\b(I would like to|I am writing to|I would appreciate)\b'
            ],
            'formal': [
                r'\b(please|thank you|could you|would you|I believe)\b',
                r'\b(however|although|regarding|concerning)\b',
                r'[A-Z][a-z]+ [A-Z][a-z]+',  # Proper case names
            ],
            'casual': [
                r'\b(hey|hi|thanks|sure|okay|cool|awesome)\b',
                r'\b(gonna|wanna|kinda|sorta|lol|haha)\b',
                r'[!]{2,}|[?]{2,}',  # Multiple punctuation
            ],
            'very_casual': [
                r'\b(yo|sup|nah|yep|omg|wtf|lmao|brb|ttyl)\b',
                r'[a-z]+ w/o proper punctuation',
                r'[0-9]+ instead of words',
                r'excessive abbreviations'
            ]
        }
        
        self.authenticity_markers = {
            'high_authenticity': [
                r'\b(I feel|I think|honestly|actually|to be honest)\b',
                r'\b(my experience|personally|I struggled|I failed)\b',
                r'emotional vulnerability expressions',
                r'personal anecdotes and stories'
            ],
            'medium_authenticity': [
                r'\b(I believe|in my opinion|from what I see)\b',
                r'personal preferences without deep emotion',
                r'casual opinions and observations'
            ],
            'low_authenticity': [
                r'\b(it is important|one should|best practices)\b',
                r'generic statements and platitudes',
                r'impersonal language and third person'
            ]
        }
        
        self.emotional_openness_indicators = {
            'high_openness': [
                r'\b(excited|anxious|worried|frustrated|disappointed|thrilled)\b',
                r'\b(I\'m struggling|I\'m concerned|I\'m happy|I\'m sad)\b',
                r'vulnerability markers and emotional disclosure'
            ],
            'medium_openness': [
                r'\b(good|bad|nice|interesting|challenging)\b',
                r'mild emotional expressions',
                r'indirect emotional references'
            ],
            'low_openness': [
                r'factual statements without emotion',
                r'neutral descriptive language',
                r'professional emotional restraint'
            ]
        }
        
    def analyze_text(self, text: str, source_type: str = None) -> CommunicationMetrics:
        """Analyze communication style of a text sample"""
        
        # Normalize text for analysis
        normalized_text = self._normalize_text(text)
        
        # Calculate metrics
        formality = self._calculate_formality(normalized_text)
        authenticity = self._calculate_authenticity(normalized_text)
        emotional_openness = self._calculate_emotional_openness(normalized_text)
        conciseness = self._calculate_conciseness(normalized_text)
        engagement = self._analyze_engagement_patterns(normalized_text, source_type)
        linguistic_markers = self._extract_linguistic_markers(normalized_text)
        
        return CommunicationMetrics(
            formality_score=formality,
            authenticity_indicators=authenticity,
            emotional_openness=emotional_openness,
            conciseness_score=conciseness,
            engagement_patterns=engagement,
            linguistic_markers=linguistic_markers
        )
    
    def _normalize_text(self, text: str) -> str:
        """Normalize text for consistent analysis"""
        # Convert to lowercase for pattern matching
        # Preserve original case for certain analyses
        return text.lower().strip()
    
    def _calculate_formality(self, text: str) -> float:
        """Calculate formality score (0.0 = very casual, 1.0 = very formal)"""
        scores = {'very_formal': 0, 'formal': 0, 'casual': 0, 'very_casual': 0}
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.5
        
        for level, patterns in self.formality_patterns.items():
            for pattern in patterns:
                matches = len(re.findall(pattern, text, re.IGNORECASE))
                scores[level] += matches
        
        # Weight the scores
        weighted_score = (
            scores['very_formal'] * 1.0 +
            scores['formal'] * 0.7 +
            scores['casual'] * 0.3 +
            scores['very_casual'] * 0.0
        )
        
        # Normalize by text length
        normalized_score = min(1.0, weighted_score / (total_words * 0.1))
        return normalized_score
    
    def _calculate_authenticity(self, text: str) -> Dict[str, float]:
        """Calculate authenticity indicators"""
        indicators = {}
        total_words = len(text.split())
        
        if total_words == 0:
            return {'overall': 0.5}
        
        for level, patterns in self.authenticity_markers.items():
            score = 0
            for pattern in patterns:
                if isinstance(pattern, str) and pattern.startswith(r'\b'):
                    matches = len(re.findall(pattern, text, re.IGNORECASE))
                    score += matches
            
            indicators[level] = min(1.0, score / (total_words * 0.05))
        
        # Overall authenticity score
        overall = (
            indicators.get('high_authenticity', 0) * 1.0 +
            indicators.get('medium_authenticity', 0) * 0.6 +
            indicators.get('low_authenticity', 0) * 0.2
        ) / 3
        
        indicators['overall'] = overall
        return indicators
    
    def _calculate_emotional_openness(self, text: str) -> float:
        """Calculate emotional openness score"""
        total_score = 0
        total_words = len(text.split())
        
        if total_words == 0:
            return 0.5
        
        for level, patterns in self.emotional_openness_indicators.items():
            level_score = 0
            for pattern in patterns:
                if isinstance(pattern, str) and pattern.startswith(r'\b'):
                    matches = len(re.findall(pattern, text, re.IGNORECASE))
                    level_score += matches
            
            if level == 'high_openness':
                total_score += level_score * 1.0
            elif level == 'medium_openness':
                total_score += level_score * 0.6
            elif level == 'low_openness':
                total_score -= level_score * 0.3  # Reduces openness score
        
        normalized_score = max(0.0, min(1.0, total_score / (total_words * 0.1)))
        return normalized_score
    
    def _calculate_conciseness(self, text: str) -> float:
        """Calculate how concise/verbose the communication is"""
        sentences = re.split(r'[.!?]+', text)
        if not sentences:
            return 0.5
        
        avg_sentence_length = sum(len(s.split()) for s in sentences if s.strip()) / len([s for s in sentences if s.strip()])
        
        # Score: shorter sentences = higher conciseness
        # 0.0 = very verbose, 1.0 = very concise
        if avg_sentence_length <= 8:
            return 1.0
        elif avg_sentence_length <= 15:
            return 0.8
        elif avg_sentence_length <= 25:
            return 0.5
        else:
            return 0.2
    
    def _analyze_engagement_patterns(self, text: str, source_type: str = None) -> Dict[str, int]:
        """Analyze engagement patterns specific to communication type"""
        patterns = {
            'questions': len(re.findall(r'\?', text)),
            'exclamations': len(re.findall(r'!', text)),
            'mentions': len(re.findall(r'@\w+', text)),
            'hashtags': len(re.findall(r'#\w+', text)),
            'urls': len(re.findall(r'http[s]?://\S+', text)),
            'emojis': len(re.findall(r'[😀-🙿]|[🚀-🛿]|[☀-➿]', text)),
            'caps_words': len(re.findall(r'\b[A-Z]{2,}\b', text)),
            'ellipsis': len(re.findall(r'\.{3,}', text))
        }
        
        # Source-specific engagement analysis
        if source_type == 'chat':
            patterns['quick_responses'] = len(re.findall(r'\b(yep|nope|ok|sure|cool|thanks)\b', text, re.IGNORECASE))
        elif source_type == 'posts':
            patterns['engagement_calls'] = len(re.findall(r'\b(what do you think|thoughts|agree|disagree)\b', text, re.IGNORECASE))
        elif source_type == 'articles':
            patterns['formal_transitions'] = len(re.findall(r'\b(furthermore|moreover|in conclusion|therefore)\b', text, re.IGNORECASE))
        
        return patterns
    
    def _extract_linguistic_markers(self, text: str) -> Dict[str, List[str]]:
        """Extract specific linguistic patterns and markers"""
        markers = {
            'frequent_words': [],
            'unique_phrases': [],
            'personal_pronouns': [],
            'discourse_markers': [],
            'intensifiers': [],
            'hedges': []
        }
        
        # Frequent words (excluding common stop words)
        words = re.findall(r'\b\w{4,}\b', text)
        word_freq = Counter(words)
        markers['frequent_words'] = [word for word, count in word_freq.most_common(10)]
        
        # Personal pronouns
        pronouns = re.findall(r'\b(i|me|my|myself|we|us|our|you|your)\b', text, re.IGNORECASE)
        markers['personal_pronouns'] = list(set(pronouns))
        
        # Discourse markers
        discourse_patterns = [
            r'\b(however|therefore|furthermore|moreover|nevertheless|consequently)\b',
            r'\b(first|second|finally|in conclusion|on the other hand)\b',
            r'\b(actually|basically|essentially|obviously|clearly)\b'
        ]
        
        for pattern in discourse_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            markers['discourse_markers'].extend(matches)
        
        # Intensifiers
        intensifier_pattern = r'\b(very|really|extremely|incredibly|absolutely|totally|quite|rather)\b'
        markers['intensifiers'] = re.findall(intensifier_pattern, text, re.IGNORECASE)
        
        # Hedges (uncertainty markers)
        hedge_pattern = r'\b(maybe|perhaps|possibly|probably|might|could|seems|appears|I think|I believe)\b'
        markers['hedges'] = re.findall(hedge_pattern, text, re.IGNORECASE)
        
        # Remove duplicates and limit length
        for key in markers:
            markers[key] = list(set(markers[key]))[:10]
        
        return markers
    
    def compare_communication_styles(self, metrics_dict: Dict[str, CommunicationMetrics]) -> Dict:
        """Compare communication styles across different sources"""
        comparison = {
            'formality_ranking': [],
            'authenticity_ranking': [], 
            'emotional_openness_ranking': [],
            'style_differences': {},
            'cross_source_patterns': {}
        }
        
        # Rank sources by different metrics
        formality_sorted = sorted(metrics_dict.items(), key=lambda x: x[1].formality_score, reverse=True)
        authenticity_sorted = sorted(metrics_dict.items(), key=lambda x: x[1].authenticity_indicators.get('overall', 0), reverse=True)
        emotional_sorted = sorted(metrics_dict.items(), key=lambda x: x[1].emotional_openness, reverse=True)
        
        comparison['formality_ranking'] = [(name, metrics.formality_score) for name, metrics in formality_sorted]
        comparison['authenticity_ranking'] = [(name, metrics.authenticity_indicators.get('overall', 0)) for name, metrics in authenticity_sorted]
        comparison['emotional_openness_ranking'] = [(name, metrics.emotional_openness) for name, metrics in emotional_sorted]
        
        # Identify style differences
        if len(metrics_dict) >= 2:
            sources = list(metrics_dict.keys())
            for i, source1 in enumerate(sources):
                for source2 in sources[i+1:]:
                    metrics1 = metrics_dict[source1]
                    metrics2 = metrics_dict[source2]
                    
                    formality_diff = abs(metrics1.formality_score - metrics2.formality_score)
                    authenticity_diff = abs(
                        metrics1.authenticity_indicators.get('overall', 0) - 
                        metrics2.authenticity_indicators.get('overall', 0)
                    )
                    emotional_diff = abs(metrics1.emotional_openness - metrics2.emotional_openness)
                    
                    comparison['style_differences'][f"{source1}_vs_{source2}"] = {
                        'formality_difference': formality_diff,
                        'authenticity_difference': authenticity_diff,
                        'emotional_difference': emotional_diff,
                        'overall_difference': (formality_diff + authenticity_diff + emotional_diff) / 3
                    }
        
        return comparison
    
    def generate_style_summary(self, metrics: CommunicationMetrics, source_name: str) -> str:
        """Generate human-readable summary of communication style"""
        
        # Formality description
        if metrics.formality_score >= 0.8:
            formality = "very formal"
        elif metrics.formality_score >= 0.6:
            formality = "formal"
        elif metrics.formality_score >= 0.4:
            formality = "semi-formal"
        elif metrics.formality_score >= 0.2:
            formality = "casual"
        else:
            formality = "very casual"
        
        # Authenticity description
        auth_overall = metrics.authenticity_indicators.get('overall', 0.5)
        if auth_overall >= 0.7:
            authenticity = "highly authentic"
        elif auth_overall >= 0.5:
            authenticity = "moderately authentic"
        else:
            authenticity = "less authentic/more filtered"
        
        # Emotional openness description
        if metrics.emotional_openness >= 0.7:
            emotional = "emotionally open"
        elif metrics.emotional_openness >= 0.4:
            emotional = "moderately expressive"
        else:
            emotional = "emotionally reserved"
        
        # Conciseness description
        if metrics.conciseness_score >= 0.7:
            conciseness = "concise"
        elif metrics.conciseness_score >= 0.4:
            conciseness = "balanced"
        else:
            conciseness = "verbose"
        
        summary = f"{source_name}: {formality}, {authenticity}, {emotional}, {conciseness} communication style"
        
        # Add specific markers if notable
        if metrics.engagement_patterns.get('questions', 0) > 5:
            summary += "; frequently asks questions"
        if metrics.engagement_patterns.get('exclamations', 0) > 5:
            summary += "; uses emphatic expressions"
        if len(metrics.linguistic_markers.get('hedges', [])) > 3:
            summary += "; tends to hedge statements"
        if len(metrics.linguistic_markers.get('intensifiers', [])) > 3:
            summary += "; uses many intensifiers"
        
        return summary

# Example usage
if __name__ == "__main__":
    analyzer = CommunicationStyleAnalyzer()
    
    # Example text analysis
    sample_texts = {
        "whatsapp": "hey! how are you doing? i'm so excited about tomorrow's meeting :) wanna grab coffee after?",
        "email": "Dear Colleague, I am writing to inform you about the upcoming project deadline. Please find attached the relevant documents for your review. I would appreciate your feedback at your earliest convenience. Best regards,",
        "twitter": "Just shipped a new feature! Really proud of the team's hard work. What do you think about the new design? #product #teamwork 🚀"
    }
    
    print("Communication Style Analysis Example:")
    print("=" * 50)
    
    for source, text in sample_texts.items():
        metrics = analyzer.analyze_text(text, source)
        summary = analyzer.generate_style_summary(metrics, source)
        print(f"{summary}")
        print(f"  Formality: {metrics.formality_score:.2f}")
        print(f"  Authenticity: {metrics.authenticity_indicators.get('overall', 0):.2f}")
        print(f"  Emotional Openness: {metrics.emotional_openness:.2f}")
        print(f"  Conciseness: {metrics.conciseness_score:.2f}")
        print()