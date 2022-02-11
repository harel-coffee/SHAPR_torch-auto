"""Run hyperparameter sweep."""

import argparse

from shapr import run_train
from shapr._settings import SHAPRConfig


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    default_config = SHAPRConfig()

    # Check which arguments we can actually override from outside.
    shapr_args = set()

    for k, _ in default_config._SHAPRConfig__config_param_names.items():
        parser.add_argument(
            f'--{k}',
            type=type(default_config.__getattribute__(k)),
        )

        shapr_args.add(k)

    args = parser.parse_args()

    # Prepare arguments that were overridden by the user from the
    # command-line (or via a sweep, for instance).
    overrides = {}

    for k, v in vars(args).items():
        if k in shapr_args and v is not None:
            overrides[k] = v

    run_train(overrides=overrides)