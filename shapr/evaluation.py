"""Evaluate data with respect to ground truth and plot it.

This script generates plots for evaluating runs of SHAPR. Different
scenarios or models can be tested against a "ground truth" data set
and the results are stored in PDF files.

This script requres a configuration file to work.
"""

import argparse
import collections
import json
import os
import trimesh

from tqdm import tqdm

import numpy as np
import pandas as pd

from skimage import measure
from skimage.filters import threshold_otsu
from skimage.io import imread

import matplotlib.pyplot as plt
import seaborn as sns


plt.rcParams.update({
    'font.family': 'serif',
    'text.usetex': True,
    'pgf.rcfonts': False,
})


def parse_config(filename):
    """Parse JSON configuration file.

    Parameters
    ----------
    filename : str
        Input filename; must be a JSON configuration file.

    Returns
    -------
    Tuple of configuration and target keys
        The parsed configuration is returned as a dictionary; for
        convenience purposes, source information and all target keys are
        returned as well.
    """
    with open(filename) as f:
        config = json.load(f)

    targets = [k for k in config.keys() if k.startswith('target_')]
    return config, targets


def norm_thres(data):
    """Perform Otsu's method for thresholding."""
    maxd = np.max(data)
    data = np.nan_to_num(data / maxd)
    if np.max(data) > 0:
        thresh = threshold_otsu(data)
        binary = data > thresh
    else:
        binary = data

    return binary * 1.0


def get_surface(obj):
    """Calculate surface area using a mesh."""
    verts_pred, faces_pred, _, _ = measure.marching_cubes(
        obj * 255.,
        method='lewiner'
    )
    surface_pred = measure.mesh_surface_area(verts_pred, faces_pred)
    return surface_pred


def IoU(y_true, y_pred):
    """Calculate IoU between ground truth and prediction."""
    intersection = y_true + y_pred
    intersection = np.count_nonzero(intersection > 1.5)
    union = y_true + y_pred
    union = np.count_nonzero(union > 0.5)
    return intersection / union


def get_roughness(obj):
    """Calculate surface roughness using mesh."""
    verts, faces, _, _ = measure.marching_cubes(
        obj * 255.,
        method='lewiner',
    )
    mesh = trimesh.Trimesh(vertices=verts, faces=faces, process=False)
    smesh = trimesh.smoothing.filter_humphrey(mesh)

    # Additional conversion requird since we are getting
    # a `TrackedArray` that does not play nice with SNS.
    roughness = np.mean(np.sqrt((np.sum((verts-smesh.vertices)**2))))
    roughness = np.asarray(roughness)

    return roughness


def swarmplot(data, label, ax):
    """Create swarmplot with specific label."""
    ax = sns.violinplot(
        data=data,
        showfliers=False,
        color='lightgray',
        boxprops={'facecolor': 'None'},
        orient='h',
        ax=ax
    )

    ax = sns.swarmplot(
        data=data,
        color='.25',
        size=1.5,
        orient='h',
        ax=ax
    )

    ax.set_xlabel(label, size=15)
    ax.set_xlim(-0.01, 1.01)


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('CONFIG', type=str, help='Configuration file')

    parser.add_argument(
        '-q', '--quick',
        action='store_true',
        help='If set, only calculates statistics that can be obtained '
             'efficiently.'
    )

    args = parser.parse_args()

    config, targets = parse_config(args.CONFIG)

    iou_inv = collections.defaultdict(list)
    volume = collections.defaultdict(list)
    surface = collections.defaultdict(list)
    roughness = collections.defaultdict(list)

    source_path = config['source']
    filenames = sorted(os.listdir(source_path))
    processed = []

    for filename in tqdm(filenames, desc='File'):
        source = imread(os.path.join(source_path, filename)) / 255.0

        # First check whether all files exist; else, we skip processing
        # in order to ensure consistent lists.
        skip = False
        for target_ in targets:
            target_path = os.path.join(config[target_]['path'], filename)

            if not os.path.exists(target_path):
                skip = True
                break

        if skip:
            continue
        else:
            processed.append(os.path.basename(filename))

        for target_ in targets:
            target_path = os.path.join(config[target_]['path'], filename)

            target = np.squeeze(
                norm_thres(np.nan_to_num(
                        imread(target_path)
                    )
                )
            )

            label = config[target_]['label']

            iou_inv[label].append(1 - IoU(source, target))
            volume[label].append(
                np.abs(np.sum(target) - np.sum(source)) / np.sum(source)
            )

            if not args.quick:
                source_surface = get_surface(source)
                surface[label].append(
                    np.abs(get_surface(target) - source_surface)
                    / source_surface
                )

                source_roughness = get_roughness(source)
                roughness[label].append(
                    np.abs(get_roughness(target) - source_roughness)
                    / source_roughness
                )

    # Since we rank data sets based on this quantity, it makes sense to
    # calculate a fixed data frame here.
    df_iou = pd.DataFrame.from_dict(iou_inv)
    df_iou['filename'] = processed

    print('Mean for IoU error:')
    print(df_iou.mean(axis='rows', numeric_only=True).values)

    for col in df_iou.select_dtypes('number').columns:
        print(df_iou[[col, 'filename']].sort_values(by=col)[:5])

    df_volume = pd.DataFrame.from_dict(volume)

    print('Mean for volume:')
    print(df_volume.mean(axis='rows', numeric_only=True).values)

    fig, axes = plt.subplots(
        nrows=4 - 2 * args.quick,
        squeeze=True,
        figsize=(5, 6)
    )

    swarmplot(df_iou, '1 - IoU', axes[0])
    swarmplot(df_volume, 'Volume error', axes[1])

    filenames = list(map(os.path.basename, filenames))

    if len(filenames) > len(processed):
        skipped = sorted(set(filenames) - set(processed))
        print(f'Skipped some files: {skipped}')

    if not args.quick:
        swarmplot(
            pd.DataFrame.from_dict(surface),
            'Surface error',
            axes[2]
        )

        swarmplot(
            pd.DataFrame.from_dict(roughness),
            'Roughness error',
            axes[3]
        )

    plt.tight_layout()
    plt.savefig(config['output'], backend='pgf')
    plt.show()

########################################################################
# HIC SVNT DRACONES
########################################################################

mask_path = "/media/dominik/LaCie/SHAPR_pytorch/Organoid/mask/"

volume = []
mask_area = []

files = os.listdir(pytorch_path)
print(len(files))

fname = []
for index, file in enumerate(files): 
    pytorchdata = np.squeeze(norm_thres(np.nan_to_num(imread(pytorch_path + file))))
    mask = np.squeeze(norm_thres(np.nan_to_num(imread(mask_path + file))))
    volume.append(np.sum(pytorchdata))

    mask_area.append(np.sum(mask))

plt.scatter(mask_area, volume, s = 1)
plt.show()
