import torch
from torch import nn
import numpy as np
import torch
from torch import nn
from torch.autograd import Variable
from torch.nn.functional import softmax, relu


# ------------------------------- MODEL A -------------------------------
class Part3RnnBiLSTMA(nn.Module):
    def __init__(self, dims, vocab_size, embedding_dim=50, lr=0.01, pre_trained=None, gpu=True):
        super(Part3RnnBiLSTMA, self).__init__()

        # layer sizes
        self._lstm_out_dim = dims[0]
        self._lin1_out = dims[1]
        self._out_dim = dims[-1]
        self._embedding_dim = embedding_dim

        # useful info in forward function
        if pre_trained:
            self.embeddings, embedding_dim = self._load_pre_trained(pre_trained)
        else:
            self.embeddings = nn.Embedding(vocab_size, embedding_dim)

        self._gpu = gpu
        self._lstm_layer = nn.LSTM(embedding_dim, self._lstm_out_dim, 2, batch_first=True,
                                   dropout=0.1, bidirectional=True)  # 2 layers RNN
        self._layer1 = nn.Linear(2 * self._lstm_out_dim, self._lin1_out)
        self._layer2 = nn.Linear(self._lin1_out, self._out_dim)
        # self._output_layer = nn.Linear(hidden_mlp_dim, out_dim)

        # set optimizer
        self.optimizer = self.set_optimizer(lr)

    def _get_first_h(self, batch_size=4):
        return (torch.zeros(4, batch_size, self._lstm_out_dim).cuda(), torch.zeros(4, batch_size, self._lstm_out_dim).cuda()) if \
                   self._gpu else (torch.zeros(4, batch_size, self._lstm_out_dim), torch.zeros(4, batch_size, self._lstm_out_dim))

    @staticmethod
    def _load_pre_trained(weights_matrix, non_trainable=False):
        weights_matrix = torch.Tensor(np.loadtxt(weights_matrix))
        num_embeddings, embedding_dim = weights_matrix.size()
        emb_layer = nn.Embedding(num_embeddings, embedding_dim)
        emb_layer.load_state_dict({'weight': weights_matrix})
        if non_trainable:
            emb_layer.weight.requires_grad = False
        return emb_layer, embedding_dim

    # init optimizer with RMS_prop
    def set_optimizer(self, lr):
        return torch.optim.Adam(self.parameters(), lr=lr)

    def forward(self, input_x):
        # break input to variables
        x, x_pref, x_suf = input_x
        x = Variable(x.cuda()) if self._gpu else Variable(x)

        x = self.embeddings(x)
        # x = torch.tanh(x)
        output_seq, _ = self._lstm_layer(x, self._get_first_h(batch_size=x.shape[0]))
        x = output_seq.squeeze(dim=1)
        x = self._layer1(x)
        x = torch.tanh(x)
        x = self._layer2(x)
        x = softmax(x, dim=1)
        return x


