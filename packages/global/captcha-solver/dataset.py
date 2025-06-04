import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
import string
from torchvision import transforms

class CaptchaDataset(Dataset):
    def __init__(self, data_dir, transform=None, max_length=5):
        self.data_dir = data_dir
        self.transform = transform
        self.max_length = max_length
        
        self.chars = string.ascii_lowercase + string.digits
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        
        self.image_files = [f for f in os.listdir(data_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
    def __len__(self):
        return len(self.image_files)
    
    def __getitem__(self, idx):
        img_name = self.image_files[idx]
        img_path = os.path.join(self.data_dir, img_name)
        
        image = Image.open(img_path).convert('RGB')
        
        if self.transform:
            image = self.transform(image)
        
        label = os.path.splitext(img_name)[0].lower()
        
        encoded_label = torch.zeros(self.max_length, len(self.chars))
        for i, char in enumerate(label):
            if i < self.max_length and char in self.char_to_idx:
                encoded_label[i, self.char_to_idx[char]] = 1
        
        return image, encoded_label, len(label)
    
    def decode_prediction(self, prediction, length):
        pred_chars = []
        for i in range(length):
            char_idx = torch.argmax(prediction[i]).item()
            pred_chars.append(self.idx_to_char[char_idx])
        return ''.join(pred_chars)

def get_dataloader(data_dir, batch_size=32, shuffle=True):
    transform = transforms.Compose([
        transforms.Resize((64, 160)),
        transforms.ToTensor(),
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    dataset = CaptchaDataset(data_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
    
    return dataloader, dataset