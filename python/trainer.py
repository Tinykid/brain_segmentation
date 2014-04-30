__author__ = 'adeb'

import sys
import os
import time

import numpy

import theano
import theano.tensor as T


class Trainer():
    def __init__(self, config, net, ds):
        print '... configure training'

        self.batch_size = config.getint('training', 'batch_size')
        self.learning_rate = config.getfloat('training', 'learning_rate')
        self.n_epochs = config.getint('training', 'n_epochs')

        self.nn = net
        self.ds = ds

        self.n_train_batches = ds.n_train / self.batch_size
        self.n_valid_batches = ds.n_valid / self.batch_size
        self.n_test_batches = ds.n_test / self.batch_size

        self.idx_batch = T.lscalar()
        self.x = net.x  # Minibatch input matrix
        self.y_true = T.matrix('y_true')  # True output of a minibatch

        # Cost the trainer is going to minimize
        self.cost = net.cost(self.y_true)

        # Compute gradients
        self.params = net.params
        self.grads = T.grad(self.cost, self.params)

        updates = []
        for param_i, grad_i in zip(self.params, self.grads):
            updates.append((param_i, param_i - self.learning_rate * grad_i))

        id1 = self.idx_batch * self.batch_size
        id2 = (self.idx_batch + 1) * self.batch_size
        self.test_model = theano.function(
            inputs=[self.idx_batch],
            outputs=net.errors(self.y_true),
            givens={self.x: ds.test_x[id1:id2], self.y_true: ds.test_y[id1:id2]})

        self.validate_model = theano.function(
            inputs=[self.idx_batch],
            outputs=net.errors(self.y_true),
            givens={self.x: ds.valid_x[id1:id2], self.y_true: ds.valid_y[id1:id2]})

        self.train_model = theano.function(
            inputs=[self.idx_batch],
            outputs=self.cost,
            updates=updates,
            givens={self.x: ds.train_x[id1:id2], self.y_true: ds.train_y[id1:id2]})

    def train(self):
        print '... train the network'

        start_time = time.clock()

        # early-stopping parameters
        patience = 10000  # look as this many examples regardless
        patience_increase = 1000  # wait this much longer when a new best is found
        improvement_threshold = 0.995  # a relative improvement of this much is considered significant
        validation_frequency = min(self.n_train_batches, patience / 2)
                                      # go through this many
                                      # minibatche before checking the network
                                      # on the validation set; in this case we
                                      # check every epoch

        best_validation_loss = numpy.inf
        best_iter = 0
        test_score = 0.

        epoch = 0
        early_stopping = False
        id_mini_batch = 0

        while (epoch < self.n_epochs) and (not early_stopping):
            epoch += 1
            for minibatch_index in xrange(self.n_train_batches):

                id_mini_batch += 1

                if id_mini_batch % 100 == 0:
                    print('epoch %i, minibatch %i/%i' % (epoch, minibatch_index + 1, self.n_train_batches))

                self.train_model(minibatch_index)

                if patience <= id_mini_batch:
                    early_stopping = True
                    break

                if (id_mini_batch + 1) % validation_frequency > 0:
                    continue

                # compute validation error
                validation_losses = [self.validate_model(i) for i in xrange(self.n_valid_batches)]
                this_validation_loss = numpy.mean(validation_losses)
                print('epoch %i, minibatch %i/%i, validation error %f' %
                      (epoch, minibatch_index + 1, self.n_train_batches, this_validation_loss))

                # if we got the best validation score until now
                if this_validation_loss >= best_validation_loss:
                    continue

                #improve patience if loss improvement is good enough
                if this_validation_loss < best_validation_loss * improvement_threshold:
                    patience += patience_increase

                # save best validation score and iteration number
                best_validation_loss = this_validation_loss
                best_iter = id_mini_batch

                # test it on the test set
                test_losses = [self.test_model(i) for i in xrange(self.n_test_batches)]
                test_score = numpy.mean(test_losses)
                print('     epoch %i, minibatch %i/%i, test error of best model %f' %
                      (epoch, minibatch_index + 1, self.n_train_batches, test_score))

        end_time = time.clock()
        print('Training complete.')
        print('Best validation score of %f obtained at iteration %i with test performance %f' %
              (best_validation_loss, best_iter + 1, test_score))
        print >> sys.stderr, ('The code for file ran for %.2fm' % ((end_time - start_time) / 60.))