# ------------------------------- MODEL B -------------------------------
class Part3RnnBiLSTMB(nn.Module):
    def __init__(self, dims, vocab_size=128, embedding_dim=10, lr=0.01, gpu=True):
        super(Part3RnnBiLSTMB, self).__init__()
        self._gpu = gpu
        # layer sizes
        self._lstm_embed_out_dim = dims[0]
        self._lstm_out_dim = dims[1]
        self._out_dim = dims[-1]

        self.embeddings = nn.Embedding(vocab_size, embedding_dim)
        self._lstm_embed_layer = nn.LSTM(embedding_dim, self._lstm_embed_out_dim, 2, dropout=0.5)  # 2 layers RNN
        self._lstm_layer = nn.LSTM(self._lstm_embed_out_dim, self._lstm_out_dim, 2, batch_first=True
                                   , dropout=0.1, bidirectional=True)  # 2 layers RNN
        self._layer1 = nn.Linear(2 * self._lstm_out_dim, self._out_dim)
        # self._output_layer = nn.Linear(hidden_mlp_dim, out_dim)

        # set optimizer
        self.optimizer = self.set_optimizer(lr)

    # init optimizer with RMS_prop
    def set_optimizer(self, lr):
        return torch.optim.Adam(self.parameters(), lr=lr)

    def forward(self, input_x):
        x = self.embeddings(Variable(input_x.cuda())).transpose(1, 2)
        out_lstm1 = []
        for i in x:
            out_lstm1.append(self._lstm_embed_layer(i)[0].squeeze(dim=0)[-1])
        # for w in input_x:
        #     w = self.embeddings(Variable(w.cuda())) if self._gpu else self.embeddings(Variable(w.cuda()))
        #     w, _ = self._lstm_embed_layer(w.squeeze(dim=0).unsqueeze(dim=1))
        #     x.append(w.squeeze(dim=0)[-1])
        # x = [w if len(w.shape) == 2 else w.unsqueeze(dim=0) for w in x]
        x = torch.stack(out_lstm1)
        # x = torch.tanh(x)
        output_seq, _ = self._lstm_layer(x)
        x = output_seq.squeeze(dim=1)

        x = self._layer1(x)
        x = softmax(x, dim=1)
        return x


# ------------------------------- MODEL C -------------------------------
class Part3RnnBiLSTMC(nn.Module):
    def __init__(self, dims, vocab_size, pref_size, suf_size, embedding_dim=50, lr=0.01, pre_trained=None, gpu=True):
        super(Part3RnnBiLSTMC, self).__init__()
        self._gpu = True
        # layer sizes
        self._lstm_out_dim = dims[0]
        self._lin1_out = dims[1]
        self._out_dim = dims[-1]

        # useful info in forward function
        if pre_trained:
            self.embeddings, embedding_dim = self._load_pre_trained(pre_trained)
        else:
            self.embeddings = nn.Embedding(vocab_size, embedding_dim)

        self.pref_embeddings = nn.Embedding(pref_size, embedding_dim)
        self.pref_embeddings.load_state_dict({'weight': torch.zeros(pref_size, embedding_dim)})
        self.suf_embeddings = nn.Embedding(suf_size, embedding_dim)
        self.suf_embeddings.load_state_dict({'weight': torch.zeros(suf_size, embedding_dim)})

        self._lstm_layer = nn.LSTM(embedding_dim, self._lstm_out_dim, 2, batch_first=True
                                   , dropout=0.1, bidirectional=True)  # 2 layers RNN
        self._layer1 = nn.Linear(2 * self._lstm_out_dim, self._lin1_out)
        self._layer2 = nn.Linear(self._lin1_out, self._out_dim)

        # set optimizer
        self.optimizer = self.set_optimizer(lr)

    @staticmethod
    def _load_pre_trained(weights_matrix, non_trainable=False):
        weights_matrix = torch.Tensor(np.loadtxt(weights_matrix))
        num_embeddings, embedding_dim = weights_matrix.size()
        emb_layer = nn.Embedding(num_embeddings, embedding_dim)
        emb_layer.load_state_dict({'weight': weights_matrix})
        if non_trainable:
            emb_layer.weight.requires_grad = False
        return emb_layer, embedding_dim

    # init optimizer with RMS_prop
    def set_optimizer(self, lr):
        return torch.optim.Adam(self.parameters(), lr=lr)

    def _get_first_h(self, batch_size=4):
        return (torch.zeros(4, batch_size, self._lstm_out_dim).cuda(), torch.zeros(4, batch_size, self._lstm_out_dim).cuda()) if \
                   self._gpu else (torch.zeros(4, batch_size, self._lstm_out_dim), torch.zeros(4, batch_size, self._lstm_out_dim))

    def forward(self, input_x):
        # break input to variables
        x, x_pref, x_suf = input_x
        x = Variable(x.cuda()) if self._gpu else Variable(x)
        x_pref = Variable(x_pref.cuda()) if self._gpu else Variable(x_pref)
        x_suf = Variable(x_suf.cuda()) if self._gpu else Variable(x_suf)

        x = (self.embeddings(x) + self.pref_embeddings(x_pref) + self.suf_embeddings(x_suf))
        # x = torch.tanh(x)
        output_seq, _ = self._lstm_layer(x, self._get_first_h(batch_size=x.shape[0]))
        x = output_seq.squeeze(dim=1)
        x = self._layer1(x)
        x = torch.tanh(x)
        x = self._layer2(x)
        x = softmax(x, dim=1)
        return x


