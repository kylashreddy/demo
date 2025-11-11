from flask import Flask, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from model import FakeReviewDetector

app = Flask(__name__)
CORS(app)

# In-memory storage for reviews (in production, use a database)
reviews_storage = []


@app.route('/api/analyze', methods=['POST'])
def analyze_review():
    """
    Analyze a single review

    Expected JSON format:
    {
        "product": "Product Name",
        "reviewer": "Reviewer Name",
        "rating": 5,
        "text": "Review text here"
    }
    """
    try:
        data = request.get_json()

        # Validate input
        if not data or 'text' not in data or 'rating' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing required fields: text and rating'
            }), 400

        # Create detector instance
        detector = FakeReviewDetector()

        # Analyze the review
        analysis = detector.analyze_review(data['text'], int(data['rating']))

        # Create review object
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

        # Store the review
        reviews_storage.append(review)

        return jsonify({
            'success': True,
            'review': review
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviews', methods=['GET'])
def get_reviews():
    """Get all stored reviews"""
    try:
        # Get query parameters for filtering
        product = request.args.get('product')
        prediction = request.args.get('prediction')

        filtered_reviews = reviews_storage

        # Filter by product
        if product and product != 'all':
            filtered_reviews = [r for r in filtered_reviews if r['product'] == product]

        # Filter by prediction
        if prediction and prediction != 'all':
            filtered_reviews = [r for r in filtered_reviews if r['prediction'] == prediction]

        return jsonify({
            'success': True,
            'count': len(filtered_reviews),
            'reviews': filtered_reviews
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/statistics', methods=['GET'])
def get_stats():
    """Get statistics about stored reviews"""
    try:
        # Calculate basic statistics
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

        # Get product list
        products = list(set(r['product'] for r in reviews_storage))

        return jsonify({
            'success': True,
            'statistics': stats,
            'products': products
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/clear', methods=['POST'])
def clear_all():
    """Clear all stored reviews"""
    try:
        global reviews_storage
        count = len(reviews_storage)
        reviews_storage = []

        return jsonify({
            'success': True,
            'message': f'Cleared {count} reviews'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.errorhandler(404)
def not_found(error):
    """Handle 404 errors"""
    return jsonify({
        'success': False,
        'error': 'Endpoint not found'
    }), 404


@app.errorhandler(500)
def internal_error(error):
    """Handle 500 errors"""
    return jsonify({
        'success': False,
        'error': 'Internal server error'
    }), 500


# Vercel serverless function handler
def handler(event, context):
    """Vercel serverless function handler"""
    try:
        from werkzeug.wrappers import Request
        from werkzeug.test import EnvironBuilder

        # Build WSGI environment from Vercel event
        if 'requestContext' in event:  # API Gateway format
            method = event.get('httpMethod', 'GET')
            path = event.get('path', '/')
            headers = event.get('headers', {})
            body = event.get('body', '')
            query_params = event.get('queryStringParameters', {}) or {}
        else:  # Vercel format
            method = event.get('method', 'GET')
            path = event.get('path', '/')
            headers = event.get('headers', {})
            body = event.get('body', '')
            query_params = event.get('query', {}) or {}

        # Build query string
        query_string = '&'.join([f"{k}={v}" for k, v in query_params.items()])

        # Create WSGI environment
        builder = EnvironBuilder(
            method=method,
            path=path,
            query_string=query_string,
            headers=headers,
            data=body if body else None
        )
        env = builder.get_environ()

        # Create response collector
        response_data = []

        def start_response(status, response_headers, exc_info=None):
            response_data.append((status, response_headers))

        # Call WSGI app
        result = app.wsgi_app(env, start_response)

        # Get response
        status, headers = response_data[0]
        response_body = b''.join(result).decode('utf-8')

        # Parse status code
        status_code = int(status.split()[0])

        # Convert headers to dict
        response_headers = {k: v for k, v in headers}

        return {
            'statusCode': status_code,
            'headers': response_headers,
            'body': response_body
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


if __name__ == '__main__':
    import os
    print("=" * 60)
    print("🔍 Opinion Mining Based Fake Review Detection System")
    print("=" * 60)
    port = int(os.environ.get('PORT', 5000))
    print(f"Server starting on port {port}")
    print("Press CTRL+C to quit")
    print("=" * 60)
    app.run(debug=False, host='0.0.0.0', port=port)
