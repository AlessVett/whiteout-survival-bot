import torch
import torch.nn as nn
import torch.nn.functional as F

class CaptchaCNN(nn.Module):
    def __init__(self, num_chars=36, max_length=5):
        super(CaptchaCNN, self).__init__()
        self.num_chars = num_chars
        self.max_length = max_length
        
        self.conv1 = nn.Conv2d(3, 32, kernel_size=3, padding=1)
        self.conv2 = nn.Conv2d(32, 64, kernel_size=3, padding=1)
        self.conv3 = nn.Conv2d(64, 128, kernel_size=3, padding=1)
        self.conv4 = nn.Conv2d(128, 256, kernel_size=3, padding=1)
        
        self.pool = nn.MaxPool2d(2, 2)
        self.dropout = nn.Dropout(0.3)
        
        self.fc1 = nn.Linear(256 * 4 * 10, 1024)
        self.fc2 = nn.Linear(1024, 512)
        
        self.char_outputs = nn.ModuleList([
            nn.Linear(512, num_chars) for _ in range(max_length)
        ])
        
    def forward(self, x):
        x = self.pool(F.relu(self.conv1(x)))
        x = self.pool(F.relu(self.conv2(x)))
        x = self.pool(F.relu(self.conv3(x)))
        x = self.pool(F.relu(self.conv4(x)))
        
        x = x.view(x.size(0), -1)
        
        x = F.relu(self.fc1(x))
        x = self.dropout(x)
        x = F.relu(self.fc2(x))
        x = self.dropout(x)
        
        outputs = []
        for i in range(self.max_length):
            outputs.append(self.char_outputs[i](x))
        
        return torch.stack(outputs, dim=1)