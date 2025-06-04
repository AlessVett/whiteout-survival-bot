"""
Neural Network Model for CAPTCHA Recognition

This module defines the CNN architecture used for solving CAPTCHAs.
The model uses convolutional layers to extract features from CAPTCHA images
and separate output heads for each character position.
"""

import torch
import torch.nn as nn
import torch.nn.functional as F


class CaptchaCNN(nn.Module):
    """
    Convolutional Neural Network for CAPTCHA text recognition.
    
    Architecture:
    - 4 convolutional layers with increasing channels (32->64->128->256)
    - MaxPooling after each convolutional layer
    - 2 fully connected layers (1024->512 units)
    - Separate output heads for each character position
    - Dropout for regularization
    
    Args:
        num_chars (int): Number of possible characters (default: 36 for a-z + 0-9)
        max_length (int): Maximum CAPTCHA length (default: 5)
    """
    
    def __init__(self, num_chars=36, max_length=5):
        super(CaptchaCNN, self).__init__()
        self.num_chars = num_chars
        self.max_length = max_length
        
        # Convolutional layers with increasing filter sizes
        # Input: 3 channels (RGB), Output: progressively more feature maps
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        
        # Pooling layer reduces spatial dimensions by factor of 2
        self.pool = nn.MaxPool2d(2, 2)
        
        # Dropout for regularization during training
        self.dropout = nn.Dropout(0.3)
        
        # Fully connected layers
        # Input size: 256 channels * 4 height * 10 width (after 4 pooling operations on 64x160 input)
        self.fc1 = nn.Linear(256 * 4 * 10, 1024)
        self.fc2 = nn.Linear(1024, 512)
        
        # Separate output head for each character position
        # This allows the model to learn position-specific patterns
        self.char_outputs = nn.ModuleList([
            nn.Linear(512, num_chars) for _ in range(max_length)
        ])
        
    def forward(self, x):
        """
        Forward pass through the network.
        
        Args:
            x (torch.Tensor): Input tensor of shape (batch_size, 3, 64, 160)
            
        Returns:
            torch.Tensor: Output tensor of shape (batch_size, max_length, num_chars)
                         containing character predictions for each position
        """
        # Apply convolutional layers with ReLU activation and pooling
        # Each pooling reduces dimensions by factor of 2
        x = self.pool(F.relu(self.conv1(x)))  # -> (batch, 32, 32, 80)
        x = self.pool(F.relu(self.conv2(x)))  # -> (batch, 64, 16, 40)
        x = self.pool(F.relu(self.conv3(x)))  # -> (batch, 128, 8, 20)
        x = self.pool(F.relu(self.conv4(x)))  # -> (batch, 256, 4, 10)
        
        # Flatten the feature maps for fully connected layers
        x = x.view(x.size(0), -1)  # -> (batch, 256*4*10)
        
        # Apply fully connected layers with dropout
        x = F.relu(self.fc1(x))    # -> (batch, 1024)
        x = self.dropout(x)
        x = F.relu(self.fc2(x))    # -> (batch, 512)
        x = self.dropout(x)
        
        # Generate predictions for each character position
        outputs = []
        for i in range(self.max_length):
            outputs.append(self.char_outputs[i](x))  # -> (batch, num_chars)
        
        # Stack outputs to create tensor of shape (batch, max_length, num_chars)
        return torch.stack(outputs, dim=1)