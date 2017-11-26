import os
import pickle
from .static_variables import EXPERIMENTS_TRAINED_MODELS_DIR, EXPERIMENTS_PREDICTIONS_DIR, EXPERIMENTS_MODEL_ACCURACY_DIR
from .static_variables import PICKLE_EXTENTION
from .static_variables import FLAG_ML_MODEL,FLAG_PREDICTIONS
from .static_variables import REFORMATTED_DATASETS_DIR
from .static_variables import RUNTIMES_GROUP
from .static_variables import RESULTS_DIR
import h5py
import tables
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split


class FilesIO:

    def __init__(self, hdf5_filename):
        self.hdf5_filename = hdf5_filename

    
    def check_file_exists(self, dataset_name, file_type):
        filename = ''
        if file_type == FLAG_ML_MODEL:
            filename = EXPERIMENTS_TRAINED_MODELS_DIR + dataset_name + PICKLE_EXTENTION
        elif file_type == FLAG_PREDICTIONS:
            filename = EXPERIMENTS_PREDICTIONS_DIR + dataset_name + PICKLE_EXTENTION
        else:
            raise ValueError('Please specify supported file type')
 
        file_exists = os.path.isfile(filename)
        if file_exists:
            return pickle.load(open(filename, 'rb'))
        else:
            return False
    
    def check_prediction_exists(self, dataset_name):
        f = h5py.File(self.hdf5_filename)
        is_present = EXPERIMENTS_PREDICTIONS_DIR +  dataset_name in f
        f.close()
        return is_present
    

    def load_predictions_for_dataset(self, dataset_name):
        f = h5py.File(self.hdf5_filename)
        predictions = f['/'+EXPERIMENTS_PREDICTIONS_DIR + dataset_name]
        
        predictions_for_dataset = []
        for strategy in list(predictions):
            predictions_for_dataset.append([strategy, predictions[strategy][...]])
        return predictions_for_dataset

        
    def save_trained_models_to_disk(self, trained_models, dataset_name):
        with open(EXPERIMENTS_TRAINED_MODELS_DIR + dataset_name + PICKLE_EXTENTION,'wb') as f:
            pickle.dump(trained_models,f)
    
    def save_predictions_to_db(self, predictions, dataset_name):
        f = h5py.File(self.hdf5_filename)
        for prediction in predictions:
            strategy_name = prediction[0]
            strategy_predictions = np.array(prediction[1])
            save_path = EXPERIMENTS_PREDICTIONS_DIR + dataset_name  + strategy_name
            try:
                f[save_path] = strategy_predictions
            except:
                raise ValueError('Save path already exists')
        f.close()

    def save_prediction_accuracies_to_db(self, model_accuracies):
        for model in model_accuracies:
            model_name = model[0]
            model_accuracy = np.array([model[1]])
            
            #create group if necessary
            f =  h5py.File(self.hdf5_filename, 'a')
            if not '/' + EXPERIMENTS_MODEL_ACCURACY_DIR in f:
                f.create_group('/' + EXPERIMENTS_MODEL_ACCURACY_DIR)
            f.close()            
            #create array with accuracies or append it
            f = tables.open_file(self.hdf5_filename, 'a')
            if not  '/' + EXPERIMENTS_MODEL_ACCURACY_DIR + model_name in f: 
                f.create_earray('/' +EXPERIMENTS_MODEL_ACCURACY_DIR, name=model_name, obj=model_accuracy)
            else:
                mdl_acc = getattr(f.root.experiments.trained_models_accuracies, model_name)
                mdl_acc.append(model_accuracy)
            f.close()
            
    def get_prediction_accuracies_per_strategy(self):
        pred_accuracies = {}
        f = h5py.File(self.hdf5_filename)
        strategies = f[EXPERIMENTS_MODEL_ACCURACY_DIR]
        for strategy in strategies:
            pred_accuracies[strategy] = strategies[strategy][...]
        return pred_accuracies
    
    def save_ml_strategy_timestamps(self, timestamps_df, dataset_name):
        store = pd.HDFStore(self.hdf5_filename)
        store[RUNTIMES_GROUP + '/' + dataset_name ] = timestamps_df
        store.close()
    
    def save_stat_test_result(self, stat_test_dataset, values):
        store = pd.HDFStore(self.hdf5_filename)
        store['/' + RESULTS_DIR + stat_test_dataset] = values
        store.close()
    
    def list_datasets(self, hdf5_group):
        '''
        TODO this needs to be linked. Currently copied from 
        create_dataset_splitstrategy
        '''
        datasets = []
        f = h5py.File(self.hdf5_filename)
        for i in f[hdf5_group].items():
            datasets.append(i[0])
        f.close()
        return datasets
    
    def load_dataset(self, dataset_name):
        store = pd.HDFStore(self.hdf5_filename)
        dataset = store[dataset_name]
        metadata = store.get_storer(dataset_name).attrs.metadata
        store.close()
        return dataset, metadata
    
    def save_datasets(self, datasets, datasets_save_paths, dts_metadata, verbose = False):
        '''
        saves datasets in HDF5 database. 
        dataset_names must contain full path
        '''
        store = pd.HDFStore(self.hdf5_filename)
        for dts in zip(datasets, dts_metadata, datasets_save_paths):
            
            dts_name = dts[1]['dataset_name']     
            save_loc = dts[2]    
            store[save_loc] = dts[0]
            store.get_storer(save_loc).attrs.metadata = dts[1]
            if verbose is True:
                print(f'Saved: {dts_name} to HDF5 database')
        store.close()
    
    def split_dataset(self, dataset_path, test_size=0.33):
        #load
        dataset, metadata = self.load_dataset(dataset_path)
        class_name = metadata['class_name']
        dataset_name = metadata['dataset_name']
        #split
        y = dataset[class_name]
        X = dataset.loc[:, dataset.columns != class_name]
        X_train, X_test, y_train, y_test = train_test_split(
                X, y, test_size=test_size, random_state=42)
        #reformat y_train and y_test
        return (X_train, X_test, y_train,  
                y_test)
        
    def split_and_save(self, dataset_paths, save_loc, test_size = None):
        for dts in dataset_paths:
            if test_size is None:
                test_size = 0.33
            X_train, X_test, y_train, y_test = self.split_dataset(
                    dataset_path=dts, test_size=0.33)
            #load metadata
            _, metadata = self.load_dataset(dts)
            class_name = metadata['class_name']
            dataset_name = metadata['dataset_name']
            #save
            save_dataset_paths = [
                save_loc + '/' + dataset_name + '/X_train',
                save_loc + '/' + dataset_name + '/X_test',
                save_loc + '/' + dataset_name + '/y_train',
                save_loc + '/' + dataset_name + '/y_test'
            ]
            meta = [{'dataset_name': dataset_name}]*4
            self.save_datasets(datasets=[X_train, X_test, y_train, y_test], 
                            dataset_names = save_dataset_paths, 
                            dts_metadata = meta, 
                            verbose=None)