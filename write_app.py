content = """from flask import Flask, render_template, request
from PyPDF2 import PdfReader
from nltk.tokenize import sent_tokenize, word_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
import re, nltk, urllib.request

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

from nltk.corpus import stopwords

app = Flask(__name__)
STOP_WORDS = set(stopwords.words('english'))

FEATURED_BOOKS = [
    {"title": "Pride and Prejudice", "author": "Jane Austen", "category": "Romance", "emoji": "💕", "color": "#c8860a", "url": "https://www.gutenberg.org/files/1342/1342-0.txt", "rating": "4.9"},
    {"title": "Frankenstein", "author": "Mary Shelley", "category": "Horror", "emoji": "👹", "color": "#2c3e50", "url": "https://www.gutenberg.org/files/84/84-0.txt", "rating": "4.8"},
    {"title": "Alice in Wonderland", "author": "Lewis Carroll", "category": "Fantasy", "emoji": "🐇", "color": "#7d3c98", "url": "https://www.gutenberg.org/files/11/11-0.txt", "rating": "4.8"},
    {"title": "Moby Dick", "author": "Herman Melville", "category": "Adventure", "emoji": "🐋", "color": "#1a6b5a", "url": "https://www.gutenberg.org/files/2701/2701-0.txt", "rating": "4.6"},
    {"title": "Romeo and Juliet", "author": "William Shakespeare", "category": "Tragedy", "emoji": "🌹", "color": "#8b3a0f", "url": "https://www.gutenberg.org/files/1513/1513-0.txt", "rating": "4.9"},
    {"title": "Dracula", "author": "Bram Stoker", "category": "Horror", "emoji": "🧛", "color": "#6c0a0a", "url": "https://www.gutenberg.org/files/345/345-0.txt", "rating": "4.7"},
    {"title": "The Odyssey", "author": "Homer", "category": "Epic", "emoji": "⚔️", "color": "#5a6e1f", "url": "https://www.gutenberg.org/files/1727/1727-0.txt", "rating": "4.8"},
    {"title": "Great Expectations", "author": "Charles Dickens", "category": "Classic", "emoji": "🎩", "color": "#1a5276", "url": "https://www.gutenberg.org/files/1400/1400-0.txt", "rating": "4.7"}
]

def fetch_gutenberg(url):
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=15) as r:
        return r.read().decode('utf-8', errors='ignore')

def extract_text(file):
    if file.filename.endswith('.pdf'):
        reader = PdfReader(file)
        return ' '.join(page.extract_text() for page in reader.pages)
    return file.read().decode('utf-8')

def clean_text(text):
    text = re.sub(r'\\*\\*\\*.*?\\*\\*\\*', '', text, flags=re.DOTALL)
    text = re.sub(r'CHAPTER\\s+[A-Z0-9]+.*?\\n', '', text)
    text = re.sub(r'\\s+', ' ', text)
    return text.strip()

def summarize(sentences, n=10):
    words = [w.lower() for s in sentences for w in word_tokenize(s)
             if w.isalpha() and w.lower() not in STOP_WORDS]
    freq = Counter(words)
    scores = {s: sum(freq.get(w.lower(), 0) for w in word_tokenize(s) if w.isalpha()) for s in sentences}
    return sorted(sentences, key=lambda s: scores.get(s, 0), reverse=True)[:n]

def extract_characters(sentences, n=10):
    candidates = []
    for s in sentences:
        for w in s.split():
            clean = re.sub(r'[^a-zA-Z]', '', w)
            if clean and clean[0].isupper() and len(clean) > 2 and clean.lower() not in STOP_WORDS:
                candidates.append(clean)
    return Counter(candidates).most_common(n)

def emotional_arc(text, chunks=10):
    analyzer = SentimentIntensityAnalyzer()
    words = text.split()
    size = max(1, len(words) // chunks)
    arc = []
    for i in range(chunks):
        chunk = ' '.join(words[i*size:(i+1)*size])
        arc.append(round(analyzer.polarity_scores(chunk)['compound'], 3))
    return arc

def generate_quiz(summary):
    quiz = []
    for s in summary[:5]:
        words = s.split()
        if len(words) > 6:
            mid = len(words) // 2
            question = ' '.join(words[:mid]) + ' ______?'
            quiz.append({'question': question, 'answer': s})
    return quiz

def analyze_text(text, persona='student', length=2):
    n_sentences = {1: 5, 2: 10, 3: 15}.get(length, 10)
    text = clean_text(text)
    sentences = sent_tokenize(text)
    summary = summarize(sentences, n=n_sentences)
    characters = extract_characters(sentences)
    analyzer = SentimentIntensityAnalyzer()
    sentiment = analyzer.polarity_scores(text[:10000])
    arc = emotional_arc(text)
    quiz = generate_quiz(summary)
    mood = 'Positive 😊' if sentiment['compound'] >= 0.05 else 'Negative 😞' if sentiment['compound'] <= -0.05 else 'Neutral 😐'
    return dict(summary=summary, characters=characters, sentiment=sentiment, mood=mood, arc=arc, quiz=quiz, persona=persona)

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        file = request.files.get('file')
        persona = request.form.get('persona', 'student')
        length = int(request.form.get('length', 2))
        if not file or file.filename == '':
            return render_template('index.html', error='Please upload a file.', books=FEATURED_BOOKS)
        raw = extract_text(file)
        results = analyze_text(raw, persona, length)
        return render_template('results.html', **results)
    return render_template('index.html', books=FEATURED_BOOKS)

@app.route('/featured/<int:book_id>')
def featured(book_id):
    if book_id >= len(FEATURED_BOOKS):
        return render_template('index.html', books=FEATURED_BOOKS, error='Book not found.')
    book = FEATURED_BOOKS[book_id]
    try:
        raw = fetch_gutenberg(book['url'])
        results = analyze_text(raw, persona='student', length=2)
        results['book_title'] = book['title']
        results['book_author'] = book['author']
        return render_template('results.html', **results)
    except Exception as e:
        return render_template('index.html', books=FEATURED_BOOKS, error=f'Could not load book: {str(e)}')

if __name__ == '__main__':
    app.run(debug=True)
"""

with open("app.py", "w") as f:
    f.write(content)
print("app.py written successfully!")
