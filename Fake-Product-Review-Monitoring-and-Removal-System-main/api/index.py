from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import json
from datetime import datetime
from model import FakeReviewDetector, analyze_batch_reviews, get_statistics

app = Flask(__name__)
CORS(app)

# In-memory storage for reviews (in production, use a database)
reviews_storage = []


@app.route('/')
def index():
    """Render the main page"""
    return render_template('index.html')


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


@app.route('/api/analyze-batch', methods=['POST'])
def analyze_batch():
    """
    Analyze multiple reviews at once

    Expected JSON format:
    {
        "reviews": [
            {
                "product": "Product Name",
                "reviewer": "Reviewer Name",
                "rating": 5,
                "text": "Review text"
            },
            ...
        ]
    }
    """
    try:
        data = request.get_json()

        if not data or 'reviews' not in data:
            return jsonify({
                'success': False,
                'error': 'Missing reviews array'
            }), 400

        reviews = data['reviews']

        if not isinstance(reviews, list) or len(reviews) == 0:
            return jsonify({
                'success': False,
                'error': 'Reviews must be a non-empty array'
            }), 400

        # Analyze all reviews
        analyzed_reviews = analyze_batch_reviews(reviews)

        # Store all analyzed reviews
        for review in analyzed_reviews:
            review['id'] = len(reviews_storage) + 1
            review['timestamp'] = datetime.now().isoformat()
            reviews_storage.append(review)

        return jsonify({
            'success': True,
            'count': len(analyzed_reviews),
            'reviews': analyzed_reviews
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


@app.route('/api/reviews/<int:review_id>', methods=['DELETE'])
def delete_review(review_id):
    """Delete a specific review"""
    try:
        global reviews_storage

        # Find and remove the review
        reviews_storage = [r for r in reviews_storage if r['id'] != review_id]

        return jsonify({
            'success': True,
            'message': 'Review deleted successfully'
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'error': str(e)
        }), 500


@app.route('/api/reviews/bulk-delete', methods=['POST'])
def bulk_delete():
    """Delete multiple reviews based on prediction type"""
    try:
        data = request.get_json()
        prediction_type = data.get('prediction', 'fake')

        global reviews_storage

        # Count reviews to be deleted
        before_count = len(reviews_storage)

        # Remove reviews matching the prediction type
        reviews_storage = [r for r in reviews_storage if r['prediction'] != prediction_type]

        after_count = len(reviews_storage)
        deleted_count = before_count - after_count

        return jsonify({
            'success': True,
            'deleted_count': deleted_count,
            'message': f'Deleted {deleted_count} {prediction_type} reviews'
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
        stats = get_statistics(reviews_storage)

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


# Vercel expects a function named 'app' for serverless functions
# This is the entry point for Vercel
def handler(event, context):
    # For Vercel, we need to handle the request differently
    # This is a basic handler that delegates to Flask
    from werkzeug.wrappers import Request
    from werkzeug.serving import make_server

    # Create a WSGI application
    wsgi_app = app.wsgi_app

    # Handle the request
    request = Request(event)
    response = wsgi_app(request.environ, lambda s, h: None)

    return {
        'statusCode': response.status_code,
        'headers': dict(response.headers),
        'body': response.get_data(as_text=True)
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
