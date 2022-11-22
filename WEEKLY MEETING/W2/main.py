
import numpy as np
import torch
import torch.nn as nn
from torch import optim
from torch.utils.data import DataLoader
from torch.utils.data import Dataset
from sklearn.model_selection import train_test_split
from sklearn import preprocessing
from helpers import *
from neural_network import *
import gc
from torch.optim.lr_scheduler import ReduceLROnPlateau
from os import makedirs
from shutil import rmtree
import params
import pickle

##### GLOBAL ENVIRONMENT #####

# Define path for data and useful variables
name_file = 'LH_0/MHI_LH0_z=0.770.hdf5'
path_file = './outputs_test/'+ name_file
batch_size = 128
lr = 0.1
activation = 'sigmoid'

# Defining useful class to convert data in a format accepted by Pytorch
class Customized_dataset(Dataset):

    def __init__(self,X,target):
        super().__init__()
        self.X = torch.tensor(X)
        self.target = torch.tensor(target)
        self.dtype = self.X.dtype
    
    def __len__(self):
        return self.X.shape[0]

    def __getitem__(self, idx):

        return self.X[idx,:], self.target[idx]

##### MAIN SCRIPT TO RUN #####
if __name__ == '__main__':

    gc.collect()
    
    # Loading dataset
    X, y, dim_feat = get_single_dataset(params.path_file)

    # Line to try
    X = X[:1000]
    y = y[:1000]

    # Splitting data into train and test set
    X_train,X_test,y_train,y_test = train_test_split(X,y, test_size=0.2, random_state=2022)

    # Processing target data depending on activation function
    if params.activation == 'sigmoid':
        y_train = min_max_scaling(y_train)
        y_test = min_max_scaling(y_test)
    
    # Converting data into pytorch dataset object
    train_dataset = Customized_dataset(X_train,y_train)
    test_dataset = Customized_dataset(X_test,y_test)

    # Divide train and test data into iterable batches
    train_loader = DataLoader(dataset=train_dataset,batch_size=params.batch_size, shuffle=True,
                                num_workers=2, pin_memory=torch.cuda.is_available())

    test_loader = DataLoader(dataset=test_dataset,batch_size=params.batch_size, shuffle=True)

    dtype = train_dataset.dtype
    
    # Cleaning memory
    del train_dataset
    del test_dataset

    gc.collect()

#-----------------------------------------------------------------------------------------------
    # Defining num_epochs
    epochs = params.epochs

    # case of the first run
    if (params.first_run == True):
        
        # creation of the folder "checkpoints"
        makedirs('./checkpoints/', exist_ok=True)
        rmtree('./checkpoints/') # to remove all previous checkpoint files
        makedirs('./checkpoints/') 
    
        #Defining useful variables for epochs
        loss_epoch_train = [] # will contain all the train losses of the different epochs
        loss_epoch_test = [] # will contain all the test losses of the different epochs
        final_epoch=epochs
        prev_loss=10**5
        current_epoch=0

        # Importing model and move it on GPU (if available)
        model = my_FNN_increasing(dim_feat,dtype)
        if(torch.cuda.is_available()): # for the case of laptop with local GPU
            model = model.cuda()

        # Defining optimizer
        optimizer = optim.SGD(model.parameters(), lr=params.lr)

        # Defining a scheduler to adjust the learning rate
        scheduler = ReduceLROnPlateau(optimizer = optimizer, mode = 'min', factor = 0.1, patience = 20, min_lr=1e-12, verbose=True)

        #Defining loss function and shift it on GPU (if available)
        criterion = nn.MSELoss()

        if torch.cuda.is_available():
            criterion.cuda()

    else:
    # if it's not the first run, resume the training from last_model
        PATH = './checkpoints/last_model.pt'

        model = my_FNN_increasing(dim_feat,dtype)

        # Defining optimizer
        optimizer = optim.SGD(model.parameters(), lr=params.lr)

        # Defining a scheduler to adjust the learning rate
        scheduler = ReduceLROnPlateau(optimizer = optimizer, mode = 'min', factor = 0.1, patience = 20, min_lr=1e-12, verbose=True)

        #Defining loss function and shift it on GPU (if available)
        criterion = nn.MSELoss()

        if torch.cuda.is_available():
            criterion.cuda() 

        checkpoint = torch.load(PATH)
        model.load_state_dict(checkpoint['model_state'])

        if(torch.cuda.is_available()): # for the case of laptop with local GPU
            model = model.cuda()

        optimizer.load_state_dict(checkpoint['optimizer_state'])
        scheduler.load_state_dict(checkpoint['scheduler_state'])
        current_epoch = checkpoint['epoch'] + 1   # since we save the last epoch done, we have to start from the correct one
        prev_loss = checkpoint['loss']
        final_epoch = current_epoch + epochs # updating the number of the final epoch
    
        train_losses = pickle.load(open("./checkpoints/loss_train.txt", "rb"))  # to load the vector of train losses
        test_losses = pickle.load(open("./checkpoints/loss_test.txt", "rb"))    # to load the vector of test losses
        all_test_losses = test_losses["test_loss"]
        all_train_losses = train_losses["train_loss"]

