import torch
import torch.nn as nn


class Model(nn.Module):
    """Fused GEMM epilogue: relu(x @ W + bias)."""

    def __init__(self, K, N):
        super().__init__()
        self.weight = nn.Parameter(torch.randn(K, N))
        self.bias = nn.Parameter(torch.randn(N))

    def forward(self, x):
        return torch.relu(x @ self.weight + self.bias)


M, K, N = 1024, 1024, 1024


def get_inputs():
    return [torch.rand(M, K)]


def get_init_inputs():
    return [K, N]
