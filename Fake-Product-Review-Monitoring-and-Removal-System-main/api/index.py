import json
from datetime import datetime

# Simple fake review detector (embedded to avoid import issues)
class FakeReviewDetector:
    def __init__(self):
        self.generic_phrases = [
            'best product ever', 'highly recommend', 'amazing product',
            'must buy', 'life changing', 'perfect', 'awesome',
            'excellent', 'worst ever', 'terrible product', 'waste of money',
            'don\'t buy', 'save your money', 'total scam'
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
        score = 0
        features = {
            'suspicious_patterns': [],
            'positive_indicators': [],
            'warnings': []
        }

        # Simple analysis
        text_lower = review_text.lower()

        # Check for generic phrases
        found_phrases = [phrase for phrase in self.generic_phrases if phrase in text_lower]
        if len(found_phrases) > 1:
            features['suspicious_patterns'].append('Multiple generic phrases')
            score += 25

        # Check sentiment vs rating
        pos_count = sum(1 for word in self.positive_words if word in text_lower)
        neg_count = sum(1 for word in self.negative_words if word in text_lower)

        if rating >= 4 and neg_count > pos_count:
            features['suspicious_patterns'].append('Rating-content mismatch')
            score += 35
        elif rating <= 2 and pos_count > neg_count:
            features['suspicious_patterns'].append('Rating-content mismatch')
            score += 35

        # Length check
        if len(review_text) < 20:
            features['suspicious_patterns'].append('Very short review')
            score += 30

        # Determine prediction
        if score >= 60:
            prediction = 'fake'
            confidence = 85
        elif score >= 30:
            prediction = 'suspicious'
            confidence = 65
        else:
            prediction = 'genuine'
            confidence = 80

        return {
            'prediction': prediction,
            'confidence': confidence,
            'score': score,
            'features': features
        }


# Vercel serverless function
reviews_storage = []

def handler(event, context):
    return {
        'statusCode': 200,
        'headers': {'Content-Type': 'application/json'},
        'body': json.dumps(event)
    }


def handle_analyze(data):
    """Handle review analysis"""
    try:
        if not data or 'text' not in data or 'rating' not in data:
            return {
                'statusCode': 400,
                'headers': {'Content-Type': 'application/json'},
                'body': json.dumps({
                    'success': False,
                    'error': 'Missing required fields: text and rating'
                })
            }

        detector = FakeReviewDetector()
        analysis = detector.analyze_review(data['text'], int(data['rating']))

        review = {
            'id': len(reviews_storage) + 1,
            'product': data.get('product', 'Unknown'),
            'reviewer': data.get('reviewer', 'Anonymous'),
            'rating': int(data['rating']),
            'text': data['text'],
            'prediction': analysis['prediction'],
            'confidence': analysis['confidence'],
            'features': analysis['features'],
            'timestamp': datetime.now().isoformat()
        }

        reviews_storage.append(review)

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'review': review
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


def handle_get_reviews(query_params):
    """Handle get reviews"""
    try:
        product = query_params.get('product')
        prediction = query_params.get('prediction')

        filtered_reviews = reviews_storage

        if product and product != 'all':
            filtered_reviews = [r for r in filtered_reviews if r['product'] == product]

        if prediction and prediction != 'all':
            filtered_reviews = [r for r in filtered_reviews if r['prediction'] == prediction]

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'count': len(filtered_reviews),
                'reviews': filtered_reviews
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


def handle_statistics():
    """Handle statistics"""
    try:
        total_reviews = len(reviews_storage)
        fake_count = sum(1 for r in reviews_storage if r['prediction'] == 'fake')
        genuine_count = sum(1 for r in reviews_storage if r['prediction'] == 'genuine')
        suspicious_count = sum(1 for r in reviews_storage if r['prediction'] == 'suspicious')

        stats = {
            'total_reviews': total_reviews,
            'fake_reviews': fake_count,
            'genuine_reviews': genuine_count,
            'suspicious_reviews': suspicious_count,
            'fake_percentage': round((fake_count / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'genuine_percentage': round((genuine_count / total_reviews * 100) if total_reviews > 0 else 0, 1),
            'suspicious_percentage': round((suspicious_count / total_reviews * 100) if total_reviews > 0 else 0, 1)
        }

        products = list(set(r['product'] for r in reviews_storage))

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'statistics': stats,
                'products': products
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }


def handle_clear():
    """Handle clear all reviews"""
    try:
        count = len(reviews_storage)
        reviews_storage.clear()

        return {
            'statusCode': 200,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': True,
                'message': f'Cleared {count} reviews'
            })
        }

    except Exception as e:
        return {
            'statusCode': 500,
            'headers': {'Content-Type': 'application/json'},
            'body': json.dumps({
                'success': False,
                'error': str(e)
            })
        }