# ------------------------------- MODEL D -------------------------------
class Part3RnnBiLSTMD(nn.Module):
    def __init__(self, dims, vocab_size, pref_size, suf_size, embedding_dim=50, lr=0.01, pre_trained=None, gpu=True):
        super(Part3RnnBiLSTMD, self).__init__()
        self._gpu = gpu
        # layer sizes
        self._lstm_out_dim = dims[0]
        self._lin1_out = dims[1]
        self._out_dim = dims[-1]

        # useful info in forward function
        if pre_trained:
            self.embeddings, embedding_dim = self._load_pre_trained(pre_trained)
        else:
            self.embeddings = nn.Embedding(vocab_size, embedding_dim)

        self.pref_embeddings = nn.Embedding(pref_size, embedding_dim)
        self.pref_embeddings.load_state_dict({'weight': torch.zeros(pref_size, embedding_dim)})
        self.suf_embeddings = nn.Embedding(suf_size, embedding_dim)
        self.suf_embeddings.load_state_dict({'weight': torch.zeros(suf_size, embedding_dim)})

        self._lstm_layer = nn.LSTM(3 * embedding_dim, self._lstm_out_dim, 2, batch_first=True
                                   , dropout=0.1, bidirectional=True)  # 2 layers RNN
        self._layer1 = nn.Linear(2 * self._lstm_out_dim, self._lin1_out)
        self._layer2 = nn.Linear(self._lin1_out, self._out_dim)

        # set optimizer
        self.optimizer = self.set_optimizer(lr)

    @staticmethod
    def _load_pre_trained(weights_matrix, non_trainable=False):
        weights_matrix = torch.Tensor(np.loadtxt(weights_matrix))
        num_embeddings, embedding_dim = weights_matrix.size()
        emb_layer = nn.Embedding(num_embeddings, embedding_dim)
        emb_layer.load_state_dict({'weight': weights_matrix})
        if non_trainable:
            emb_layer.weight.requires_grad = False
        return emb_layer, embedding_dim

    # init optimizer with RMS_prop
    def set_optimizer(self, lr):
        return torch.optim.Adam(self.parameters(), lr=lr)

    def _get_first_h(self, batch_size=4):
        return (torch.zeros(4, batch_size, self._lstm_out_dim).cuda(), torch.zeros(4, batch_size, self._lstm_out_dim).cuda()) if \
                   self._gpu else (torch.zeros(4, batch_size, self._lstm_out_dim), torch.zeros(4, batch_size, self._lstm_out_dim))

    def forward(self, input_x):
        # break input to variables
        x, x_pref, x_suf = input_x
        x = Variable(x.cuda()) if self._gpu else Variable(x)
        x_pref = Variable(x_pref.cuda()) if self._gpu else Variable(x_pref)
        x_suf = Variable(x_suf.cuda()) if self._gpu else Variable(x_suf)

        x = torch.cat([self.embeddings(x), self.pref_embeddings(x_pref), self.suf_embeddings(x_suf)], dim=2)
        # x = torch.tanh(x)
        output_seq, _ = self._lstm_layer(x, self._get_first_h(batch_size=x.shape[0]))
        x = output_seq.squeeze(dim=1)
        x = self._layer1(x)
        x = torch.tanh(x)
        x = self._layer2(x)
        x = softmax(x, dim=1)
        return x


if __name__ == '__main__':
    pass
