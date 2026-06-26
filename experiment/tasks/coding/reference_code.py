import torch
import torch.nn as nn


class Model(nn.Module):
    def __init__(self, feature_size):
        super().__init__()
        self.scale = nn.Parameter(torch.randn(feature_size))
        self.bias = nn.Parameter(torch.randn(feature_size))

    def forward(self, x):
        return torch.relu(x * self.scale + self.bias)


batch_size = 1024
feature_size = 4096


def get_inputs():
    return [torch.rand(batch_size, feature_size)]


def get_init_inputs():
    return [feature_size]
