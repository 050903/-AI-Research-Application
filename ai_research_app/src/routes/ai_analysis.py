from flask import Blueprint, request, jsonify
from flask_cors import cross_origin
import cv2
import numpy as np
from PIL import Image
import io
import base64
import requests
from bs4 import BeautifulSoup
from transformers import pipeline, BlipProcessor, BlipForConditionalGeneration
import torch

ai_analysis_bp = Blueprint('ai_analysis', __name__)

# Initialize models (these will be loaded on first use to save memory)
image_captioning_model = None
image_captioning_processor = None

def get_image_captioning_model():
    global image_captioning_model, image_captioning_processor
    if image_captioning_model is None:
        image_captioning_processor = BlipProcessor.from_pretrained("Salesforce/blip-image-captioning-base")
        image_captioning_model = BlipForConditionalGeneration.from_pretrained("Salesforce/blip-image-captioning-base")
    return image_captioning_model, image_captioning_processor

@ai_analysis_bp.route('/analyze_image', methods=['POST'])
@cross_origin()
def analyze_image():
    """Analyze an uploaded image using computer vision techniques."""
    try:
        if 'image' not in request.files:
            return jsonify({'error': 'No image file provided'}), 400
        
        file = request.files['image']
        if file.filename == '':
            return jsonify({'error': 'No image file selected'}), 400
        
        # Read image
        image_bytes = file.read()
        image = Image.open(io.BytesIO(image_bytes))
        
        # Convert to OpenCV format for basic analysis
        opencv_image = cv2.cvtColor(np.array(image), cv2.COLOR_RGB2BGR)
        
        # Basic image properties
        height, width, channels = opencv_image.shape
        
        # Generate image caption using BLIP model
        model, processor = get_image_captioning_model()
        inputs = processor(image, return_tensors="pt")
        out = model.generate(**inputs, max_length=50)
        caption = processor.decode(out[0], skip_special_tokens=True)
        
        # Basic color analysis
        mean_color = np.mean(opencv_image, axis=(0, 1))
        
        # Edge detection
        gray = cv2.cvtColor(opencv_image, cv2.COLOR_BGR2GRAY)
        edges = cv2.Canny(gray, 100, 200)
        edge_count = np.count_nonzero(edges)
        
        analysis_result = {
            'dimensions': {'width': width, 'height': height, 'channels': channels},
            'caption': caption,
            'mean_color': {
                'blue': float(mean_color[0]),
                'green': float(mean_color[1]),
                'red': float(mean_color[2])
            },
            'edge_density': float(edge_count / (width * height)),
            'analysis_type': 'image_recognition'
        }
        
        return jsonify(analysis_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_analysis_bp.route('/analyze_website', methods=['POST'])
@cross_origin()
def analyze_website():
    """Analyze a website URL and extract key information."""
    try:
        data = request.get_json()
        if not data or 'url' not in data:
            return jsonify({'error': 'No URL provided'}), 400
        
        url = data['url']
        
        # Fetch website content
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        
        # Parse HTML content
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract basic information
        title = soup.find('title')
        title_text = title.get_text().strip() if title else 'No title found'
        
        # Extract meta description
        meta_desc = soup.find('meta', attrs={'name': 'description'})
        description = meta_desc.get('content', 'No description found') if meta_desc else 'No description found'
        
        # Extract headings
        headings = []
        for i in range(1, 7):
            h_tags = soup.find_all(f'h{i}')
            for h in h_tags[:5]:  # Limit to first 5 of each type
                headings.append({
                    'level': i,
                    'text': h.get_text().strip()
                })
        
        # Extract main text content
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()
        
        text_content = soup.get_text()
        # Clean up text
        lines = (line.strip() for line in text_content.splitlines())
        chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
        text_content = ' '.join(chunk for chunk in chunks if chunk)
        
        # Limit text content length
        if len(text_content) > 2000:
            text_content = text_content[:2000] + "..."
        
        # Extract links
        links = []
        for link in soup.find_all('a', href=True)[:10]:  # Limit to first 10 links
            links.append({
                'text': link.get_text().strip(),
                'url': link['href']
            })
        
        analysis_result = {
            'url': url,
            'title': title_text,
            'description': description,
            'headings': headings,
            'text_content': text_content,
            'links': links,
            'analysis_type': 'website_analysis'
        }
        
        return jsonify(analysis_result)
        
    except requests.RequestException as e:
        return jsonify({'error': f'Failed to fetch website: {str(e)}'}), 400
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_analysis_bp.route('/answer_question', methods=['POST'])
@cross_origin()
def answer_question():
    """Answer questions using a simple knowledge base approach."""
    try:
        data = request.get_json()
        if not data or 'question' not in data:
            return jsonify({'error': 'No question provided'}), 400
        
        question = data['question'].lower()
        
        # Simple knowledge base for AI/ML/DL topics
        knowledge_base = {
            'machine learning': 'Machine Learning is a subset of artificial intelligence that enables computers to learn and make decisions from data without being explicitly programmed for every task.',
            'deep learning': 'Deep Learning is a subset of machine learning that uses neural networks with multiple layers to model and understand complex patterns in data.',
            'neural network': 'A Neural Network is a computing system inspired by biological neural networks. It consists of interconnected nodes (neurons) that process information.',
            'computer vision': 'Computer Vision is a field of AI that enables computers to interpret and understand visual information from the world, such as images and videos.',
            'natural language processing': 'Natural Language Processing (NLP) is a branch of AI that helps computers understand, interpret, and generate human language.',
            'artificial intelligence': 'Artificial Intelligence (AI) is the simulation of human intelligence in machines that are programmed to think and learn like humans.',
            'convolutional neural network': 'A Convolutional Neural Network (CNN) is a type of deep learning model particularly effective for image recognition and computer vision tasks.',
            'transformer': 'Transformers are a type of neural network architecture that has revolutionized natural language processing and is the foundation of modern language models.',
            'llm': 'Large Language Models (LLMs) are AI systems trained on vast amounts of text data to understand and generate human-like text.',
            'opencv': 'OpenCV is a library of programming functions mainly aimed at real-time computer vision and image processing.',
            'pytorch': 'PyTorch is an open-source machine learning framework that provides a flexible platform for deep learning research and production.',
            'tensorflow': 'TensorFlow is an open-source machine learning framework developed by Google for building and deploying ML models.'
        }
        
        # Find the best match
        best_match = None
        best_score = 0
        
        for key, value in knowledge_base.items():
            if key in question:
                score = len(key)
                if score > best_score:
                    best_score = score
                    best_match = value
        
        if best_match:
            answer = best_match
        else:
            answer = "I'm sorry, I don't have specific information about that topic in my current knowledge base. Please try asking about machine learning, deep learning, neural networks, computer vision, or related AI topics."
        
        analysis_result = {
            'question': data['question'],
            'answer': answer,
            'analysis_type': 'question_answering'
        }
        
        return jsonify(analysis_result)
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@ai_analysis_bp.route('/health', methods=['GET'])
@cross_origin()
def health_check():
    """Health check endpoint."""
    return jsonify({'status': 'healthy', 'service': 'AI Analysis API'})

