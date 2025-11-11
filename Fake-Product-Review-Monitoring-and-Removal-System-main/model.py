"""
Opinion Mining Based Fake Review Detection Model
This module contains all the logic for analyzing and detecting fake reviews
"""

import re
import nltk
from textblob import TextBlob
from collections import Counter

# Download required NLTK data
try:
    nltk.download('punkt', quiet=True)
    nltk.download('stopwords', quiet=True)
    nltk.download('vader_lexicon', quiet=True)
except:
    pass


class FakeReviewDetector:
    """
    Main class for detecting fake product reviews using opinion mining techniques
    """
    
    def __init__(self):
        self.generic_phrases = [
            'best product ever', 'highly recommend', 'amazing product',
            'must buy', 'life changing', 'perfect', 'awesome',
            'excellent', 'worst ever', 'terrible product', 'waste of money',
            'don\'t buy', 'save your money', 'total scam'
        ]
        
        self.spam_patterns = [
            r'http[s]?://',
            r'www\.',
            r'\.com',
            r'click here',
            r'buy now',
            r'limited offer',
            r'discount code'
        ]
        
        self.positive_words = [
            'good', 'great', 'excellent', 'love', 'best', 'amazing',
            'wonderful', 'fantastic', 'perfect', 'awesome', 'outstanding'
        ]
        
        self.negative_words = [
            'bad', 'poor', 'terrible', 'worst', 'hate', 'disappointed',
            'awful', 'horrible', 'useless', 'waste', 'regret'
        ]
    
    def analyze_review(self, review_text, rating):
        """
        Analyze a single review and return prediction with confidence score
        
        Args:
            review_text (str): The review text to analyze
            rating (int): The rating given (1-5)
            
        Returns:
            dict: Analysis results including prediction, confidence, and features
        """
        score = 0
        features = {
            'suspicious_patterns': [],
            'positive_indicators': [],
            'warnings': []
        }
        
        # Feature 1: Review Length Analysis
        score += self._analyze_length(review_text, features)
        
        # Feature 2: Punctuation Analysis
        score += self._analyze_punctuation(review_text, features)
        
        # Feature 3: Capitalization Analysis
        score += self._analyze_capitalization(review_text, features)
        
        # Feature 4: Generic Phrases Detection
        score += self._detect_generic_phrases(review_text, features)
        
        # Feature 5: Sentiment Analysis
        score += self._analyze_sentiment(review_text, rating, features)
        
        # Feature 6: Spam Pattern Detection
        score += self._detect_spam_patterns(review_text, features)
        
        # Feature 7: Repeated Characters
        score += self._detect_repeated_chars(review_text, features)
        
        # Feature 8: Word Diversity
        score += self._analyze_word_diversity(review_text, features)
        
        # Determine final prediction
        prediction, confidence = self._calculate_prediction(score)
        
        return {
            'prediction': prediction,
            'confidence': round(confidence, 1),
            'score': score,
            'features': features
        }
    
    def _analyze_length(self, text, features):
        """Analyze review length"""
        length = len(text)
        
        if length < 20:
            features['suspicious_patterns'].append('Very short review')
            return 30
        elif length > 100:
            features['positive_indicators'].append('Detailed review')
            return -10
        return 0
    
    def _analyze_punctuation(self, text, features):
        """Detect excessive punctuation"""
        exclamation_count = text.count('!')
        question_count = text.count('?')
        
        score = 0
        if exclamation_count > 3:
            features['suspicious_patterns'].append(f'Excessive exclamation marks ({exclamation_count})')
            score += 20
        
        if question_count > 3:
            features['suspicious_patterns'].append(f'Too many questions ({question_count})')
            score += 10
        
        return score
    
    def _analyze_capitalization(self, text, features):
        """Detect excessive capitalization"""
        words = text.split()
        caps_words = [w for w in words if w.isupper() and len(w) > 3]
        
        if len(caps_words) > 2:
            features['suspicious_patterns'].append(f'Excessive capitalization ({len(caps_words)} words)')
            return 15
        return 0
    
    def _detect_generic_phrases(self, text, features):
        """Detect generic/template phrases"""
        text_lower = text.lower()
        found_phrases = [phrase for phrase in self.generic_phrases if phrase in text_lower]
        
        if len(found_phrases) > 2:
            features['suspicious_patterns'].append(f'Multiple generic phrases: {", ".join(found_phrases[:3])}')
            return 25
        elif len(found_phrases) > 0:
            features['warnings'].append(f'Generic phrase detected: {found_phrases[0]}')
            return 10
        return 0
    
    def _analyze_sentiment(self, text, rating, features):
        """Analyze sentiment and check for rating mismatch"""
        text_lower = text.lower()
        
        pos_count = sum(1 for word in self.positive_words if word in text_lower)
        neg_count = sum(1 for word in self.negative_words if word in text_lower)
        
        try:
            blob = TextBlob(text)
            polarity = blob.sentiment.polarity
        except:
            polarity = 0
        
        score = 0
        if rating >= 4 and (neg_count > pos_count or polarity < -0.2):
            features['suspicious_patterns'].append('Rating-content mismatch (high rating, negative content)')
            score += 35
        elif rating <= 2 and (pos_count > neg_count or polarity > 0.2):
            features['suspicious_patterns'].append('Rating-content mismatch (low rating, positive content)')
            score += 35
        else:
            features['positive_indicators'].append('Rating matches sentiment')
        
        return score
    
    def _detect_spam_patterns(self, text, features):
        """Detect spam and promotional content"""
        score = 0
        found_patterns = []
        
        for pattern in self.spam_patterns:
            if re.search(pattern, text, re.IGNORECASE):
                found_patterns.append(pattern.replace('\\', ''))
        
        if found_patterns:
            features['suspicious_patterns'].append(f'Contains promotional content: {", ".join(found_patterns[:2])}')
            score += 40
        
        return score
    
    def _detect_repeated_chars(self, text, features):
        """Detect repeated characters (e.g., 'sooooo', 'greatttt')"""
        pattern = r'(.)\1{4,}'
        matches = re.findall(pattern, text)
        
        if matches:
            features['suspicious_patterns'].append(f'Repeated characters detected')
            return 20
        return 0
    
    def _analyze_word_diversity(self, text, features):
        """Analyze vocabulary diversity"""
        words = text.lower().split()
        if len(words) < 5:
            return 0
        
        unique_words = len(set(words))
        total_words = len(words)
        diversity_ratio = unique_words / total_words
        
        if diversity_ratio < 0.5 and total_words > 20:
            features['suspicious_patterns'].append('Low vocabulary diversity')
            return 15
        elif diversity_ratio > 0.8:
            features['positive_indicators'].append('High vocabulary diversity')
        
        return 0
    
    def _calculate_prediction(self, score):
        """Calculate final prediction and confidence"""
        if score >= 60:
            prediction = 'fake'
            confidence = min(95, 60 + score / 2)
        elif score >= 30:
            prediction = 'suspicious'
            confidence = 50 + score / 2
        else:
            prediction = 'genuine'
            confidence = 100 - score * 2
        
        return prediction, max(50, min(99, confidence))


# Example usage:
if __name__ == "__main__":
    detector = FakeReviewDetector()
    review = "This is the best product ever! I love it! Highly recommend to everyone!!!"
    result = detector.analyze_review(review, rating=5)
    print(result)
