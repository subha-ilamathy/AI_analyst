"""Advanced NLP-based parsing using spaCy, semantic similarity, and dependency parsing."""

import re
import warnings
from datetime import datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any
from dataclasses import dataclass

try:
    import spacy
    from spacy import displacy
    from spacy.tokens import Span
    SPACY_AVAILABLE = True
except ImportError:
    SPACY_AVAILABLE = False
    warnings.warn("spaCy not available. Install with: pip install spacy")

try:
    from sentence_transformers import SentenceTransformer
    SENTENCE_TRANSFORMERS_AVAILABLE = True
except ImportError:
    SENTENCE_TRANSFORMERS_AVAILABLE = False
    warnings.warn("sentence-transformers not available. Install with: pip install sentence-transformers")

try:
    from sklearn.metrics.pairwise import cosine_similarity
    from sklearn.feature_extraction.text import TfidfVectorizer
    SKLEARN_AVAILABLE = True
except ImportError:
    SKLEARN_AVAILABLE = False
    warnings.warn("scikit-learn not available. Install with: pip install scikit-learn")

from dateutil import parser as dtparser
from dateutil.relativedelta import relativedelta


@dataclass
class TimeExpression:
    """Represents a parsed time expression."""
    text: str
    start_date: Optional[datetime]
    end_date: Optional[datetime]
    confidence: float
    expression_type: str  # 'relative', 'absolute', 'range', 'period'
    entities: List[str]  # Named entities found


