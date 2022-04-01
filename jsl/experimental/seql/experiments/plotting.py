
import jax.numpy as jnp

import seaborn as sns
from matplotlib import pyplot as plt

from functools import reduce


agents = { "kf": 0,
           "eekf": 0,
           "exact bayes": 1,
            "sgd": 2,
            "laplace": 3,
            "bfgs": 4,
            "lbfgs": 5,
            "nuts": 6,
            "sgld": 7,
            }

colors = {k : sns.color_palette("Paired")[v]
          for k,v in agents.items()}


def sort_data(x, y):
    *_, nfeatures = x.shape
    *_, ntargets = y.shape

    x_ = x.reshape((-1, nfeatures))
    y_ = y.reshape((-1, ntargets))
    
    if nfeatures>1:
        indices = jnp.argsort(x_[:, 1])
    else:
        indices = jnp.argsort(x_[:, 0])

    x_ = x_[indices]
    y_ = y_[indices]

    return x_, y_

def plot_regression_posterior_predictive(ax, agent, env, belief, agent_name, t):
    nprev = reduce(lambda x, y: x*y,
                env.X_test[:t].shape[:-1])

    X_train, Y_train = env.X_test[:t+1], env.y_test[:t+1]

    nfeatures = X_train.shape[-1]
    prev_x = X_train.reshape((-1, nfeatures))[:nprev, 1]
    prev_y = Y_train.reshape((-1, 1))[:nprev]

    cur_x = X_train.reshape((-1, nfeatures))[nprev:, 1]
    cur_y = Y_train.reshape((-1, 1))[nprev:]
    
    # Plot training data
    ax.scatter(prev_x, prev_y, c="#40476D")
    ax.scatter(cur_x, cur_y , c="#c33149")

    X_train, Y_train = sort_data(X_train, Y_train)
    mu, sigma = agent.predict(belief, X_train)

    ypred = jnp.squeeze(mu)
    error = jnp.squeeze(sigma)

    ground_truth =  X_train @ env.ground_truth 
    ax.plot(jnp.squeeze(X_train[:, 1]),
            jnp.squeeze(ground_truth),
            color="#72A276",
            linewidth=2)

    ax.errorbar(jnp.squeeze(X_train[:, 1]),
                ypred,
                yerr=error,
                color=colors[agent_name])
    ax.fill_between(jnp.squeeze(X_train[:, 1]),
                    ypred + error,
                    ypred - error,
                    alpha=0.2,
                    color=colors[agent_name])

def plot_classification_2d(ax,
                        env,
                        grid,
                        grid_preds,
                        t):
    
    sns.set_style("whitegrid")
    cmap = sns.diverging_palette(250, 12, s=85, l=25, as_cmap=True)

    X_train, Y_train = sort_data(env.X_train[:t+1], env.y_train[:t+1])
    nclasses = Y_train.max()

    if nclasses == 1 and grid_preds.shape[-1] == 1:
        grid_preds = jnp.hstack([1- grid_preds, grid_preds])

    ax.contourf(grid[:, 1].reshape((100, 100)),
                grid[:, 2].reshape((100, 100)),
                grid_preds[:, 1].reshape((100,100)),
                cmap=cmap)
    
    for cls in range(nclasses + 1):
        indices = jnp.argwhere(Y_train == cls)
        
        # Plot training data
        ax.scatter(X_train[indices, 1],
                   X_train[indices, 2])