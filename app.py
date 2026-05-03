from flask_mail import Mail, Message
import random, string
from datetime import datetime, timedelta
from flask import Flask, render_template, request, redirect, url_for, flash, session, jsonify
from PyPDF2 import PdfReader
from nltk.tokenize import sent_tokenize, word_tokenize
from vaderSentiment.vaderSentiment import SentimentIntensityAnalyzer
from collections import Counter
from flask_bcrypt import Bcrypt
from functools import wraps
import re, nltk, urllib.request, urllib.parse, pymysql, os, json, random

nltk.download('punkt')
nltk.download('stopwords')
nltk.download('punkt_tab')

from nltk.corpus import stopwords

app = Flask(__name__)
app.secret_key = 'bookease_secret_key_2024'
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = 'your_gmail@gmail.com'
app.config['MAIL_PASSWORD'] = 'your_16_digit_app_password'
app.config['MAIL_DEFAULT_SENDER'] = 'your_gmail@gmail.com'
mail = Mail(app)
bcrypt = Bcrypt(app)
STOP_WORDS = set(stopwords.words('english'))

# ─── DATABASE ───────────────────────────────────────────
def get_db():
    return pymysql.connect(
        unix_socket='/tmp/mysql.sock',
        user='root',
        password='root123',
        database='bookease',
        cursorclass=pymysql.cursors.DictCursor
    )

# ─── DECORATORS ─────────────────────────────────────────
def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please login first!', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated

def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if 'user_id' not in session:
            return redirect(url_for('login'))
        if not session.get('is_admin'):
            flash('Admin access required!', 'error')
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated

# ─── FEATURED BOOKS ─────────────────────────────────────
FEATURED_BOOKS = [
    {"title": "Pride and Prejudice", "author": "Jane Austen", "category": "Romance", "emoji": "💕", "color": "#c8860a",
     "cover": "https://i.pinimg.com/1200x/fa/3c/a9/fa3ca9871168fc20422e04d637118b07.jpg",
     "url": "https://www.gutenberg.org/files/1342/1342-0.txt", "rating": "4.9"},
    {"title": "Frankenstein", "author": "Mary Shelley", "category": "Horror", "emoji": "👹", "color": "#2c3e50",
     "cover": "https://i.pinimg.com/736x/b5/c8/0e/b5c80e1aeac655a222eea9a56663a9bb.jpg",
     "url": "https://www.gutenberg.org/files/84/84-0.txt", "rating": "4.8"},
    {"title": "Alice in Wonderland", "author": "Lewis Carroll", "category": "Fantasy", "emoji": "🐇", "color": "#7d3c98",
     "cover": "https://i.pinimg.com/1200x/86/8d/b5/868db593032a5620a62e8b7fa00d19c5.jpg",
     "url": "https://www.gutenberg.org/files/11/11-0.txt", "rating": "4.8"},
    {"title": "Moby Dick", "author": "Herman Melville", "category": "Adventure", "emoji": "🐋", "color": "#1a6b5a",
     "cover": "https://i.pinimg.com/1200x/87/ab/62/87ab629e6a39fe98972fd2dc2ea6e79a.jpg",
     "url": "https://www.gutenberg.org/files/2701/2701-0.txt", "rating": "4.6"},
    {"title": "Romeo and Juliet", "author": "William Shakespeare", "category": "Tragedy", "emoji": "🌹", "color": "#8b3a0f",
     "cover": "https://i.pinimg.com/736x/3f/b6/bc/3fb6bc577e4948ddd90ebe700ef3c802.jpg",
     "url": "https://www.gutenberg.org/files/1513/1513-0.txt", "rating": "4.9"},
    {"title": "Dracula", "author": "Bram Stoker", "category": "Horror", "emoji": "🧛", "color": "#6c0a0a",
     "cover": "https://i.pinimg.com/1200x/d3/ee/9d/d3ee9dbb2089d378d7f9335e0f14b9ca.jpg",
     "url": "https://www.gutenberg.org/files/345/345-0.txt", "rating": "4.7"},
    {"title": "The Odyssey", "author": "Homer", "category": "Epic", "emoji": "⚔️", "color": "#5a6e1f",
     "cover": "https://i.pinimg.com/736x/89/8b/26/898b26212aaa10ac1a6345d34bec4a70.jpg",
     "url": "https://www.gutenberg.org/files/1727/1727-0.txt", "rating": "4.8"},
    {"title": "Great Expectations", "author": "Charles Dickens", "category": "Classic", "emoji": "🎩", "color": "#1a5276",
     "cover": "https://i.pinimg.com/1200x/a6/5d/13/a65d131fc83f280550249fb0f5318b24.jpg",
     "url": "https://www.gutenberg.org/files/1400/1400-0.txt", "rating": "4.7"}
]

