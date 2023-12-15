"""
MIT License:
Copyright (c) 2023 Muhammad Umer

Training script for Pytorch models [Pytorch Lightning]

Usage:
    >>> python train.py --help
    >>> python train.py --data-dir <path> --model-dir <path> --batch-size <int> --num-workers <int> --num-epochs <int> --lr <float> --rich-progress --accelerator <str> --devices <str> --weights <path> --resume --test-only
    
Example:
    Use the default config:
    >>> python train.py
    
    Override the config:
    >>> python train.py --data-dir data --model-dir models --batch-size 128 --num-workers 8 --num-epochs 100 --lr 0.001 --rich-progress --accelerator gpu --devices 1 --weights models/best_model.ckpt --resume --test-only
"""

import os
import sys

sys.path.append(os.path.join(os.getcwd(), "..", "."))  # add parent dir to path

import argparse
import warnings
from typing import Tuple

import lightning as pl
import lightning.pytorch.callbacks as pl_callbacks
import matplotlib.pyplot as plt
import timm
import torch
import torch.nn as nn
import torch.optim as optim
import torch.optim.lr_scheduler as lr_scheduler
import torchmetrics
from termcolor import colored
from torch import nn, optim
from torchvision import transforms

from config import *
from data import *
from models import EfficientNetV2

# Common setup
warnings.filterwarnings("ignore")
torch.set_float32_matmul_precision("medium")
plt.rcParams["font.family"] = "STIXGeneral"


def train(
    cfg,
    accelerator,
    devices,
    rich_progress,
    test_mode=False,
    resume=False,
    weights=None,
):
    # Training
    train_transform, test_transform = get_cifar100_transforms()

    train_dataloader, val_dataloader, test_dataloader = get_cifar100_loaders(
        cfg.data_dir,
        cfg.batch_size,
        cfg.num_workers,
        train_transform,
        test_transform,
        val_size=0.1,
    )

    class ImageClassifier(pl.LightningModule):
        def __init__(self, model: nn.Module, cfg: dict):
            super().__init__()
            self.model = model
            self.cfg = cfg
            self.loss = nn.CrossEntropyLoss()

        def forward(self, x: torch.Tensor):
            return self.model(x)

        def training_step(
            self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int
        ):
            x, y = batch
            y_hat = self(x)
            loss = self.loss(y_hat, y)
            self.log("train_loss", loss, prog_bar=True)
            return loss

        def validation_step(
            self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int
        ):
            x, y = batch
            y_hat = self(x)
            loss = self.loss(y_hat, y)
            self.log("val_loss", loss, prog_bar=True)

            # calculate accuracy
            _, preds = torch.max(y_hat, dim=1)
            acc = torchmetrics.functional.accuracy(
                preds, y, num_classes=100, task="multiclass"
            )
            self.log("val_acc", acc)

            return loss

        def test_step(self, batch: Tuple[torch.Tensor, torch.Tensor], batch_idx: int):
            x, y = batch
            y_hat = self(x)

            # calculate accuracy
            _, preds = torch.max(y_hat, dim=1)
            acc = torchmetrics.functional.accuracy(
                preds, y, num_classes=100, task="multiclass"
            )
            self.log("test_acc", acc)

        def configure_optimizers(self):
            optimizer = optim.Adam(self.parameters(), lr=self.cfg.lr)
            scheduler = lr_scheduler.StepLR(optimizer, step_size=30, gamma=0.1)
            return [optimizer], [scheduler]

    theme = pl_callbacks.progress.rich_progress.RichProgressBarTheme(
        description="black",
        progress_bar="cyan",
        progress_bar_finished="green",
        progress_bar_pulse="#6206E0",
        batch_progress="cyan",
        time="grey82",
        processing_speed="grey82",
        metrics="black",
    )

    # Create the model
    model = EfficientNetV2(num_classes=cfg.num_classes)
    model = ImageClassifier(model, cfg)

    # Load from checkpoint if weights are provided
    if weights is not None:
        model.load_state_dict(torch.load(weights)["state_dict"])

    # Create a PyTorch Lightning trainer with the required callbacks
    if rich_progress:
        trainer = pl.Trainer(
            accelerator=accelerator,
            devices=devices,
            max_epochs=cfg.num_epochs,
            enable_model_summary=False,
            callbacks=[
                pl_callbacks.RichModelSummary(max_depth=3),
                pl_callbacks.RichProgressBar(theme=theme),
                pl_callbacks.ModelCheckpoint(
                    dirpath=cfg.model_dir,
                    filename="best_model",
                ),
            ],
        )
    else:
        trainer = pl.Trainer(
            accelerator=accelerator,
            devices=devices,
            max_epochs=cfg.num_epochs,
            enable_model_summary=False,
            callbacks=[
                pl_callbacks.ModelSummary(max_depth=3),
                pl_callbacks.ModelCheckpoint(
                    dirpath=cfg.model_dir,
                    filename="best_model",
                ),
            ],
        )

    # Train the model
    if not test_mode:
        if resume:
            trainer.fit(model, train_dataloader, val_dataloader, ckpt_path=weights)
        trainer.fit(model, train_dataloader, val_dataloader)

    # Evaluate the model on the test set
    trainer.test(model, test_dataloader)


if __name__ == "__main__":
    cfg = get_cifar100_config()

    # Add argument parsing with cfg overrides
    parser = argparse.ArgumentParser(description="Train a model on CIFAR100 dataset")
    parser.add_argument(
        "--data-dir", type=str, default=cfg.data_dir, help="Directory for the data"
    )
    parser.add_argument(
        "--model-dir", type=str, default=cfg.model_dir, help="Directory for the model"
    )
    parser.add_argument(
        "--batch-size", type=int, default=cfg.batch_size, help="Batch size for training"
    )
    parser.add_argument(
        "--num-workers",
        type=int,
        default=cfg.num_workers,
        help="Number of workers for data loading",
    )
    parser.add_argument(
        "--num-epochs",
        type=int,
        default=cfg.num_epochs,
        help="Number of epochs for training",
    )
    parser.add_argument(
        "--lr", type=float, default=cfg.lr, help="Learning rate for the optimizer"
    )
    parser.add_argument(
        "--rich-progress", action="store_true", help="Use rich progress bar"
    )
    parser.add_argument(
        "--accelerator",
        type=str,
        default="auto",
        help="Accelerator type (auto, gpu, tpu, etc.)",
    )
    parser.add_argument(
        "--devices",
        type=str,
        default="auto",
        help="Devices to use for training (auto, cpu, gpu, etc.)",
    )
    parser.add_argument(
        "--weights",
        type=str,
        default=None,
        help="Path to the weights file for the model",
    )
    parser.add_argument(
        "--resume",
        action="store_true",
        help="Resume training from the provided weights",
    )
    parser.add_argument(
        "--test-only", action="store_true", help="Only test the model, do not train"
    )
    args = parser.parse_args()

    cfg.update(args.__dict__)

    print(colored(f"Config:", "green"))
    print(cfg)

    # Train the model
    if args.devices != "auto":
        args.devices = int(args.devices)
    if (args.resume or args.test_only) and args.weights is None:
        raise ValueError(
            colored(
                "Provide the path to the weights file using --weights",
                "red",
            )
        )

    train(
        cfg,
        args.accelerator,
        args.devices,
        args.rich_progress,
        args.test_only,
        args.resume,
        args.weights if args.resume or args.test_only else None,
    )