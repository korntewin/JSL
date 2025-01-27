import jax.numpy as jnp
from jax import jit, value_and_grad

import optax

import chex

import typing_extensions
from typing import Any, NamedTuple

import warnings
from functools import partial

from jsl.experimental.seql.agents.agent_utils import Memory
from jsl.experimental.seql.agents.base import Agent

Params = Any
Optimizer = NamedTuple


# https://github.com/deepmind/optax/blob/252d152660300fc7fe22d214c5adbe75ffab0c4a/optax/_src/transform.py#L35
class TraceState(NamedTuple):
    """Holds an aggregation of past updates."""
    trace: chex.ArrayTree


class ModelFn(typing_extensions.Protocol):
    def __call__(self,
                 params: Params,
                 x: chex.Array):
        ...


class LossFn(typing_extensions.Protocol):
    def __call__(self,
                 params: Params,
                 x: chex.Array,
                 y: chex.Array,
                 model_fn: ModelFn) -> float:
        ...


class BeliefState(NamedTuple):
    params: Params
    opt_state: TraceState


class Info(NamedTuple):
    loss: float


def sgd_agent(classification: bool,
              loss_fn: LossFn,
              model_fn: ModelFn,
              optimizer: Optimizer = optax.adam(1e-2),
              obs_noise: float = 0.01,
              buffer_size: int = jnp.inf,
              nepochs: int = 20,
              threshold: int = 1):
    assert threshold <= buffer_size

    memory = Memory(buffer_size)
    partial_loss_fn = partial(loss_fn, model_fn=model_fn)
    value_and_grad_fn = jit(value_and_grad(partial_loss_fn))

    def init_state(params: Params):
        opt_state = optimizer.init(params)
        return BeliefState(params, opt_state)

    def update(key: chex.PRNGKey,
               belief: BeliefState,
               x: chex.Array,
               y: chex.Array):

        assert buffer_size >= len(x)
        x_, y_ = memory.update(x, y)

        if len(x_) < threshold:
            warnings.warn("There should be more data.", UserWarning)
            info = Info(False, -1, jnp.inf)
            return belief, info

        params = belief.params
        opt_state = belief.opt_state

        for _ in range(nepochs):
            loss, grads = value_and_grad_fn(params, x_, y_)
            updates, opt_state = optimizer.update(grads, opt_state)
            params = optax.apply_updates(params, updates)

        return BeliefState(params, opt_state), Info(loss)

    def apply(params: chex.ArrayTree,
              x: chex.Array):

        n = len(x)
        predictions = model_fn(params, x).reshape((n, -1))

        return predictions

    def sample_params(key: chex.PRNGKey,
                      belief: BeliefState):
        return belief.params

    return Agent(classification, init_state, update, apply, sample_params)