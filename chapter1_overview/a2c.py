"""
PyTorch implementation of Advantage Actor-Critic (A2C)
REINFORCE method usually suffers from high variance for gradient estimation and Actor-Critic method can only get a biased gradient estimation.
To combine these two methods, A2C uses a baseline function for normalization. By substracting the baseline function to the total return, the variance for gradient estimation is reduced. 
In practical, the baseline function is set to be the value function. The final target function is formulated as:
$$- \frac 1 N \sum_{n=1}^{N} log(\pi(a^n|s^n)) A^{\pi}(s^n, a^n)$$
Also in this way, the estimation is guaranteed to be unbiased.
Supplementary material for explaining why baseline function can reduce variance: <link https://github.com/opendilab/PPOxFamily/blob/main/chapter1_overview/chapter1_supp_a2c.pdf link>
This document mainly includes:
- Implementation of A2C error.
- Main function (test function)
"""
from collections import namedtuple
import torch
import torch.nn.functional as F

a2c_data = namedtuple('a2c_data', ['logit', 'action', 'value', 'adv', 'return_', 'weight'])
a2c_loss = namedtuple('a2c_loss', ['policy_loss', 'value_loss', 'entropy_loss'])


def a2c_error(data: namedtuple) -> namedtuple:
    """
    **Overview**:
        Implementation of A2C (Advantage Actor-Critic) <link https://arxiv.org/pdf/1602.01783.pdf link>
    """
    # Unpack data: $$<\pi(a|s), a, V(s), A^{\pi}(s, a), G_t, w>$$
    logit, action, value, adv, return_, weight = data
    # Prepare weight for default cases.
    if weight is None:
        weight = torch.ones_like(value)
    # Prepare policy distribution from logit and get log propability.
    dist = torch.distributions.categorical.Categorical(logits=logit)
    logp = dist.log_prob(action)
    # Entropy bonus: $$\frac 1 N \sum_{n=1}^{N} \pi(a^n|s^n) log(\pi(a^n|s^n))$$
    entropy_loss = (dist.entropy() * weight).mean()
    # Policy loss: $$- \frac 1 N \sum_{n=1}^{N} log(\pi(a^n|s^n)) A^{\pi}(s^n, a^n)$$
    policy_loss = -(logp * adv * weight).mean()
    # Value loss: $$\frac 1 N \sum_{n=1}^{N} (G_t^n - V(s^n))^2$$
    value_loss = (F.mse_loss(return_, value, reduction='none') * weight).mean()
    # Return final loss.
    return a2c_loss(policy_loss, value_loss, entropy_loss)


def test_a2c(weight):
    # Batch_size=4, action=32
    B, N = 4, 32
    # Generate logit, action, value, adv, return_.
    logit = torch.randn(B, N).requires_grad_(True)
    action = torch.randint(0, N, size=(B, ))
    value = torch.randn(B).requires_grad_(True)
    adv = torch.rand(B)
    return_ = torch.randn(B) * 2
    data = a2c_data(logit, action, value, adv, return_, weight)
    # Compute A2C error.
    loss = a2c_error(data)
    # Assert the loss is differentiable.
    assert all([l.shape == tuple() for l in loss])
    assert logit.grad is None
    assert value.grad is None
    total_loss = sum(loss)
    total_loss.backward()
    assert isinstance(logit.grad, torch.Tensor)
    assert isinstance(value.grad, torch.Tensor)


if __name__ == '__main__':
    random_weight = torch.rand(4) + 1
    test_a2c(random_weight)
