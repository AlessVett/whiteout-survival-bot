import torch
from PIL import Image
from torchvision import transforms
import string
from model import CaptchaCNN

class CaptchaSolver:
    def __init__(self, model_path='best_captcha_model.pth'):
        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
        
        self.chars = string.ascii_lowercase + string.digits
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        
        self.model = CaptchaCNN(num_chars=36, max_length=5).to(self.device)
        self.model.load_state_dict(torch.load(model_path, map_location=self.device))
        self.model.eval()
        
        self.transform = transforms.Compose([
            transforms.Resize((64, 160)),
            transforms.ToTensor(),
            transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
        ])
    
    def solve(self, image_path, expected_length=None):
        image = Image.open(image_path).convert('RGB')
        image = self.transform(image).unsqueeze(0).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(image)
            
        prediction = []
        confidences = []
        
        max_len = expected_length if expected_length else 5
        
        for i in range(max_len):
            probs = torch.softmax(outputs[0, i], dim=0)
            char_idx = torch.argmax(probs).item()
            confidence = probs[char_idx].item()
            
            prediction.append(self.idx_to_char[char_idx])
            confidences.append(confidence)
        
        if not expected_length:
            avg_confidence = sum(confidences) / len(confidences)
            if len(confidences) > 4 and confidences[4] < avg_confidence * 0.7:
                prediction = prediction[:4]
                confidences = confidences[:4]
        
        return ''.join(prediction), confidences
    
    def solve_batch(self, image_paths):
        results = []
        for path in image_paths:
            try:
                result, confidence = self.solve(path)
                results.append({'path': path, 'prediction': result, 'confidence': confidence})
            except Exception as e:
                results.append({'path': path, 'error': str(e)})
        return results

def test_solver():
    solver = CaptchaSolver()
    
    test_images = [
        'letters/226md.png',
        'letters/22d5n.png', 
        'letters/2356g.png'
    ]
    
    for img_path in test_images:
        try:
            prediction, confidence = solver.solve(img_path)
            actual = img_path.split('/')[-1].split('.')[0]
            print(f"Image: {img_path}")
            print(f"Actual: {actual}")
            print(f"Predicted: {prediction}")
            print(f"Confidence: {[f'{c:.3f}' for c in confidence]}")
            print(f"Correct: {prediction.lower() == actual.lower()}")
            print("-" * 50)
        except Exception as e:
            print(f"Error processing {img_path}: {e}")

if __name__ == "__main__":
    test_solver()