#-----------------------------------------------------------------------------------------------------------------------------------
    
    for epoch in range((current_epoch, final_epoch)):
        
        ##### TRAINING #####

        model.train() # useless since we are not using dropout and batch normalization

        loss_train_vector = [] #vector of losses for a single epoch

        for batch_idx, (data,target) in enumerate(train_loader):
            # Moving data to the GPU if possible
            if(torch.cuda.is_available()): # for the case of laptop with local GPU
                data,target = data.cuda(), target.cuda()
            # Setting the gradient attribute of each weight to zero
            optimizer.zero_grad()
            # Computing the forward pass
            output = model(data)
            # Computing the loss
            loss = criterion(torch.flatten(output),target)
            # Computing the gradient w.r.t. model parameters
            loss.backward()
            # Adjusting the weights using SGD
            optimizer.step()
            # Saving the loss in the corresponding vector
            loss_train_vector.append(loss.item())

        loss_train = np.mean(loss_train_vector)
        # Comparing the loss of the epoch with the previous ones to check whether to change the learning rate or not
        scheduler.step(loss_train) 
        # Saving the train loss of the current epoch for later plot
        loss_epoch_train.append(loss_train)

        pickle.dump({"train_loss": loss_epoch_train}, open("./checkpoints/loss_train.txt", "wb")) # it overwrites the previous file

        ##### TEST #####

        model.eval() 

        loss_test_vector = [] #vector of losses for a single epoch

        for batch_idx, (data,target) in enumerate(test_loader):
            # Moving data to the GPU if possible
            if(torch.cuda.is_available()): # for the case of laptop with local GPU
                data,target = data.cuda(), target.cuda()
            # Using torch.no_grad() to not save the operation in the computation graph
            with torch.no_grad():
                pred = model(data)
            # Computing test loss. Since pred.require_grad = False, the following operation is not added to the computation graph
            loss = criterion(torch.flatten(pred),target).item()
            loss_test_vector.append(loss)

            correlation_plot(pred.cpu().detach().numpy(), target.cpu().detach().numpy())

        plt.savefig('./checkpoints/correlation_plot_%d.png' %(epoch+1), bbox_inches='tight') # saving correlation plot
        plt.clf() # to clear the current figure
        # Saving the test loss of the current epoch for later plot
        loss_test = np.mean(loss_test_vector)
        loss_epoch_test.append(loss_test)
    
        # Visualizing loss values against the number of epoch
        visualize_LvsN(loss_epoch_test, loss_epoch_train)
        plt.savefig('./checkpoints/LvsN_visualization_plot_%d.png' %(epoch+1), bbox_inches='tight') # saving LvsN plot
        plt.clf() # to clear the current figure

        pickle.dump({"test_loss": all_test_losses}, open("./checkpoints/loss_test.txt", "wb")) # it overwrites the previous file

        if (loss_test < prev_loss): # if our current model is better, update the best model saving the net state, loss value and R2 score
            prev_loss = loss_test
            PATH = './checkpoints/model_%d.pt' % epoch
            torch.save({'epoch': epoch,
                        'model_state': model.state_dict(),
                        'optimizer_state': optimizer.state_dict(),
                        'scheduler_state': scheduler.state_dict(),
                        'loss': prev_loss}, PATH)
        print('Epoch %d: loss=%.4f, val_loss=%.4f, R2=%.4f, val_R2=%.4f' %(epoch+1, loss_train, loss_test ))


        # saving the last model used (to be sure, we save it each epoch)
        PATH = './checkpoints/last_model.pt'
        torch.save({'epoch': epoch,
                    'model_state': model.state_dict(),
                    'optimizer_state': optimizer.state_dict(),
                    'scheduler_state': scheduler.state_dict(),
                    'loss': prev_loss}, PATH)







