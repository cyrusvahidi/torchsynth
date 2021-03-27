# -*- coding: utf-8 -*-
"""lightningsynth.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/github/turian/torchsynth/blob/lightning-synth/examples/lightningsynth.ipynb

# lightningsynth

Profiling for our synth on GPUs

Make sure you are on GPU runtime

If this hasn't been merged to master yet, run:
```
!pip uninstall -y torchsynth
!pip install git+https://github.com/turian/torchsynth.git@lightning-synth
```
"""

#!pip uninstall -y torchsynth
#!pip install git+https://github.com/turian/torchsynth.git@lightning-synth

#!pip install torchvision

from typing import Any

import torch
import torch.tensor as T
from tqdm.auto import tqdm

import torch

# import torchvision.models as models
import torch.autograd.profiler as profiler
import pytorch_lightning as pl

from torchsynth.globals import SynthGlobals
from torchsynth.synth import Voice
import torchsynth.module

gpus = torch.cuda.device_count()
print("Usings %d gpus" % gpus)

# Note this is the batch size for our synth!
# i.e. this many synth sounds are generated at once
# Not the batch size of the datasets
BATCH_SIZE = 64

import multiprocessing

ncores = multiprocessing.cpu_count()
print(f"Using ncores {ncores} for generating batch numbers (low CPU usage)")


class batch_idx_dataset(torch.utils.data.Dataset):
    def __init__(self, num_batches):
        self.num_batches = num_batches

    def __getitem__(self, idx):
        return idx

    def __len__(self):
        return self.num_batches


# TODO Add this to torchsynth API
# see https://github.com/turian/torchsynth/issues/154
class TorchSynthCallback(pl.Callback):
    def on_test_batch_end(
        self,
        trainer,
        pl_module: pl.LightningModule,
        outputs: Any,
        batch: Any,
        batch_idx: int,
        dataloader_idx: int,
    ) -> None:
        assert batch.ndim == 1
        _ = pl_module(batch_idx)
        # I don't think the following is correct
        # _ = torch.stack([pl_module(i) for i in batch])


synth1B = batch_idx_dataset(1024 * 1024 * 1024 // BATCH_SIZE)

test_dataloader = torch.utils.data.DataLoader(synth1B, num_workers=0, batch_size=1)

synthglobals = SynthGlobals(batch_size=T(BATCH_SIZE))
voice = Voice(synthglobals).to("cuda")

accelerator = None
if gpus == 0:
    use_gpus = None
    precision = 32
else:
    # specifies all available GPUs (if only one GPU is not occupied,
    # auto_select_gpus=True uses one gpu)
    use_gpus = -1
    # TODO: Change precision?
    precision = 16
    if gpus > 1:
        accelerator = "ddp"

# Use deterministic?
trainer = pl.Trainer(
    precision=precision,
    gpus=use_gpus,
    auto_select_gpus=True,
    accelerator=accelerator,
    deterministic=True,
    max_epochs=0,
    callbacks=[TorchSynthCallback()],
)

trainer.test(voice, test_dataloaders=test_dataloader)
