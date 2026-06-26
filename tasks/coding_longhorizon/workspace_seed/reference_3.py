import torch
import torch.nn as nn


class Model(nn.Module):
    """Tiled GEMM: x @ W."""

    def __init__(self, K, N):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(K, N))

    def forward(self, x):
        return x @ self.weight


M, K, N = 1024, 1024, 1024


def get_inputs():
    return [torch.rand(M, K)]


def get_init_inputs():
    return [K, N]