# ─── HELPER ─────────────────────────────────────────────
def get_community_novels():
    try:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("""
                SELECT c.*, u.name as uploader
                FROM community_novels c
                JOIN users u ON c.user_id = u.id
                ORDER BY c.created_at DESC LIMIT 10
            """)
            novels = cur.fetchall()
        db.close()
        return novels
    except:
        return []

# ─── NLP FUNCTIONS ──────────────────────────────────────
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
    text = re.sub(r'[*]{3}.*?[*]{3}', '', text, flags=re.DOTALL)
    text = re.sub(r'CHAPTER\s+[A-Z0-9]+.*?\n', '', text)
    text = re.sub(r'\s+', ' ', text)
    return text.strip()[:50000]

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

def emotional_arc(text, chunks=5):
    analyzer = SentimentIntensityAnalyzer()
    words = text.split()
    size = max(1, len(words) // chunks)
    return [round(analyzer.polarity_scores(' '.join(words[i*size:(i+1)*size]))['compound'], 3) for i in range(chunks)]

def generate_quiz(summary, characters=[]):
    import random
    quiz = []
    char_names = [c[0] for c in characters] if characters else []

    for s in summary[:8]:
        words = s.split()
        if len(words) < 8:
            continue

        # Find best target word — prefer character names first
        target_word = None
        target_idx = None

        # Try character names first
        for i, w in enumerate(words):
            clean = re.sub(r'[^a-zA-Z]', '', w)
            if clean in char_names and len(clean) > 3:
                target_word = clean
                target_idx = i
                break

        # Then try important content words
        if not target_word:
            for i in range(2, len(words) - 1):
                clean = re.sub(r'[^a-zA-Z]', '', words[i])
                if (len(clean) > 5 and
                    clean.lower() not in STOP_WORDS and
                    clean[0].isupper()):
                    target_word = clean
                    target_idx = i
                    break

        # Then any long word
        if not target_word:
            for i in range(2, len(words) - 1):
                clean = re.sub(r'[^a-zA-Z]', '', words[i])
                if len(clean) > 5 and clean.lower() not in STOP_WORDS:
                    target_word = clean
                    target_idx = i
                    break

        if not target_word or not target_idx:
            continue

        # Build question
        question_words = words.copy()
        question_words[target_idx] = '______'
        question = ' '.join(question_words)

        # Build WRONG options — must be meaningfully different from correct answer
        wrong_options = []

        # Use other character names as distractors
        other_chars = [c for c in char_names if c != target_word and len(c) > 3]
        random.shuffle(other_chars)
        wrong_options.extend(other_chars[:2])

        # Use other important words from summary as distractors
        if len(wrong_options) < 3:
            all_words = []
            for sent in summary:
                for w in sent.split():
                    clean = re.sub(r'[^a-zA-Z]', '', w)
                    if (len(clean) > 4 and
                        clean != target_word and
                        clean.lower() not in STOP_WORDS and
                        clean not in wrong_options):
                        all_words.append(clean)

            # Deduplicate
            all_words = list(dict.fromkeys(all_words))
            random.shuffle(all_words)
            for w in all_words:
                if w not in wrong_options and len(wrong_options) < 3:
                    wrong_options.append(w)

        if len(wrong_options) < 3:
            continue

        wrong_options = wrong_options[:3]

        # Build 4 options and shuffle
        options = [target_word] + wrong_options
        random.shuffle(options)
        correct_index = options.index(target_word)

        quiz.append({
            'question': question,
            'options': options,
            'correct': correct_index,
            'answer': s
        })

        if len(quiz) == 3:
            break

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
    quiz = generate_quiz(summary, characters)
    mood = 'Positive 😊' if sentiment['compound'] >= 0.05 else 'Negative 😞' if sentiment['compound'] <= -0.05 else 'Neutral 😐'
    return dict(summary=summary, characters=characters, sentiment=sentiment, mood=mood, arc=arc, quiz=quiz, persona=persona)

# ─── AUTH ROUTES ────────────────────────────────────────
@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        name = request.form['name']
        email = request.form['email']
        password = request.form['password']
        confirm = request.form.get('confirm_password', '')
        if password != confirm:
            flash('Passwords do not match!', 'error')
            return render_template('register.html')
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return render_template('register.html')
        try:
            hashed = bcrypt.generate_password_hash(password).decode('utf-8')
            db = get_db()
            with db.cursor() as cur:
                cur.execute("INSERT INTO users (name, email, password) VALUES (%s, %s, %s)", (name, email, hashed))
            db.commit()
            db.close()
            flash('Account created! Please login.', 'success')
            return redirect(url_for('login'))
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        email = request.form['email'].strip().lower()
        password = request.form['password']
        try:
            db = get_db()
            with db.cursor() as cur:
                cur.execute("SELECT * FROM users WHERE LOWER(email)=%s", (email,))
                user = cur.fetchone()
            db.close()
            if not user:
                flash('No account found with this email!', 'error')
                return render_template('login.html')
            if bcrypt.check_password_hash(user['password'], password):
                session['user_id'] = user['id']
                session['user_name'] = user['name']
                session['is_admin'] = user['is_admin']
                flash(f"Welcome back, {user['name']}!", 'success')
                if user['is_admin']:
                    return redirect(url_for('admin'))
                return redirect(url_for('index'))
            else:
                flash('Wrong password! Please try again.', 'error')
        except Exception as e:
            flash(f'Error: {str(e)}', 'error')
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('Logged out successfully!', 'success')
    return redirect(url_for('login'))

# ─── WELCOME ────────────────────────────────────────────
@app.route('/welcome')
def welcome():
    return render_template('welcome.html')

# ─── MAIN ROUTES ────────────────────────────────────────
@app.route('/', methods=['GET', 'POST'])
def index():
    if 'user_id' not in session:
        return redirect(url_for('welcome'))
    if request.method == 'POST':
        file = request.files.get('file')
        persona = request.form.get('persona', 'student')
        length = int(request.form.get('length', 2))
        title = request.form.get('title', 'Untitled Novel')
        author = request.form.get('author', 'Unknown')
        if not file or file.filename == '':
            return render_template('index.html', error='Please upload a file.',
                                   books=FEATURED_BOOKS, community=get_community_novels())
        raw = extract_text(file)
        results = analyze_text(raw, persona, length)
        results['novel_title'] = title
        results['novel_id'] = None
        try:
            db = get_db()
            with db.cursor() as cur:
                summary_text = ' '.join(results['summary'])
                cur.execute("INSERT INTO novels (user_id, title, summary, mood) VALUES (%s, %s, %s, %s)",
                    (session['user_id'], title, summary_text, results['mood']))
                results['novel_id'] = cur.lastrowid
                cur.execute("SELECT id FROM community_novels WHERE title=%s", (title,))
                existing = cur.fetchone()
                if not existing:
                    cur.execute("INSERT INTO community_novels (user_id, title, author, content) VALUES (%s, %s, %s, %s)",
                        (session['user_id'], title, author, raw[:500000]))
            db.commit()
            db.close()
        except Exception as e:
            print(f"DB Error: {e}")
        return render_template('results.html', **results)
    return render_template('index.html', books=FEATURED_BOOKS, community=get_community_novels())

@app.route('/featured/<int:book_id>')
def featured(book_id):
    if book_id >= len(FEATURED_BOOKS):
        return render_template('index.html', books=FEATURED_BOOKS, community=get_community_novels())
    book = FEATURED_BOOKS[book_id]
    try:
        raw = fetch_gutenberg(book['url'])
        results = analyze_text(raw)
        results['novel_title'] = book['title']
        results['novel_id'] = None
        if 'user_id' in session:
            try:
                db = get_db()
                with db.cursor() as cur:
                    summary_text = ' '.join(results['summary'])
                    cur.execute("INSERT INTO novels (user_id, title, summary, mood) VALUES (%s, %s, %s, %s)",
                        (session['user_id'], book['title'], summary_text, results['mood']))
                    results['novel_id'] = cur.lastrowid
                db.commit()
                db.close()
            except Exception as e:
                print(f"DB Error: {e}")
        return render_template('results.html', **results)
    except Exception as e:
        return render_template('index.html', books=FEATURED_BOOKS,
                               community=get_community_novels(), error=f'Could not load: {str(e)}')

# ─── READER ─────────────────────────────────────────────
@app.route('/read/featured/<int:book_id>')
def read_featured(book_id):
    if book_id >= len(FEATURED_BOOKS):
        return redirect(url_for('index'))
    book = FEATURED_BOOKS[book_id]
    try:
        raw = fetch_gutenberg(book['url'])
        # Remove Gutenberg header/footer
        start_markers = ['*** START OF THIS PROJECT', '*** START OF THE PROJECT', '*END*THE SMALL PRINT']
        end_markers = ['*** END OF THIS PROJECT', '*** END OF THE PROJECT', 'End of the Project']
        text = raw
        for marker in start_markers:
            idx = text.find(marker)
            if idx != -1:
                text = text[idx+len(marker):]
                # Skip to next newline
                nl = text.find('\n')
                if nl != -1:
                    text = text[nl+1:]
                break
        for marker in end_markers:
            idx = text.find(marker)
            if idx != -1:
                text = text[:idx]
                break
        text = text.strip()
        return render_template('reader.html',
            title=book['title'],
            author=book['author'],
            content=text,
            book_id=book_id)
    except Exception as e:
        flash(f'Could not load: {str(e)}', 'error')
        return redirect(url_for('index'))

@app.route('/read/community/<int:novel_id>')
def read_community(novel_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM community_novels WHERE id=%s", (novel_id,))
        novel = cur.fetchone()
    db.close()
    if not novel:
        flash('Novel not found!', 'error')
        return redirect(url_for('index'))
    return render_template('reader.html',
        title=novel['title'], author=novel['author'],
        content=novel['content'], book_id=None)

@app.route('/analyze/community/<int:novel_id>')
def analyze_community(novel_id):
    if 'user_id' not in session:
        flash('Please login first!', 'error')
        return redirect(url_for('login'))
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM community_novels WHERE id=%s", (novel_id,))
        novel = cur.fetchone()
    db.close()
    if not novel:
        flash('Novel not found!', 'error')
        return redirect(url_for('index'))
    results = analyze_text(novel['content'])
    results['novel_title'] = novel['title']
    results['novel_id'] = None
    try:
        db = get_db()
        with db.cursor() as cur:
            summary_text = ' '.join(results['summary'])
            cur.execute("INSERT INTO novels (user_id, title, summary, mood) VALUES (%s, %s, %s, %s)",
                (session['user_id'], novel['title'], summary_text, results['mood']))
            results['novel_id'] = cur.lastrowid
        db.commit()
        db.close()
    except Exception as e:
        print(f"DB Error: {e}")
    return render_template('results.html', **results)

# ─── DASHBOARD ──────────────────────────────────────────
@app.route('/dashboard')
@login_required
def dashboard():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT n.*,
            (SELECT COUNT(*) FROM likes WHERE novel_id=n.id) as like_count,
            (SELECT COUNT(*) FROM likes WHERE novel_id=n.id AND user_id=%s) as user_liked
            FROM novels n WHERE n.user_id=%s ORDER BY n.created_at DESC
        """, (session['user_id'], session['user_id']))
        novels = cur.fetchall()
        cur.execute("""
            SELECT title, COUNT(*) as analyze_count
            FROM novels GROUP BY title
            ORDER BY analyze_count DESC LIMIT 5
        """)
        trending = cur.fetchall()
    db.close()
    return render_template('dashboard.html', novels=novels, trending=trending)

# ─── LIKE ───────────────────────────────────────────────
@app.route('/like/<int:novel_id>', methods=['POST'])
@login_required
def like(novel_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM likes WHERE user_id=%s AND novel_id=%s", (session['user_id'], novel_id))
        existing = cur.fetchone()
        if existing:
            cur.execute("DELETE FROM likes WHERE user_id=%s AND novel_id=%s", (session['user_id'], novel_id))
            action = 'unliked'
        else:
            cur.execute("INSERT INTO likes (user_id, novel_id) VALUES (%s, %s)", (session['user_id'], novel_id))
            action = 'liked'
    db.commit()
    db.close()
    return {'action': action}

# ─── SEARCH ─────────────────────────────────────────────
@app.route('/search_novel')
def search_novel():
    query = request.args.get('q', '').strip()
    if not query:
        return {'results': []}
    search_url = f"https://gutendex.com/books/?search={urllib.parse.quote(query)}&languages=en"
    try:
        req = urllib.request.Request(search_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req, timeout=10) as r:
            data = json.loads(r.read().decode('utf-8'))
        results = []
        for book in data.get('results', [])[:5]:
            authors = ', '.join(a['name'] for a in book.get('authors', []))
            formats = book.get('formats', {})
            txt_url = (formats.get('text/plain; charset=utf-8') or
                       formats.get('text/plain; charset=us-ascii') or
                       formats.get('text/plain') or
                       next((v for k, v in formats.items() if 'text/plain' in k), None))
            if txt_url:
                results.append({'id': book['id'], 'title': book['title'], 'author': authors, 'url': txt_url})
        return {'results': results}
    except Exception as e:
        return {'results': [], 'error': str(e)}

@app.route('/analyze_search', methods=['POST'])
def analyze_search():
    if 'user_id' not in session:
        flash('Please login to analyze novels!', 'error')
        return redirect(url_for('login'))
    url = request.form.get('url')
    title = request.form.get('title')
    author = request.form.get('author')
    try:
        raw = fetch_gutenberg(url)
        results = analyze_text(raw)
        results['novel_title'] = f"{title} by {author}"
        results['novel_id'] = None
        try:
            db = get_db()
            with db.cursor() as cur:
                summary_text = ' '.join(results['summary'])
                cur.execute("INSERT INTO novels (user_id, title, summary, mood) VALUES (%s, %s, %s, %s)",
                    (session['user_id'], title, summary_text, results['mood']))
                results['novel_id'] = cur.lastrowid
            db.commit()
            db.close()
        except Exception as e:
            print(f"DB Error: {e}")
        return render_template('results.html', **results)
    except Exception as e:
        flash(f'Could not load novel: {str(e)}', 'error')
        return redirect(url_for('index'))

# ─── REVIEWS ────────────────────────────────────────────
@app.route('/review/<path:novel_title>', methods=['POST'])
def review(novel_title):
    if 'user_id' not in session:
        flash('Please login to write a review!', 'error')
        return redirect(url_for('login'))
    rating = int(request.form.get('rating', 5))
    review_text = request.form.get('review_text', '').strip()
    if review_text:
        db = get_db()
        with db.cursor() as cur:
            cur.execute("INSERT INTO reviews (user_id, novel_title, rating, review_text) VALUES (%s, %s, %s, %s)",
                (session['user_id'], novel_title, rating, review_text))
        db.commit()
        db.close()
        flash('Review posted!', 'success')
    return redirect(request.referrer or url_for('index'))

@app.route('/get_reviews/<path:novel_title>')
def get_reviews(novel_title):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("""
            SELECT r.rating, r.review_text, r.created_at, u.name as user_name
            FROM reviews r JOIN users u ON r.user_id = u.id
            WHERE r.novel_title = %s ORDER BY r.created_at DESC
        """, (novel_title,))
        reviews = cur.fetchall()
    db.close()
    result = [{'user_name': r['user_name'], 'rating': r['rating'],
               'review_text': r['review_text'], 'created_at': str(r['created_at'])} for r in reviews]
    return jsonify({'reviews': result})

# ─── ADMIN ──────────────────────────────────────────────
@app.route('/admin')
@admin_required
def admin():
    db = get_db()
    with db.cursor() as cur:
        cur.execute("SELECT * FROM users ORDER BY created_at DESC")
        users = cur.fetchall()
        cur.execute("""
            SELECT n.*, u.name as user_name,
            (SELECT COUNT(*) FROM likes WHERE novel_id=n.id) as like_count
            FROM novels n JOIN users u ON n.user_id=u.id
            ORDER BY n.created_at DESC
        """)
        novels = cur.fetchall()
    db.close()
    return render_template('admin.html', users=users, novels=novels)

@app.route('/admin/delete_novel/<int:novel_id>', methods=['POST'])
@admin_required
def delete_novel(novel_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM likes WHERE novel_id=%s", (novel_id,))
        cur.execute("DELETE FROM novels WHERE id=%s", (novel_id,))
    db.commit()
    db.close()
    flash('Novel deleted!', 'success')
    return redirect(url_for('admin'))

@app.route('/admin/delete_user/<int:user_id>', methods=['POST'])
@admin_required
def delete_user(user_id):
    db = get_db()
    with db.cursor() as cur:
        cur.execute("DELETE FROM likes WHERE user_id=%s", (user_id,))
        cur.execute("DELETE FROM novels WHERE user_id=%s", (user_id,))
        cur.execute("DELETE FROM users WHERE id=%s", (user_id,))
    db.commit()
    db.close()
    flash('User deleted!', 'success')
    return redirect(url_for('admin'))
@app.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM users WHERE LOWER(email)=%s", (email,))
            user = cur.fetchone()
        if not user:
            flash('No account found with this email!', 'error')
            return render_template('forgot_password.html')
        # Generate 6 digit OTP
        otp = ''.join(random.choices(string.digits, k=6))
        expires_at = datetime.now() + timedelta(minutes=10)
        with db.cursor() as cur:
            cur.execute("DELETE FROM password_resets WHERE email=%s", (email,))
            cur.execute("INSERT INTO password_resets (email, otp, expires_at) VALUES (%s, %s, %s)",
                (email, otp, expires_at))
        db.commit()
        db.close()
        # Send OTP email
        try:
            msg = Message(
                subject='BookEase — Password Reset OTP',
                recipients=[email],
                body=f"""
Hello {user['name']},

Your BookEase password reset OTP is:

    {otp}

This OTP is valid for 10 minutes.
If you did not request this, please ignore this email.

— BookEase Team
                """
            )
            mail.send(msg)
            flash('OTP sent to your email!', 'success')
            return redirect(url_for('verify_otp', email=email))
        except Exception as e:
            flash(f'Failed to send email: {str(e)}', 'error')
    return render_template('forgot_password.html')


@app.route('/verify_otp/<email>', methods=['GET', 'POST'])
def verify_otp(email):
    if request.method == 'POST':
        otp_input = request.form.get('otp', '').strip()
        db = get_db()
        with db.cursor() as cur:
            cur.execute("SELECT * FROM password_resets WHERE email=%s ORDER BY created_at DESC LIMIT 1", (email,))
            record = cur.fetchone()
        db.close()
        if not record:
            flash('OTP not found. Please try again.', 'error')
            return redirect(url_for('forgot_password'))
        if datetime.now() > record['expires_at']:
            flash('OTP expired. Please request a new one.', 'error')
            return redirect(url_for('forgot_password'))
        if otp_input != record['otp']:
            flash('Incorrect OTP. Please try again.', 'error')
            return render_template('verify_otp.html', email=email)
        flash('OTP verified! Set your new password.', 'success')
        return redirect(url_for('reset_password', email=email))
    return render_template('verify_otp.html', email=email)


@app.route('/reset_password/<email>', methods=['GET', 'POST'])
def reset_password(email):
    if request.method == 'POST':
        password = request.form.get('password', '')
        confirm = request.form.get('confirm_password', '')
        if password != confirm:
            flash('Passwords do not match!', 'error')
            return render_template('reset_password.html', email=email)
        if len(password) < 6:
            flash('Password must be at least 6 characters!', 'error')
            return render_template('reset_password.html', email=email)
        hashed = bcrypt.generate_password_hash(password).decode('utf-8')
        db = get_db()
        with db.cursor() as cur:
            cur.execute("UPDATE users SET password=%s WHERE LOWER(email)=%s", (hashed, email.lower()))
            cur.execute("DELETE FROM password_resets WHERE email=%s", (email,))
        db.commit()
        db.close()
        flash('Password reset successfully! Please login.', 'success')
        return redirect(url_for('login'))
    return render_template('reset_password.html', email=email)

if __name__ == '__main__':
    app.run(debug=True)