import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import random_split
import os
from model import CaptchaCNN
from dataset import get_dataloader

def train_model(data_dir, epochs=50, batch_size=32, learning_rate=0.001):
    print(torch.cuda.is_available())
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    print(f"Using device: {device}")
    
    dataloader, dataset = get_dataloader(data_dir, batch_size=batch_size, shuffle=True)
    
    train_size = int(0.8 * len(dataset))
    val_size = len(dataset) - train_size
    train_dataset, val_dataset = random_split(dataset, [train_size, val_size])
    
    train_loader = torch.utils.data.DataLoader(train_dataset, batch_size=batch_size, shuffle=True)
    val_loader = torch.utils.data.DataLoader(val_dataset, batch_size=batch_size, shuffle=False)
    
    model = CaptchaCNN(num_chars=36, max_length=5).to(device)
    criterion = nn.CrossEntropyLoss()
    optimizer = optim.Adam(model.parameters(), lr=learning_rate)
    
    best_val_acc = 0.0
    
    for epoch in range(epochs):
        model.train()
        train_loss = 0.0
        train_correct = 0
        train_total = 0
        
        for images, labels, lengths in train_loader:
            images, labels = images.to(device), labels.to(device)
            
            optimizer.zero_grad()
            outputs = model(images)
            
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
            
            loss.backward()
            optimizer.step()
            
            train_loss += loss.item()
            train_correct += correct
            train_total += total
        
        model.eval()
        val_loss = 0.0
        val_correct = 0
        val_total = 0
        
        with torch.no_grad():
            for images, labels, lengths in val_loader:
                images, labels = images.to(device), labels.to(device)
                outputs = model(images)
                
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
        
        train_acc = train_correct / train_total if train_total > 0 else 0
        val_acc = val_correct / val_total if val_total > 0 else 0
        
        print(f'Epoch [{epoch+1}/{epochs}]')
        print(f'Train Loss: {train_loss/len(train_loader):.4f}, Train Acc: {train_acc:.4f}')
        print(f'Val Loss: {val_loss/len(val_loader):.4f}, Val Acc: {val_acc:.4f}')
        print('-' * 50)
        
        if val_acc > best_val_acc:
            best_val_acc = val_acc
            torch.save(model.state_dict(), 'best_captcha_model.pth')
            print(f'New best model saved with validation accuracy: {val_acc:.4f}')
    
    return model

if __name__ == "__main__":
    data_dir = "letters"
    model = train_model(data_dir, epochs=1000, batch_size=16, learning_rate=0.001)