from sklearn.metrics import accuracy_score, mean_squared_error
import collections
import numpy as np
import pandas as pd
class Losses(object):
    """
    Calculates prediction losses on test datasets achieved by the trained estimators. When the class is instantiated it creates a dictionary that stores the losses.

    
    :type metric: string
    :param metrics: loss metric that will be calculated.

    """

    def __init__(self, metric):

        self._losses = collections.defaultdict(list)
        self._metric = metric

    def evaluate(self, predictions, true_labels):
        """
        Calculates the loss metrics on the test sets.

        :type predictions: 2d numpy array
        :param v: Predictions of trained estimators in the form [estimator_name, [predictions]]

        :type true_labels: numpy array
        :param true_labels: true labels of test dataset.
        """
        
        for prediction in predictions:
            estimator_name = prediction[0]
            estimator_predictions = prediction[1]
            
            
            if self._metric is 'accuracy':
                loss = accuracy_score(true_labels, estimator_predictions)
                self._losses[estimator_name].append( loss )
            elif self._metric is 'mean_squared_error':
                loss = mean_squared_error(true_labels, estimator_predictions)
                self._losses[estimator_name].append(loss)   
            else:
                raise ValueError(f'metric {self._metric} is not supported.')
            
    def evaluate_per_dataset(self, 
                            predictions, 
                            true_labels, 
                            dataset_name):

        """
        Calculates the error of an estimator per dataset.
        
        Parameters
        ----------
        predictions : 2d array-like in the form [estimator name, [estimator_predictions]].
        true_labels : 1d array-like
        
        """
        estimator_name = predictions[0]
        estimator_predictions = np.array(predictions[1])
        errors = []
        for pair in zip(estimator_predictions, true_labels):
            prediction = pair[0]
            true_label = pair[1]
            if self._metric is 'mean_squared_error':
                mse = mean_squared_error([prediction], [true_label])
                errors.append(mse)
            if self._metric is 'accuracy':
                accuracy = accuracy_score([true_label], [prediction])
                errors.append(accuracy)

        std_score = np.std(errors)
        n = len(errors)
        sum_score = np.sum(errors)
        score = np.sqrt(sum_score/n)
        self._losses[dataset_name].append([estimator_name, score, std_score])

    def get_losses(self):
        """
        When the Losses class is instantiated a dictionary that holds all losses is created and appended every time the evaluate() method is run. This method returns this dictionary with the losses.

        :rtype: dictionary
        """ 
        return self._losses

    def losses_to_dataframe(self, losses):
        """
        Reformats the output of the dictionary returned by the :func:`mleap.analyze_results.losses.Losses.get_losses` to a pandas DataFrame. This method can only be applied to reformat the output produced by :func:`mleap.analyze_results.Losses.evaluate_per_dataset`.

        Parameters
        ----------

        losses: dictionary returned by the :func:`mleap.analyze_results.losses.Losses.get_losses` generated by :func:`mleap.analyze_results.losses.Losses.evaluate_per_dataset`
        """

        df = pd.DataFrame(losses)
        #unpivot the data
        df = df.melt(var_name='dts', value_name='values')
        df['classifier'] = df.apply(lambda raw: raw.values[1][0], axis=1)
        df['score'] = df.apply(lambda raw: raw.values[1][1], axis=1)
        df['std'] = df.apply(lambda raw: raw.values[1][2], axis=1)
        df = df.drop('values', axis=1)
        #create multilevel index dataframe
        dts = df['dts'].unique()
        estimators_list = df['classifier'].unique()
        score = df['score'].values
        std = df['std'].values
        
        df = df.drop('dts', axis=1)
        df=df.drop('classifier', axis=1)
        
        df.index = pd.MultiIndex.from_product([dts, estimators_list])

        return df