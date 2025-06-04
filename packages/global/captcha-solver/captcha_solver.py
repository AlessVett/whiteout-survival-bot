"""
CAPTCHA Solver Module for Inference

This module provides the main interface for solving CAPTCHAs using
the trained CNN model. It handles image preprocessing, prediction,
and confidence scoring.
"""

import torch
from PIL import Image
from torchvision import transforms
import string
from model import CaptchaCNN
import os


class CaptchaSolver:
    """
    Main class for solving CAPTCHA images using a trained model.
    
    This class loads a pre-trained model and provides methods for
    solving single images or batches of images.
    
    Attributes:
        model: Trained CaptchaCNN model
        device: CPU or CUDA device for inference
        transform: Image preprocessing pipeline
    """
    
    def __init__(self, model_path='best_captcha_model.pth'):
        """
        Initialize the CAPTCHA solver with a trained model.
        
        Args:
            model_path (str): Path to the saved model weights
        """
        # Set device for inference (GPU if available)
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        # Define character set and mappings
        self.chars = string.ascii_lowercase + string.digits  # a-z + 0-9
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        
        # Load model architecture and weights
        self.model = CaptchaCNN(num_chars=36, max_length=5).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()  # Set to evaluation mode
        
        # Define image preprocessing (same as training)
        self.transform = transforms.Compose([
            transforms.Resize((64, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def solve(self, image_path, expected_length=None):
        """
        Solve a single CAPTCHA image.
        
        Args:
            image_path (str): Path to the CAPTCHA image
            expected_length (int, optional): Expected length of CAPTCHA text.
                                           If None, length is determined automatically.
        
        Returns:
            tuple: (predicted_text, confidence_scores)
                - predicted_text (str): Predicted CAPTCHA text
                - confidence_scores (list): Confidence score for each character
        """
        # Load and preprocess image
        image = Image.open(image_path).convert('RGB')
        image = self.transform(image).unsqueeze(0).to(self.device)
        
        # Run inference
        with torch.no_grad():
            outputs = self.model(image)  # Shape: (1, max_length, num_chars)
            
        prediction = []
        confidences = []
        
        # Process predictions for each position
        max_len = expected_length if expected_length else 5
        
        for i in range(max_len):
            # Apply softmax to get probabilities
            probs = torch.softmax(outputs[0, i], dim=0)
            # Get most likely character
            char_idx = torch.argmax(probs).item()
            confidence = probs[char_idx].item()
            
            prediction.append(self.idx_to_char[char_idx])
            confidences.append(confidence)
        
        # Dynamic length detection based on confidence
        if not expected_length:
            avg_confidence = sum(confidences) / len(confidences)
            # If 5th character has significantly lower confidence, assume 4-char CAPTCHA
            if len(confidences) > 4 and confidences[4] < avg_confidence * 0.7:
                prediction = prediction[:4]
                confidences = confidences[:4]
        
        return ''.join(prediction), confidences
    
    def solve_dict(self, image_path, expected_length=None):
        """
        Solve a CAPTCHA and return results as a dictionary.
        
        This is a convenience method that wraps solve() and returns
        a dictionary format as shown in the README examples.
        
        Args:
            image_path (str): Path to the CAPTCHA image
            expected_length (int, optional): Expected length of CAPTCHA text
            
        Returns:
            dict: {'text': str, 'confidence': list}
        """
        text, confidence = self.solve(image_path, expected_length)
        return {'text': text, 'confidence': confidence}
    
    def solve_batch(self, image_paths):
        """
        Solve multiple CAPTCHA images in batch.
        
        Args:
            image_paths (list): List of paths to CAPTCHA images
            
        Returns:
            list: List of dictionaries containing results for each image
                  Format: {'path': str, 'prediction': str, 'confidence': list}
                  or {'path': str, 'error': str} if processing fails
        """
        results = []
        for path in image_paths:
            try:
                result, confidence = self.solve(path)
                results.append({
                    'path': path,
                    'prediction': result,
                    'confidence': confidence
                })
            except Exception as e:
                results.append({
                    'path': path,
                    'error': str(e)
                })
        return results

def test_solver():
    """
    Test the CAPTCHA solver on all images in the letters directory.
    
    This function loads all images from the letters directory,
    runs predictions, and compares them with the ground truth
    (extracted from filenames).
    """
    # Initialize solver with best model
    solver = CaptchaSolver()

    letters_dir = 'letters'
    
    # Get all test images
    test_images = [
        f'{letters_dir}/{f}' for f in os.listdir(letters_dir)
        if f.endswith('.png') or f.endswith('.jpg')
    ]

    counter = 0  # Track correct predictions

    # Process each test image
    for img_path in test_images:
        try:
            # Get prediction
            prediction, confidence = solver.solve(img_path)
            # Extract ground truth from filename
            actual = img_path.split('/')[-1].split('.')[0]

            # Trim prediction to match actual length
            if len(prediction) > len(actual):
                prediction = prediction[:len(actual)]

            # Display results
            print(f"Image: {img_path}")
            print(f"Actual: {actual}")
            print(f"Predicted: {prediction}")
            print(f"Confidence: {[f'{c:.3f}' for c in confidence]}")
            print(f"Correct: {prediction.lower() == actual.lower()}")
            print("-" * 50)

            # Count correct predictions
            if prediction.lower() == actual.lower():
                counter += 1
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

    # Print summary
    print(f"Total correct predictions: {counter}/{len(test_images)}")
    print(f"Accuracy: {counter/len(test_images)*100:.2f}%")

if __name__ == "__main__":
    # Run test on all images when executed directly
    test_solver()