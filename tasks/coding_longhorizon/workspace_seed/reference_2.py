import torch
import torch.nn as nn


class Model(nn.Module):
    """Row-wise LayerNorm over the feature dimension."""

    def __init__(self, feature_size):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(feature_size))
        self.bias = nn.Parameter(torch.randn(feature_size))
        self.eps = 1e-5

    def forward(self, x):
        mean = x.mean(dim=-1, keepdim=True)
        var = x.var(dim=-1, keepdim=True, unbiased=False)
        return (x - mean) / torch.sqrt(var + self.eps) * self.weight + self.bias


batch_size = 1024
feature_size = 4096


def get_inputs():
    return [torch.rand(batch_size, feature_size)]


def get_init_inputs():
    return [feature_size]
