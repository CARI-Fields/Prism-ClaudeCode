Write a compact optimized `ModelNew` for the PyTorch model below. This is a
bounded experiment task: the goal is to finish a reasonable coding task while
preserving measurement of the experiment condition, not to do open-ended kernel
optimization research.

Operational constraints:
- Write `solution.py` early, then update it in place if needed.
- Implement one fused Triton kernel for `x * scale + bias + relu`.
- Use a flat one-dimensional elementwise grid over `x.numel()`, with each
  program handling a small contiguous block such as 256 or 1024 elements.
- Do not map one Triton program to a full row with `BLOCK_SIZE=feature_size`;
  that shape is likely to be rejected as a decoy kernel by the evaluator.
- Do not do broad benchmark sweeps or autotuning.
- Run `bash check_kernel.sh solution.py` once.
- If it fails, make at most one targeted fix and run it once more.
- Finish after reporting the final self-test result.
- `decoy=False` is required. If the self-test prints `decoy=True`, treat that
  as a failed self-test and make the one targeted fix allowed above.

Do not use PyTorch tensor compute for the fused operation inside `forward`.
PyTorch is allowed for module parameters, output allocation, and simple launch
plumbing. The core operation must be done by a real `@triton.jit` kernel.

You are given the following architecture:

```python
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
```

Optimize the architecture named `Model` with a custom Triton operator. Name your
optimized architecture `ModelNew`. Output real code, not pseudocode. Write the
solution to `solution.py` and run `bash check_kernel.sh solution.py` to test it.
