# Copyright 2024 Huawei Technologies Co., Ltd
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ============================================================================
"""Test FlashAttention-v2-FP32"""
import unittest
import numpy as np

import mindspore as ms
from mindspore import ops, Tensor
from mindnlp.transformers.kernel_utils import compile_kernel
from mindnlp.utils.testing_utils import require_mindspore_gpu
from mindspore._c_expression import _framework_profiler_step_start
from mindspore._c_expression import _framework_profiler_step_end

def manual_attn_forward(query, key, value):
    r"""
    manual attention
    """
    embed_size = query.shape[-1]
    scaling_factor = ops.sqrt(ops.sqrt(Tensor(embed_size, ms.float32)))
    query = query / scaling_factor
    attn_mask = ops.ones((query.shape[-2], key.shape[-2]), ms.bool_).tril()
    attn = ops.matmul(query, key.swapaxes(-2, -1) / scaling_factor)
    attn = attn.masked_fill(attn_mask == 0, float("-inf"))
    attn = ops.softmax(attn, -1)
    output = ops.matmul(attn, value)
    return output

def manual_attn_backward(query, key, value):
    return ms.grad(manual_attn_forward, grad_position=(0, 1, 2))(
        query, key, value
    )

def test():
    r"""
    Unit test for flashattention forward.
    """
    # 加载flash cuda kernel
    device_target = ms.get_context("device_target")
    if device_target != "GPU":
        raise RuntimeError("FlashAttention operator only support GPU currently.")

    bs=8
    num_heads=12
    seq_len=32
    head_dim=64

    # seq_len must be multiple of Br
    Q = np.random.randn(bs, num_heads, seq_len, head_dim).astype(np.float32)
    K = np.random.randn(bs, num_heads, seq_len, head_dim).astype(np.float32)
    V = np.random.randn(bs, num_heads, seq_len, head_dim).astype(np.float32)
    # profiler = ms.Profiler()

    print("====== profiling forward pass ======")
    print("=== profiling MindSpore manual-attention(forward) === ")
    for i in range(5):
        output_manual_fwd = manual_attn_forward(
            ms.Tensor(Q), ms.Tensor(K), ms.Tensor(V)
        )
        (
            output_manual_bwd_dq,
            output_manual_bwd_dk,
            output_manual_bwd_dv,
        ) = manual_attn_backward(
            ms.Tensor(Q),
            ms.Tensor(K),
            ms.Tensor(V),
        )
    _framework_profiler_step_start()
    for i in range(10):
        output_manual_fwd = manual_attn_forward(
            ms.Tensor(Q), ms.Tensor(K), ms.Tensor(V)
        )
        (
            output_manual_bwd_dq,
            output_manual_bwd_dk,
            output_manual_bwd_dv,
        ) = manual_attn_backward(
            ms.Tensor(Q),
            ms.Tensor(K),
            ms.Tensor(V),
        )
    _framework_profiler_step_end()
test()
