# 🫁 PneumoScan AI — Chest X-Ray Pneumonia Detection System

![Python](https://img.shields.io/badge/Python-3.13-blue?style=flat-square&logo=python)
![Flask](https://img.shields.io/badge/Flask-2.3-black?style=flat-square&logo=flask)
![FastAI](https://img.shields.io/badge/FastAI-v2-orange?style=flat-square)
![ResNet-50](https://img.shields.io/badge/Model-ResNet--50-red?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

A full-stack AI-powered medical diagnostic web application that classifies chest X-ray images into **Normal**, **Bacterial Pneumonia**, and **Viral Pneumonia** using a fine-tuned ResNet-50 deep learning model with Grad-CAM visual explainability.

---

## 📸 Demo

| Upload X-Ray | Get Diagnosis |
|---|---|
| Drag & drop chest X-ray | Real-time 3-class prediction |
| Grad-CAM heatmap overlay | Highlights affected lung regions |
| Confidence score | ICD-10 code + clinical recommendation |

---

## 🧠 How It Works

```
Chest X-Ray Image
      ↓
HIPAA Compliance Check
      ↓
Preprocess (Resize 224×224, Normalize)
      ↓
ResNet-50 Inference (FastAI)
      ↓
3-Class Classification
  ├── Normal
  ├── Bacterial Pneumonia
  └── Viral Pneumonia
      ↓
Grad-CAM Heatmap Generation
      ↓
Clinical Report Output
```

---

## 🗂️ Project Structure

```
pneumonia_app/
├── app.py                  ← Flask backend (REST API)
├── train.py                ← Model training script
├── pneumonia_model.pkl     ← Trained ResNet-50 model (generated after training)
├── requirements.txt        ← Python dependencies
├── README.md
├── templates/
│   └── index.html          ← Frontend UI (HTML/CSS/JS)
└── static/
    └── uploads/            ← Uploaded X-ray images
```

---

## ⚙️ Tech Stack

| Layer | Technology |
|---|---|
| Frontend | HTML5, CSS3, Vanilla JavaScript |
| Backend | Python, Flask |
| AI Model | FastAI v2, PyTorch |
| Base Model | ResNet-50 (ImageNet pretrained) |
| Explainability | Grad-CAM heatmap |
| Dataset | Kaggle Chest X-Ray Images (Pneumonia) |

---

## 📦 Dataset

**Kaggle — Chest X-Ray Images (Pneumonia)**
- Link: https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia
- 5,856 chest X-ray images
- 3 classes: Normal, Bacterial Pneumonia, Viral Pneumonia
- Split: train / val / test

Download and extract to:
```
~/Downloads/chest_xray/
    ├── train/
    │   ├── NORMAL/
    │   └── PNEUMONIA/
    ├── val/
    │   ├── NORMAL/
    │   └── PNEUMONIA/
    └── test/
        ├── NORMAL/
        └── PNEUMONIA/
```

---

## 🚀 Setup & Installation

### 1. Clone the repository
```bash
git clone https://github.com/your-username/pneumoscan-ai.git
cd pneumoscan-ai
```

### 2. Create virtual environment
```bash
python3 -m venv venv
source venv/bin/activate        # Mac/Linux
# venv\Scripts\activate         # Windows
```

### 3. Install dependencies
```bash
pip install flask werkzeug ipython fastai scikit-learn
```

---

## 🏋️ Train the Model

> Skip this step if you already have `pneumonia_model.pkl`

Make sure dataset is downloaded and extracted to `~/Downloads/chest_xray/`

```bash
python3 train.py
```

Training runs in 2 phases:
- **Phase 1** — Frozen ResNet-50 body, trains classifier head only (~40 min on Mac CPU)
- **Phase 2** — Full network fine-tuning with discriminative learning rates (~70 min on Mac CPU)

After training completes, export the model:
```bash
python3 -c "
from fastai.vision.all import *

DATASET_PATH = Path.home() / 'Downloads' / 'chest_xray'

def label_func(path):
    parent = path.parent.name.upper()
    if parent == 'NORMAL':
        return 'Normal'
    name = path.name.lower()
    if 'bacteria' in name:
        return 'Bacterial Pneumonia'
    if 'virus' in name:
        return 'Viral Pneumonia'
    return 'Bacterial Pneumonia'

dls = DataBlock(
    blocks    = (ImageBlock, CategoryBlock),
    get_items = get_image_files,
    get_y     = label_func,
    splitter  = GrandparentSplitter(train_name='train', valid_name='val'),
    item_tfms = Resize(224),
).dataloaders(DATASET_PATH, bs=16)

learn = vision_learner(dls, resnet50, metrics=[accuracy, error_rate])
learn.load('best_model')
learn.export('pneumonia_model.pkl')
print('Model exported! Size:', Path('pneumonia_model.pkl').stat().st_size / 1e6, 'MB')
"
```

---

## ▶️ Run the App

### Step 1 — Enable real model in app.py
Open `app.py` and set:
```python
USE_REAL_MODEL = True   # line 33
```

### Step 2 — Start the server
```bash
cd pneumonia_app
source venv/bin/activate
python3 app.py
```

### Step 3 — Open in browser
```
http://localhost:5001
```

---

## 🔌 API Endpoints

| Method | Endpoint | Description |
|---|---|---|
| GET | `/` | Main frontend UI |
| POST | `/predict` | Upload X-ray → get diagnosis |
| GET | `/health` | Server + model status |
| GET | `/classes` | All class labels + ICD-10 codes |

### POST `/predict` — Example

**Request (form-data):**
```
file       → chest X-ray image (PNG/JPG)
patient_id → PT-20260430-001
```

**Response (JSON):**
```json
{
  "prediction": "Bacterial Pneumonia",
  "confidence": 0.921,
  "confidence_pct": "92.1%",
  "probabilities": {
    "Normal": 0.045,
    "Bacterial Pneumonia": 0.921,
    "Viral Pneumonia": 0.034
  },
  "icd_code": "J15.9 — Unspecified bacterial pneumonia",
  "recommendation": "Antibiotic therapy recommended. Consult pulmonologist within 24 hours.",
  "severity": "high",
  "needs_review": false,
  "patient_id": "PT-20260430-001",
  "timestamp": "2026-04-30 14:30:00",
  "processing_time": "1.82s"
}
```

---

## ✨ Features

- **3-class diagnosis** — Normal / Bacterial Pneumonia / Viral Pneumonia
- **Grad-CAM heatmap** — Visual explanation of AI decision on lung regions
- **Confidence score** — Animated ring chart with percentage
- **ICD-10 code mapping** — Automatic clinical code assignment
- **Clinical recommendation** — Next steps based on diagnosis
- **Human handoff flag** — Cases below 85% confidence flagged for radiologist review
- **HIPAA-aware pipeline** — Patient data handling with compliance checks
- **Analysis history** — Last 6 scans shown in session
- **Clinical report download** — .txt report with full diagnosis details
- **Patient ID tracking** — Per-analysis patient record
- **Responsive dark UI** — Professional clinical interface

---

## 🧪 Model Architecture

```
Input Image (224 × 224 × 3)
        ↓
ResNet-50 Backbone (ImageNet pretrained)
  └── 48 Residual blocks
  └── 150+ layers total
        ↓
Custom Classifier Head (FastAI)
  └── AdaptiveAvgPool
  └── Flatten
  └── BatchNorm → Linear → ReLU → Dropout
  └── Linear → Softmax (3 classes)
        ↓
Output: [Normal, Bacterial Pneumonia, Viral Pneumonia]
```

**Training strategy:**
- Phase 1: Transfer learning — frozen backbone, train head only
- Phase 2: Fine-tuning — unfreeze all layers, discriminative learning rates
- Augmentation: Random flip, zoom, brightness, perspective warp
- Early stopping + best model checkpoint saving

---

## 📊 Results

| Metric | Value |
|---|---|
| Dataset | 5,856 chest X-ray images |
| Model | ResNet-50 (fine-tuned) |
| Classes | 3 (Normal / Bacterial / Viral) |
| Input size | 224 × 224 px |
| Model size | ~98 MB |
| Inference time | ~1.5–3s (CPU) |

---

## ⚠️ Disclaimer

This application is built for **academic and research purposes only**.
It is **not a substitute for professional medical advice**.
Always consult a qualified radiologist or physician for clinical decisions.

---

## 👩‍💻 Author

**Vyshnavi**
Bhoj Reddy Engineering College for Women
B.Tech — Computer Science Engineering

---

## 📄 License

This project is licensed under the MIT License.
```
MIT License — free to use, modify, and distribute with attribution.
```

---

## 🙏 Acknowledgements

- [Kaggle — Chest X-Ray Images Dataset](https://www.kaggle.com/datasets/paultimothymooney/chest-xray-pneumonia) by Paul Mooney
- [FastAI](https://www.fast.ai/) — Jeremy Howard & Rachel Thomas
- [PyTorch](https://pytorch.org/)
- [ResNet paper](https://arxiv.org/abs/1512.03385) — He et al., 2015
