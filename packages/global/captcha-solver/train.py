"""
Training Script for CAPTCHA Recognition Model

This module handles the training loop, validation, and model checkpointing
for the CAPTCHA recognition CNN.
"""

import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import random_split
import os
from model import CaptchaCNN
from dataset import get_dataloader


def train_model(data_dir, epochs=50, batch_size=32, learning_rate=0.001):
    """
    Train the CAPTCHA recognition model.
    
    Args:
        data_dir (str): Directory containing training images
        epochs (int): Number of training epochs (default: 50)
        batch_size (int): Batch size for training (default: 32)
        learning_rate (float): Learning rate for Adam optimizer (default: 0.001)
        
    Returns:
        CaptchaCNN: Trained model instance
    """
    # Check for GPU availability
    print(f"CUDA available: {torch.cuda.is_available()}")
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    # Load dataset
    dataloader, dataset = get_dataloader(data_dir, batch_size=batch_size, shuffle=True)
    
    # Split dataset into training and validation sets (80/20 split)
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    # Create separate data loaders for training and validation
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    # Initialize model, loss function, and optimizer
    model = CaptchaCNN(num_chars=36, max_length=5).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    # Track best validation accuracy for model checkpointing
    best_val_acc = 0.0
    
    # Training loop
    for epoch in range(epochs):
        # Training phase
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels, lengths in train_loader:
            # Move data to device (GPU if available)
            images, labels = images.to(device), labels.to(device)
            
            # Zero gradients
            optimizer.zero_grad()
            
            # Forward pass
            outputs = model(images)  # Shape: (batch_size, max_length, num_chars)
            
            # Calculate loss and accuracy for variable-length CAPTCHAs
            loss = 0
            correct = 0
            total = 0
            
            # Process each image in the batch
            for i in range(labels.size(0)):
                length = lengths[i].item()  # Actual CAPTCHA length
                # Calculate loss for each character position
                for j in range(length):
                    # CrossEntropyLoss expects class indices, not one-hot encoding
                    loss += criterion(outputs[i, j].unsqueeze(0), torch.argmax(labels[i, j]).unsqueeze(0))
                    # Check if prediction matches label
                    if torch.argmax(outputs[i, j]) == torch.argmax(labels[i, j]):
                        correct += 1
                    total += 1
            
            # Backward pass and optimization
            loss.backward()
            optimizer.step()
            
            # Accumulate metrics
            train_loss += loss.item()
            train_correct += correct
            train_total += total
        
        # Validation phase
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        # Disable gradient computation for validation
        with torch.no_grad():
            for images, labels, lengths in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                
                # Calculate validation metrics
                loss = 0
                correct = 0
                total = 0
                
                for i in range(labels.size(0)):
                    length = lengths[i].item()
                    for j in range(length):
                        loss += criterion(outputs[i, j].unsqueeze(0), torch.argmax(labels[i, j]).unsqueeze(0))
                        if torch.argmax(outputs[i, j]) == torch.argmax(labels[i, j]):
                            correct += 1
                        total += 1
                
                val_loss += loss.item()
                val_correct += correct
                val_total += total
        
        # Calculate accuracies
        train_acc = train_correct / train_total if train_total > 0 else 0
        val_acc = val_correct / val_total if val_total > 0 else 0
        
        # Print epoch results
        print(f'Epoch [{epoch+1}/{epochs}]')
        print(f'Train Loss: {train_loss/len(train_loader):.4f}, Train Acc: {train_acc:.4f}')
        print(f'Val Loss: {val_loss/len(val_loader):.4f}, Val Acc: {val_acc:.4f}')
        print('-' * 50)
        
        # Save model if validation accuracy improves
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'best_captcha_model.pth')
            print(f'New best model saved with validation accuracy: {val_acc:.4f}')
    
    return model

if __name__ == "__main__":
    # Training configuration
    data_dir = "letters"  # Directory containing CAPTCHA images
    
    # Train model with specified parameters
    # Note: 4000 epochs was used for the best model, though default is 50
    model = train_model(data_dir, epochs=4000, batch_size=16, learning_rate=0.001)