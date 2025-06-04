# CAPTCHA Solver for Whiteout Survival Gift Code System

A deep learning-based CAPTCHA solver specifically designed for the Whiteout Survival game's gift code redemption system (https://wos-giftcode.centurygame.com/).

## Overview

This project implements a Convolutional Neural Network (CNN) to automatically solve CAPTCHA challenges. The model achieves near-perfect accuracy on the target CAPTCHA system, making it suitable for automated gift code redemption workflows.

## Features

- **High Accuracy**: Achieves ~100% confidence on most test cases after 4000 epochs of training
- **Variable Length Support**: Automatically detects CAPTCHA length (up to 5 characters)
- **Batch Processing**: Supports both single image and batch inference
- **Character Set**: Recognizes lowercase letters (a-z) and digits (0-9)
- **Pre-trained Models**: Includes checkpoints at 2000 and 4000 epochs

## Architecture

The system consists of four main components:

1. **Data Pipeline** (`dataset.py`): Handles image loading, preprocessing, and label encoding
2. **Neural Network** (`model.py`): CNN architecture with 4 convolutional layers
3. **Training** (`train.py`): Training loop with validation and model checkpointing
4. **Inference** (`captcha_solver.py`): Production-ready solver for CAPTCHA images

### Model Architecture

- 4 Convolutional layers (32 → 64 → 128 → 256 channels)
- MaxPooling after each convolution
- 2 Fully connected layers (1024 → 512 units)
- Separate output heads for each character position
- Dropout (0.3) for regularization

## Installation

1. Clone the repository:
```bash
git clone https://github.com/AlessVett/whiteout-survival-bot.git
cd packages/global/captcha-solver
```

2. Install dependencies:
```bash
pip install torch torchvision pillow numpy tqdm
```

Note: The current requirements.txt file is corrupted. The essential dependencies are:
- PyTorch >= 2.0.0
- torchvision >= 0.15.0
- Pillow >= 9.0.0
- numpy >= 1.20.0
- tqdm >= 4.60.0

## Usage

### Using the Pre-trained Model

```python
from captcha_solver import CaptchaSolver

# Initialize solver with pre-trained model
solver = CaptchaSolver('best_captcha_model.pth')

# Solve a single CAPTCHA (returns tuple)
text, confidence = solver.solve('path/to/captcha.png')
print(f"Predicted text: {text}")
print(f"Confidence: {confidence}")

# Or use the dict format
result = solver.solve_dict('path/to/captcha.png')
print(f"Predicted text: {result['text']}")
print(f"Confidence: {result['confidence']}")

# Solve multiple CAPTCHAs
results = solver.solve_batch(['captcha1.png', 'captcha2.png'])
for result in results:
    print(f"File: {result['file']}, Text: {result['text']}")
```

### Training a New Model

```python
from train import train_model

# Train model with custom parameters
train_model(
    data_dir='letters/',
    epochs=100,
    batch_size=32,
    learning_rate=0.001,
    checkpoint_dir='checkpoints/'
)
```

### Testing the Model

```python
from captcha_solver import CaptchaSolver

# Test on all images in the letters directory
solver = CaptchaSolver('best_captcha_model.pth')
solver.test_solver()
```

## Dataset Format

Training images should be placed in the `letters/` directory with filenames corresponding to their labels:
- `226md.png` - CAPTCHA containing "226md"
- `22d5n.png` - CAPTCHA containing "22d5n"
- etc.

Supported image formats: PNG, JPG, JPEG

## Model Performance

### 4000 Epochs Model
- **Training Accuracy**: ~99.9%
- **Validation Accuracy**: ~99.8%
- **Test Set Performance**: Near 100% confidence on most samples
- **Training Time**: ~1-2 hours on GPU

### Character-wise Accuracy
The model tracks accuracy for each character position:
- Position 1-5: >99% accuracy across all positions

## Project Structure

```
captcha-solver/
├── __init__.py              # Package initializer
├── captcha_solver.py        # Inference module
├── dataset.py               # Data loading and preprocessing
├── model.py                 # CNN architecture
├── train.py                 # Training script
├── requirements.txt         # Dependencies (needs fixing)
├── letters/                 # Training data directory
│   ├── *.png               # CAPTCHA images
│   └── *.jpg               # CAPTCHA images
├── models/                  # Pre-trained model checkpoints
│   ├── best_captcha_model_2000_epochs.pth
│   └── best_captcha_model_4000_epochs.pth
└── results/                 # Training results and metrics
    ├── 1000-epochs.md
    ├── 2000-epochs.md
    ├── 2000-epochs-metrics.md
    ├── 4000-epochs.md
    └── 4000-epochs-metrics.md
```

## Technical Details

### Image Preprocessing
- Resize to 64x160 pixels
- Convert to RGB (if needed)
- Normalize using ImageNet statistics
- ToTensor transformation

### Label Encoding
- One-hot encoding for each character position
- Padding for variable-length CAPTCHAs
- Character mapping: lowercase letters + digits (36 classes)

### Confidence Threshold
- Dynamic length detection based on confidence scores
- Threshold: 0.5 for determining valid characters
- Returns only high-confidence predictions

## Limitations

- Maximum CAPTCHA length: 5 characters
- Character set: lowercase letters and digits only
- Requires clear, well-formed CAPTCHA images
- No support for special characters or uppercase letters

## Future Improvements

- [ ] Add support for longer CAPTCHAs
- [ ] Implement data augmentation for better generalization
- [ ] Add REST API for web service deployment
- [ ] Support for more character types
- [ ] Implement ensemble models for higher accuracy
- [ ] Add proper logging instead of print statements
- [ ] Create unit tests

## License

This project is part of the Whiteout Survival Bot suite. Please refer to the main repository for licensing information.

## Disclaimer

This tool is for educational purposes only. Users are responsible for complying with the terms of service of any systems they interact with.