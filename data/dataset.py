"""
Dataset class for CIFAR100.
"""
import os
import pickle

import numpy as np
import torch
from PIL import Image
from torch.utils.data import Dataset
from torch.utils.data.dataset import random_split
from torchvision.datasets import ImageFolder


class CIFAR100(Dataset):
    """
    Dataset class for CIFAR100.

    CIFAR100 dataset is expected to have the following directory structure.
    root
    ├── cifar-100-python
    │   ├── meta
    │   ├── test
    └── └── train

    Args:
        root (string): Root directory of dataset.
        train (bool, optional): If True, creates dataset from training set,
        otherwise creates from test set.
        transform (callable, optional): A function/transform that takes in an
        PIL image and returns a transformed version.
    """

    def __init__(self, root, train=True, transform=None):
        self.root = os.path.expanduser(root)
        self.train = train
        self.transform = transform

        if self.train:
            self.train_data, self.train_labels = self._load_data("train")
        else:
            self.test_data, self.test_labels = self._load_data("test")

        self.classes = self._load_meta()["fine_label_names"]

    def __getitem__(self, index):
        """
        Args:
            index (int): Index
        Returns:
            tuple: (image, target) where target is index of the target class.
        """
        if self.train:
            img, target = self.train_data[index], self.train_labels[index]
        else:
            img, target = self.test_data[index], self.test_labels[index]

        img = Image.fromarray(img)

        if self.transform is not None:
            img = self.transform(img)

        return img, target

    def __len__(self):
        if self.train:
            return len(self.train_data)
        else:
            return len(self.test_data)

    def _load_data(self, name):
        """
        Load data from directory.
        Args:
            name (string): Name of directory.
        Returns:
            tuple: (data, labels)
        """
        path = os.path.join(self.root, "cifar-100-python", name)
        data = []
        labels = []
        with open(path, "rb") as f:
            if name == "train":
                entry = pickle.load(f, encoding="latin1")
            else:
                entry = pickle.load(f, encoding="latin1")
            data = entry["data"]
            labels = entry["fine_labels"]

        data = np.vstack(data).reshape(-1, 3, 32, 32)
        data = data.transpose((0, 2, 3, 1))

        return data, labels

    def _load_meta(self):
        """
        Load meta data from directory.
        Returns:
            dict: Dictionary of meta data.
        """
        path = os.path.join(self.root, "cifar-100-python", "meta")
        with open(path, "rb") as f:
            entry = pickle.load(f, encoding="latin1")
            return entry


def get_imagefolder_dataset(
    root, train_transform=None, test_transform=None, val_size=0.1
):
    """
    Get ImageFolder dataset.

    Args:
        root (string): Root directory of dataset.
        train_transform (callable, optional): A function/transform that takes
        in an PIL image and returns a transformed version.
        test_transform (callable, optional): A function/transform that takes
        in an PIL image and returns a transformed version.
        val_size (float, optional): If float, should be between 0.0 and 1.0
        and represent the proportion of the dataset to include in the validation split.
    Returns:
        tuple: (train_dataset, val_dataset, test_dataset)
    """

    # Assuming that images are organized as follows:
    # root/train/class_x/xxx.ext
    # root/test/class_x/xxx.ext

    train_dataset = ImageFolder(os.path.join(root, "train"), transform=train_transform)
    test_dataset = ImageFolder(os.path.join(root, "test"), transform=test_transform)

    if val_size > 0.0:
        val_size = int(len(train_dataset) * val_size)
        train_size = len(train_dataset) - val_size
        train_dataset, val_dataset = random_split(train_dataset, [train_size, val_size])
    else:
        val_dataset = None

    return train_dataset, val_dataset, test_dataset


def get_cifar100_dataset(root, train_transform=None, test_transform=None, val_size=0.1):
    """
    Get CIFAR100 dataset.

    Args:
        root (string): Root directory of dataset.
        train_transform (callable, optional): A function/transform that takes
        in an PIL image and returns a transformed version.
        test_transform (callable, optional): A function/transform that takes
        in an PIL image and returns a transformed version.
        val_size (float, optional): If float, should be between 0.0 and 1.0
        and represent the proportion of the dataset to include in the validation split.
    Returns:
        tuple: (train_dataset, val_dataset, test_dataset)
    """
    train_dataset = CIFAR100(root, train=True, transform=train_transform)
    test_dataset = CIFAR100(root, train=False, transform=test_transform)

    if val_size > 0.0:
        val_size = int(len(train_dataset) * val_size)
        train_size = len(train_dataset) - val_size
        train_dataset, val_dataset = random_split(train_dataset, [train_size, val_size])
    else:
        val_dataset = None

    return train_dataset, val_dataset, test_dataset


def get_cifar100_loaders(
    root,
    train_transform,
    test_transform,
    batch_size=128,
    num_workers=4,
    val_size=0.1,
    shuffle=True,
    dataset_type="default",
    return_steps=False,
):
    """
    Get CIFAR100 dataset.

    Args:
        root (string): Root directory of dataset.
        train_transform (callable): A function/transform that takes
        in an PIL image and returns a transformed version.
        test_transform (callable): A function/transform that takes
        in an PIL image and returns a transformed version.
        val_size (float, optional): If float, should be between 0.0 and 1.0
        and represent the proportion of the dataset to include in the validation split.
        shuffle (bool, optional): If True, the data will be split randomly.
        return_steps (bool, optional): If True, return number of steps per epoch.

    Returns:
        tuple: (train_dataset, val_dataset, test_dataset)
    """

    if dataset_type == "default":
        train_dataset, val_dataset, test_dataset = get_cifar100_dataset(
            root, train_transform, test_transform, val_size
        )
    elif dataset_type == "imagefolder":
        train_dataset, val_dataset, test_dataset = get_imagefolder_dataset(
            root, train_transform, test_transform, val_size
        )
    else:
        raise ValueError("Invalid dataset type. Choose from [default, imagefolder].")

    train_loader = torch.utils.data.DataLoader(
        train_dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True,
    )
    val_loader = torch.utils.data.DataLoader(
        val_dataset,
        batch_size=batch_size,
        shuffle=shuffle,
        num_workers=num_workers,
        pin_memory=True,
    )
    test_loader = torch.utils.data.DataLoader(
        test_dataset,
        batch_size=batch_size,
        shuffle=False,
        num_workers=num_workers,
        pin_memory=True,
    )

    if return_steps:
        steps_per_epoch = len(train_dataset) // batch_size
        return train_loader, val_loader, test_loader, steps_per_epoch
    else:
        return train_loader, val_loader, test_loader
