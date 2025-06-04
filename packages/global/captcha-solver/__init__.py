"""
CAPTCHA Solver Package for Whiteout Survival Gift Code System

This package provides a deep learning-based solution for solving CAPTCHAs
from the Whiteout Survival game's gift code redemption system.

Main components:
- CaptchaSolver: Main class for inference
- CaptchaDataset: PyTorch dataset for training
- CaptchaCNN: Neural network architecture
- train_model: Training function

Example usage:
    from captcha_solver import CaptchaSolver
    
    solver = CaptchaSolver('best_captcha_model.pth')
    text, confidence = solver.solve('captcha.png')
    print(f"Predicted: {text}")
"""

# Version info
__version__ = "1.0.0"
__author__ = "Whiteout Survival Bot Team"

# Package-level imports for convenience
from .captcha_solver import CaptchaSolver
from .dataset import CaptchaDataset, get_dataloader
from .model import CaptchaCNN
from .train import train_model

__all__ = ['CaptchaSolver', 'CaptchaDataset', 'CaptchaCNN', 'train_model', 'get_dataloader']