class AdvancedTimeParser:
    """Advanced time parsing using multiple NLP techniques."""
    
    def __init__(self):
        self.nlp = None
        self.similarity_model = None
        self.vectorizer = None
        self._initialize_models()
        
        # Time expression patterns for semantic matching
        self.time_patterns = {
            'last_week': ['last week', 'previous week', 'past week', 'week before'],
            'this_week': ['this week', 'current week', 'present week'],
            'last_month': ['last month', 'previous month', 'past month', 'month before'],
            'this_month': ['this month', 'current month', 'present month'],
            'last_year': ['last year', 'previous year', 'past year', 'year before'],
            'this_year': ['this year', 'current year', 'present year'],
            'yesterday': ['yesterday', 'day before', 'previous day'],
            'today': ['today', 'current day', 'present day'],
            'tomorrow': ['tomorrow', 'next day', 'following day'],
        }
        
        # Relative time expressions
        self.relative_patterns = {
            'days': ['days', 'day', 'd'],
            'weeks': ['weeks', 'week', 'w'],
            'months': ['months', 'month', 'm'],
            'years': ['years', 'year', 'y'],
        }
    
    def _initialize_models(self):
        """Initialize NLP models."""
        if SPACY_AVAILABLE:
            try:
                self.nlp = spacy.load("en_core_web_sm")
            except OSError:
                try:
                    self.nlp = spacy.load("en_core_web_md")
                except OSError:
                    warnings.warn("spaCy English model not found. Install with: python -m spacy download en_core_web_sm")
                    self.nlp = None
        
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                warnings.warn(f"Could not load sentence transformer: {e}")
                self.similarity_model = None
        
        if SKLEARN_AVAILABLE:
            self.vectorizer = TfidfVectorizer(max_features=1000, stop_words='english')
    
    def parse_time_expression(self, text: str) -> List[TimeExpression]:
        """Parse time expressions from text using advanced NLP."""
        expressions = []
        
        # Method 1: spaCy NER and dependency parsing
        if self.nlp:
            expressions.extend(self._parse_with_spacy(text))
        
        # Method 2: Semantic similarity matching
        if self.similarity_model:
            expressions.extend(self._parse_with_semantic_similarity(text))
        
        # Method 3: Advanced dateutil parsing
        expressions.extend(self._parse_with_dateutil(text))
        
        # Method 4: Pattern-based parsing with context
        expressions.extend(self._parse_with_context_patterns(text))
        
        # Remove duplicates and sort by confidence
        unique_expressions = self._deduplicate_expressions(expressions)
        return sorted(unique_expressions, key=lambda x: x.confidence, reverse=True)
    
    def _parse_with_spacy(self, text: str) -> List[TimeExpression]:
        """Parse using spaCy NER and dependency parsing."""
        if not self.nlp:
            return []
        
        expressions = []
        doc = self.nlp(text)
        
        # Find DATE entities
        for ent in doc.ents:
            if ent.label_ == "DATE":
                try:
                    # Parse the date entity
                    parsed_date = dtparser.parse(ent.text, fuzzy=True)
                    expressions.append(TimeExpression(
                        text=ent.text,
                        start_date=parsed_date,
                        end_date=parsed_date,
                        confidence=0.8,
                        expression_type='absolute',
                        entities=[ent.text]
                    ))
                except:
                    # Try relative parsing
                    rel_expr = self._parse_relative_with_spacy(ent.text, doc)
                    if rel_expr:
                        expressions.append(rel_expr)
        
        # Find temporal expressions using dependency parsing
        for token in doc:
            if token.dep_ in ['tmod', 'advmod'] and token.pos_ in ['ADV', 'NOUN']:
                if any(word in token.text.lower() for word in ['last', 'this', 'next', 'previous']):
                    rel_expr = self._parse_relative_with_spacy(token.text, doc)
                    if rel_expr:
                        expressions.append(rel_expr)
        
        return expressions
    
    def _parse_relative_with_spacy(self, text: str, doc) -> Optional[TimeExpression]:
        """Parse relative time expressions using spaCy dependency parsing."""
        text_lower = text.lower()
        now = datetime.now()
        
        # Find the root of the temporal expression
        for token in doc:
            if text_lower in token.text.lower():
                # Look for modifiers
                for child in token.children:
                    if child.dep_ == 'det' and child.text.lower() in ['last', 'this', 'next', 'previous']:
                        modifier = child.text.lower()
                        
                        if 'week' in text_lower:
                            if modifier == 'last':
                                start = now - timedelta(days=now.weekday() + 7)
                                end = start + timedelta(days=6)
                                return TimeExpression(
                                    text=text,
                                    start_date=start.replace(hour=0, minute=0, second=0),
                                    end_date=end.replace(hour=23, minute=59, second=59),
                                    confidence=0.9,
                                    expression_type='relative',
                                    entities=[text]
                                )
                            elif modifier == 'this':
                                start = now - timedelta(days=now.weekday())
                                return TimeExpression(
                                    text=text,
                                    start_date=start.replace(hour=0, minute=0, second=0),
                                    end_date=now,
                                    confidence=0.9,
                                    expression_type='relative',
                                    entities=[text]
                                )
        
        return None
    
    def _parse_with_semantic_similarity(self, text: str) -> List[TimeExpression]:
        """Parse using semantic similarity matching."""
        if not self.similarity_model:
            return []
        
        expressions = []
        text_lower = text.lower()
        
        # Create embeddings for the input text
        try:
            text_embedding = self.similarity_model.encode([text_lower])
            
            # Compare with known patterns
            for pattern_type, patterns in self.time_patterns.items():
                pattern_embeddings = self.similarity_model.encode(patterns)
                similarities = cosine_similarity(text_embedding, pattern_embeddings)[0]
                max_similarity = max(similarities)
                
                if max_similarity > 0.7:  # Threshold for similarity
                    expr = self._create_expression_from_pattern(pattern_type, text)
                    if expr:
                        expr.confidence = max_similarity
                        expressions.append(expr)
        except Exception as e:
            warnings.warn(f"Semantic similarity parsing failed: {e}")
        
        return expressions
    
    def _create_expression_from_pattern(self, pattern_type: str, text: str) -> Optional[TimeExpression]:
        """Create TimeExpression from matched pattern."""
        now = datetime.now()
        
        if pattern_type == 'last_week':
            start = now - timedelta(days=now.weekday() + 7)
            end = start + timedelta(days=6)
            return TimeExpression(
                text=text,
                start_date=start.replace(hour=0, minute=0, second=0),
                end_date=end.replace(hour=23, minute=59, second=59),
                confidence=0.8,
                expression_type='relative',
                entities=[text]
            )
        elif pattern_type == 'this_week':
            start = now - timedelta(days=now.weekday())
            return TimeExpression(
                text=text,
                start_date=start.replace(hour=0, minute=0, second=0),
                end_date=now,
                confidence=0.8,
                expression_type='relative',
                entities=[text]
            )
        elif pattern_type == 'last_month':
            start = (now.replace(day=1) - timedelta(days=1)).replace(day=1)
            end = now.replace(day=1) - timedelta(seconds=1)
            return TimeExpression(
                text=text,
                start_date=start,
                end_date=end,
                confidence=0.8,
                expression_type='relative',
                entities=[text]
            )
        elif pattern_type == 'this_month':
            start = now.replace(day=1, hour=0, minute=0, second=0)
            return TimeExpression(
                text=text,
                start_date=start,
                end_date=now,
                confidence=0.8,
                expression_type='relative',
                entities=[text]
            )
        elif pattern_type == 'yesterday':
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
            return TimeExpression(
                text=text,
                start_date=start,
                end_date=end,
                confidence=0.9,
                expression_type='relative',
                entities=[text]
            )
        elif pattern_type == 'today':
            start = now.replace(hour=0, minute=0, second=0)
            return TimeExpression(
                text=text,
                start_date=start,
                end_date=now,
                confidence=0.9,
                expression_type='relative',
                entities=[text]
            )
        
        return None
    
    def _parse_with_dateutil(self, text: str) -> List[TimeExpression]:
        """Parse using advanced dateutil features."""
        expressions = []
        
        try:
            # Try parsing with dateutil's fuzzy parsing
            parsed_date = dtparser.parse(text, fuzzy=True)
            # Only add if it's a reasonable date (not too far in future/past)
            now = datetime.now()
            if abs((parsed_date - now).days) < 365 * 10:  # Within 10 years
                expressions.append(TimeExpression(
                    text=text,
                    start_date=parsed_date,
                    end_date=parsed_date,
                    confidence=0.7,
                    expression_type='absolute',
                    entities=[text]
                ))
        except:
            pass
        
        # Try parsing relative expressions
        try:
            # Look for "X days/weeks/months ago" patterns
            for unit, patterns in self.relative_patterns.items():
                for pattern in patterns:
                    if f" {pattern} ago" in text.lower():
                        # Extract number
                        match = re.search(rf'(\d+)\s+{pattern}\s+ago', text.lower())
                        if match:
                            num = int(match.group(1))
                            now = datetime.now()
                            
                            if unit == 'days':
                                start = now - timedelta(days=num)
                                end = now
                            elif unit == 'weeks':
                                start = now - timedelta(weeks=num)
                                end = now
                            elif unit == 'months':
                                # Approximate months as 30 days
                                start = now - timedelta(days=num * 30)
                                end = now
                            elif unit == 'years':
                                # Approximate years as 365 days
                                start = now - timedelta(days=num * 365)
                                end = now
                            else:
                                continue
                            
                            expressions.append(TimeExpression(
                                text=text,
                                start_date=start,
                                end_date=end,
                                confidence=0.8,
                                expression_type='relative',
                                entities=[text]
                            ))
        except:
            pass
        
        return expressions
    
    def _parse_with_context_patterns(self, text: str) -> List[TimeExpression]:
        """Parse using context-aware pattern matching."""
        expressions = []
        text_lower = text.lower()
        
        # Look for "since X" patterns
        since_match = re.search(r'since\s+([^,]+)', text_lower)
        if since_match:
            try:
                since_date = dtparser.parse(since_match.group(1), fuzzy=True)
                expressions.append(TimeExpression(
                    text=text,
                    start_date=since_date,
                    end_date=datetime.now(),
                    confidence=0.8,
                    expression_type='range',
                    entities=[since_match.group(1)]
                ))
            except:
                pass
        
        # Look for "between X and Y" patterns
        between_match = re.search(r'between\s+([^,]+?)\s+and\s+([^,]+)', text_lower)
        if between_match:
            try:
                start_date = dtparser.parse(between_match.group(1), fuzzy=True)
                end_date = dtparser.parse(between_match.group(2), fuzzy=True)
                expressions.append(TimeExpression(
                    text=text,
                    start_date=start_date,
                    end_date=end_date,
                    confidence=0.8,
                    expression_type='range',
                    entities=[between_match.group(1), between_match.group(2)]
                ))
            except:
                pass
        
        return expressions
    
    def _deduplicate_expressions(self, expressions: List[TimeExpression]) -> List[TimeExpression]:
        """Remove duplicate expressions based on similarity."""
        if not expressions:
            return []
        
        unique_expressions = []
        for expr in expressions:
            is_duplicate = False
            for unique_expr in unique_expressions:
                # Check if expressions are similar
                if (abs((expr.start_date or datetime.min) - (unique_expr.start_date or datetime.min)) < timedelta(minutes=1) and
                    abs((expr.end_date or datetime.min) - (unique_expr.end_date or datetime.min)) < timedelta(minutes=1)):
                    is_duplicate = True
                    # Keep the one with higher confidence
                    if expr.confidence > unique_expr.confidence:
                        unique_expressions.remove(unique_expr)
                        unique_expressions.append(expr)
                    break
            
            if not is_duplicate:
                unique_expressions.append(expr)
        
        return unique_expressions
    
    def get_best_time_window(self, text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
        """Get the best time window from parsed expressions."""
        expressions = self.parse_time_expression(text)
        
        if not expressions:
            return None, None
        
        # Return the highest confidence expression
        best_expr = expressions[0]
        return best_expr.start_date, best_expr.end_date


class SemanticQueryMatcher:
    """Semantic matching for query intent classification."""
    
    def __init__(self):
        self.similarity_model = None
        self._initialize_model()
        
        # Query intent patterns
        self.intent_patterns = {
            'count_sent': [
                'how many emails were sent',
                'total emails sent',
                'count of sent emails',
                'number of emails sent'
            ],
            'count_opened': [
                'how many emails were opened',
                'total emails opened',
                'count of opened emails',
                'number of emails opened',
                'open rate'
            ],
            'count_replied': [
                'how many people replied',
                'total replies',
                'count of replies',
                'number of replies',
                'reply rate'
            ],
            'count_bounced': [
                'how many emails bounced',
                'total bounces',
                'count of bounces',
                'number of bounces',
                'bounce rate'
            ],
            'group_by_domain': [
                'grouped by domain',
                'by domain',
                'per domain',
                'domain breakdown'
            ]
        }
    
    def _initialize_model(self):
        """Initialize the semantic similarity model."""
        if SENTENCE_TRANSFORMERS_AVAILABLE:
            try:
                self.similarity_model = SentenceTransformer('all-MiniLM-L6-v2')
            except Exception as e:
                warnings.warn(f"Could not load sentence transformer: {e}")
    
    def classify_intent(self, query: str) -> Dict[str, float]:
        """Classify query intent using semantic similarity."""
        if not self.similarity_model:
            return {}
        
        query_lower = query.lower()
        intent_scores = {}
        
        try:
            query_embedding = self.similarity_model.encode([query_lower])
            
            for intent, patterns in self.intent_patterns.items():
                pattern_embeddings = self.similarity_model.encode(patterns)
                similarities = cosine_similarity(query_embedding, pattern_embeddings)[0]
                max_similarity = max(similarities)
                intent_scores[intent] = max_similarity
        except Exception as e:
            warnings.warn(f"Intent classification failed: {e}")
        
        return intent_scores
    
    def get_best_intent(self, query: str) -> Tuple[Optional[str], float]:
        """Get the best matching intent."""
        scores = self.classify_intent(query)
        if not scores:
            return None, 0.0
        
        best_intent = max(scores.items(), key=lambda x: x[1])
        return best_intent if best_intent[1] > 0.6 else (None, 0.0)


# Global instances
time_parser = AdvancedTimeParser()
query_matcher = SemanticQueryMatcher()


def parse_time_advanced(text: str) -> Tuple[Optional[datetime], Optional[datetime]]:
    """Parse time expressions using advanced NLP."""
    return time_parser.get_best_time_window(text)


def classify_query_intent(query: str) -> Tuple[Optional[str], float]:
    """Classify query intent using semantic similarity."""
    return query_matcher.get_best_intent(query)


__all__ = [
    "AdvancedTimeParser", "TimeExpression", "SemanticQueryMatcher",
    "parse_time_advanced", "classify_query_intent"
]
