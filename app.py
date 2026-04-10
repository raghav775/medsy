from flask import Flask, render_template, request, jsonify
from flask_cors import CORS
import os

from engine.ocr import extract_medicines_from_file
from engine.probability import rank_pharmacies

app = Flask(__name__)
CORS(app)
app.config['UPLOAD_FOLDER'] = 'static/uploads'
app.config['MAX_CONTENT_LENGTH'] = 20 * 1024 * 1024
ALLOWED_EXTENSIONS = {'pdf', 'png', 'jpg', 'jpeg', 'txt', 'docx', 'doc'}

os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/api/ocr', methods=['POST'])
def ocr_prescription():
    if 'file' not in request.files:
        return jsonify({'error': 'No file uploaded'}), 400
    file = request.files['file']
    if not file.filename or not allowed_file(file.filename):
        return jsonify({'error': 'Unsupported file type'}), 400

    filepath = os.path.join(app.config['UPLOAD_FOLDER'], file.filename)
    file.save(filepath)
    try:
        medicines = extract_medicines_from_file(filepath)
        return jsonify({'medicines': medicines, 'filename': file.filename})
    except Exception as e:
        return jsonify({'error': str(e)}), 500
    finally:
        if os.path.exists(filepath):
            os.remove(filepath)


@app.route('/api/rank', methods=['POST'])
def rank():
    data     = request.get_json()
    selected = data.get('medicines', [])
    user_lat = float(data.get('lat', 28.5733))
    user_lng = float(data.get('lng', 77.2236))
    if not selected:
        return jsonify({'error': 'No medicines selected'}), 400
    results = rank_pharmacies(selected, user_lat, user_lng)
    return jsonify({'pharmacies': results})


if __name__ == '__main__':
    app.run(debug=True, port=5000)
