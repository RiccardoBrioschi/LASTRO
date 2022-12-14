" File to define model"

import torch.nn as nn
import torch.nn.functional as func
import talos
import params


# Defining neural network architecture to use Talos optimization. The results obtained doing cross validation are then used to build the neural network used in main script.
class customized_increasing_NN(nn.Module, talos.utils.TorchHistory):

    " Class to run optimization script "

    def __init__ (self,p, num_features,dtype):
        # Importing methods and attributes from Module
        super().__init__()
        # We use linear layer, we use params to define other layers
        self.dropout = nn.Dropout(p['dropout'])
        self.activation = p['activation']
        self.starting_linear = nn.Linear(num_features, p['hidden_layer_size'], dtype=dtype)
        self.__nr_layers = p['nr_layers']
        self.__hidden_layer_size = p['hidden_layer_size']
        self.ending_layer = nn.Linear((2**(self.__nr_layers-1))*(self.__hidden_layer_size), 1, dtype=dtype)
    
    def forward(self,input):

        "Function to implement the forward pass"

        out = self.dropout(self.activation(self.starting_linear(input)))
        for idx_layer in range(0,self.__nr_layers-1):
            self.linear = nn.Linear(self.__hidden_layer_size*(2**idx_layer), self.__hidden_layer_size*(2**(idx_layer+1)), dtype = params.dtype).cuda()
            out = self.dropout(self.activation(self.linear(out)))
        out = self.ending_layer(out)
        return out

# The hyperparameters of these architectures (e.g. depth, num layers, activation function, dropout rate) have been decided after optimizing the model using talos library.
# For further details, please refer to talos_optimization



class my_FNN_increasing_masking(nn.Module):

    """Class to define the architecture. The hyperparameters chosen after talos optimization are:
    {'nr_hidden_layer:4, hidden_layers_size:16, dropout_rate:0.1, lr:0.1} -> for masking
    """

    def __init__(self,num_feature, dtype):
        # Importing methods and attributes from Module
        super().__init__()
        # Generating and initializing each layer
        self.l1 = nn.Linear(num_feature,16,dtype=dtype)
        self.reLU1 = nn.ReLU()
        self.l2 = nn.Linear(16,32,dtype=dtype)
        self.reLU2 = nn.ReLU()
        self.l3 = nn.Linear(32,64,dtype=dtype)
        self.reLU3 = nn.ReLU()
        self.l4 = nn.Linear(64,128,dtype=dtype) 
        self.reLU4 = nn.ReLU()
        self.l5 = nn.Linear(128,1,dtype=dtype) 
        self.dropout = nn.Dropout(0.1)

    def forward(self,input):

        "Function to implement the forward pass"

        out = self.l1(input)
        out = self.reLU1(out)
        out = self.dropout(out)
        out = self.l2(out)
        out = self.reLU2(out)
        out = self.dropout(out)
        out = self.l3(out)
        out = self.reLU3(out)
        out = self.dropout(out)
        out = self.l4(out)
        out = self.reLU4(out)
        out = self.dropout(out)
        out = self.l5(out)
  
        return out
