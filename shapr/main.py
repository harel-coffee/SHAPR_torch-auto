from shapr.utils import *
from shapr._settings import SHAPRConfig
from shapr.data_generator import *
#from shapr.model import netSHAPR, netDiscriminator
import torch.optim as optim
from tqdm import tqdm
from torch.utils.data import DataLoader, random_split
from pathlib import Path
import wandb
import logging
import pytorch_lightning as pl
from model import SHAPR, LightningSHAPRoptimization, LightningSHAPR_GANoptimization
from data_generator import SHAPRDataset
from sklearn.model_selection import train_test_split
from pytorch_lightning.callbacks import ModelCheckpoint, EarlyStopping
import glob
from pytorch_lightning import loggers as pl_loggers
import torch

PARAMS = {"num_filters": 10,
      "dropout": 0.
}

"""
Set the path where the following folders are located: 
- obj: containing the 3D groundtruth segmentations 
- mask: containg the 2D masks 
- image: containing the images from which the 2D masks were segmented (e.g. brightfield)
All input data is expected to have the same x and y dimensions and the obj (3D segmentations to have a z-dimension of 64.
The filenames of corresponding files in the obj, mask and image ordner are expeted to match.
"""


def run_train(amp: bool = False, params=None):
    device = torch.device("cuda:0" if torch.cuda.is_available() else "cpu")
    settings = SHAPRConfig(params=params)

    # Handle GPU vs CPU selection
    if device == torch.device("cpu"):
        gpus = None
    else:
        gpus = 1

    print(settings)
    """
    Get the filenames
    """
    filenames = os.listdir(os.path.join(settings.path, "obj/"))

    """
    We train the model on all data on 5 folds, while the folds are randomly split
    """
    kf = KFold(n_splits=5)
    os.makedirs(os.path.join(settings.path, "logs"), exist_ok=True)

    for fold, (cv_train_indices, cv_test_indices) in enumerate(kf.split(filenames)):
        cv_train_filenames = [str(filenames[i]) for i in cv_train_indices]
        cv_test_filenames = [str(filenames[i]) for i in cv_test_indices]

        """
        From the train set we use 20% of the files as validation during training 
        """
        cv_train_filenames, cv_val_filenames = train_test_split(cv_train_filenames, test_size=0.2)

        checkpoint_callback = ModelCheckpoint(
            monitor="val_loss",
            dirpath=os.path.join(settings.path, "logs"),
            filename="SHAPR_training-{epoch:02d}-{val_loss:.2f}",
            save_top_k=3,
            mode="min",
        )
        early_stopping_callback = EarlyStopping(monitor='val_loss', patience=5)
        tb_logger = pl_loggers.TensorBoardLogger("logs/")
        SHAPRmodel = LightningSHAPRoptimization(settings, cv_train_filenames, cv_val_filenames)
        SHAPR_trainer = pl.Trainer(
            max_epochs=settings.epochs_SHAPR,
            callbacks=[checkpoint_callback,
            early_stopping_callback], logger=tb_logger,
            gpus=gpus
        )
        SHAPR_trainer.fit(model= SHAPRmodel)
        torch.save({
            'state_dict': SHAPRmodel.state_dict(),
        }, os.path.join(settings.path, "logs/")+"SHAPR_training.ckpt")

        """
        After training SHAPR for the set number of epochs, we train the adverserial model
        """
        early_stopping_callback = EarlyStopping(monitor='val_loss', patience=5)
        checkpoint_callback = ModelCheckpoint(
            monitor="val_loss",
            dirpath=os.path.join(settings.path, "logs"),
            verbose=True,
            filename="SHAPR_GAN_training-{epoch:02d}-{val_loss:.2f}",
            save_top_k=3,
            mode="min",
        )

        SHAPR_GANmodel = LightningSHAPR_GANoptimization(settings, cv_train_filenames, cv_val_filenames)

        SHAPR_GAN_trainer = pl.Trainer(
            callbacks=[early_stopping_callback, checkpoint_callback],
            max_epochs=settings.epochs_cSHAPR,logger=tb_logger,
            gpus=gpus
        )
        SHAPR_GAN_trainer.fit(model=SHAPR_GANmodel)

        """
        The 3D shape of the test data for each fold will be predicted here
        """
        if settings.epochs_cSHAPR > 0:
            with torch.no_grad():
                SHAPR_GANmodel.eval()
                for test_file in cv_test_filenames:
                    image = torch.from_numpy(get_test_image(settings, test_file))
                    img = image.float()
                    output = SHAPR_GANmodel(img)
                    os.makedirs(settings.result_path, exist_ok=True)
                    prediction = output.cpu().detach().numpy()
                    imsave(os.path.join(settings.result_path, test_file), (255 * prediction).astype("uint8"))

        else:
            with torch.no_grad():
                SHAPRmodel.eval()
                for test_file in cv_test_filenames:
                    image = torch.from_numpy(get_test_image(settings, test_file))
                    img = image.float()
                    output = SHAPRmodel(img)
                    os.makedirs(settings.result_path, exist_ok=True)
                    prediction = output.cpu().detach().numpy()
                    imsave(os.path.join(settings.result_path, test_file), (255 * prediction).astype("uint8"))


def run_evaluation():

    print(settings)

    #TODO

    """
    Get the filenames
    """
    '''test_filenames = os.listdir(os.path.join(settings.path, "obj"))

    model2D = netSHAPR(PARAMS)
    model2D.load_weights(settings.pretrained_weights_path)

    """
    If pretrained weights should be used, please add them here:
    These weights will be used for all folds
    """

    """
    The 3D shape of the test data for each fold will be predicted here
    """
    test_data = data_generator_test_set(settings.path, test_filenames)

    predict = model2D.predict_generator(test_data, steps = len(test_filenames))
    print(np.shape(predict))

    """
    The predictions on the test set for each fold will be saved to the results folder
    """
    #save predictions
    print(np.shape(predict))
    i = 0
    for i, test_filename in enumerate(test_filenames):
        result = predict[i,...]*255
        os.makedirs(settings.result_path, exist_ok=True)
        imsave(settings.result_path + test_filename, result.astype("uint8"))
        i = i+1        
    '''

