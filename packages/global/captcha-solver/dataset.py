"""
Dataset Module for CAPTCHA Image Loading and Preprocessing

This module handles loading CAPTCHA images from disk, encoding labels,
and preparing data for training the neural network.
"""

import torch
from torch.utils.data import Dataset, DataLoader
from PIL import Image
import os
import string
from torchvision import transforms


class CaptchaDataset(Dataset):
    """
    PyTorch Dataset for loading and preprocessing CAPTCHA images.
    
    This dataset expects images to be named with their labels (e.g., '2a3bc.png')
    and converts them to one-hot encoded tensors for training.
    
    Args:
        data_dir (str): Directory containing CAPTCHA images
        transform (torchvision.transforms): Image transformations to apply
        max_length (int): Maximum length of CAPTCHA text (default: 5)
    """
    
    def __init__(self, data_dir, transform=None, max_length=5):
        self.data_dir = data_dir
        self.transform = transform
        self.max_length = max_length
        
        # Define character set: lowercase letters (a-z) + digits (0-9)
        self.chars = string.ascii_lowercase + string.digits  # Total: 36 characters
        
        # Create bidirectional mappings between characters and indices
        self.char_to_idx = {char: idx for idx, char in enumerate(self.chars)}
        self.idx_to_char = {idx: char for idx, char in enumerate(self.chars)}
        
        # Get all image files from the data directory
        self.image_files = [f for f in os.listdir(data_dir) if f.endswith(('.png', '.jpg', '.jpeg'))]
        
    def __len__(self):
        """Return the total number of images in the dataset."""
        return len(self.image_files)
    
    def __getitem__(self, idx):
        """
        Load and return a single image with its encoded label.
        
        Args:
            idx (int): Index of the image to load
            
        Returns:
            tuple: (image_tensor, encoded_label, actual_length)
                - image_tensor: Preprocessed image as tensor
                - encoded_label: One-hot encoded label tensor of shape (max_length, num_chars)
                - actual_length: Actual length of the CAPTCHA text
        """
        img_name = self.image_files[idx]
        img_path = os.path.join(self.data_dir, img_name)
        
        # Load image and ensure it's in RGB format
        image = Image.open(img_path).convert('RGB')
        
        # Apply transformations if provided
        if self.transform:
            image = self.transform(image)
        
        # Extract label from filename (e.g., '2a3bc.png' -> '2a3bc')
        label = os.path.splitext(img_name)[0].lower()
        
        # Create one-hot encoded label tensor
        # Shape: (max_length, num_chars) where each position has one hot value
        encoded_label = torch.zeros(self.max_length, len(self.chars))
        for i, char in enumerate(label):
            if i < self.max_length and char in self.char_to_idx:
                encoded_label[i, self.char_to_idx[char]] = 1
        
        return image, encoded_label, len(label)
    
    def decode_prediction(self, prediction, length):
        """
        Convert model prediction back to readable text.
        
        Args:
            prediction (torch.Tensor): Model output tensor of shape (max_length, num_chars)
            length (int): Number of characters to decode
            
        Returns:
            str: Decoded CAPTCHA text
        """
        pred_chars = []
        for i in range(length):
            # Get the character with highest probability for each position
            char_idx = torch.argmax(prediction[i]).item()
            pred_chars.append(self.idx_to_char[char_idx])
        return ''.join(pred_chars)

def get_dataloader(data_dir, batch_size=32, shuffle=True):
    """
    Create a DataLoader for the CAPTCHA dataset with standard preprocessing.
    
    Args:
        data_dir (str): Directory containing CAPTCHA images
        batch_size (int): Number of images per batch (default: 32)
        shuffle (bool): Whether to shuffle the data (default: True)
        
    Returns:
        tuple: (dataloader, dataset)
            - dataloader: PyTorch DataLoader instance
            - dataset: CaptchaDataset instance
    """
    # Define image preprocessing pipeline
    transform = transforms.Compose([
        transforms.Resize((64, 160)),  # Resize to fixed dimensions
        transforms.ToTensor(),         # Convert PIL image to tensor
        # Normalize using ImageNet statistics for better convergence
        transforms.Normalize(mean=[0.485, 0.456, 0.406], std=[0.229, 0.224, 0.225])
    ])
    
    dataset = CaptchaDataset(data_dir, transform=transform)
    dataloader = DataLoader(dataset, batch_size=batch_size, shuffle=shuffle)
    
    return dataloader, dataset