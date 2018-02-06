import fire
import os
import statistics

from data.objects.list import DATASETS, get_dataset_names
from data.objects.ProcessedData import ProcessedData
from algorithms.list import ALGORITHMS
from metrics.list import get_metrics

NUM_TRIALS_DEFAULT = 10

def get_algorithm_names():
    result = [algorithm.get_name() for algorithm in ALGORITHMS]
    print("Available algorithms:")
    for a in result:
        print("  %s" % a)
    return result

def run(num_trials = NUM_TRIALS_DEFAULT, dataset = get_dataset_names(),
        algorithm = get_algorithm_names()):
    algorithms_to_run = algorithm

    print("Datasets: '%s'" % dataset)
    for dataset_obj in DATASETS:
        if not dataset_obj.get_dataset_name() in dataset:
            continue

        print("\nEvaluating dataset:" + dataset_obj.get_dataset_name())

        processed_dataset = ProcessedData(dataset_obj)
        train_test_splits = processed_dataset.create_train_test_splits(num_trials)

        all_sensitive_attributes = dataset_obj.get_sensitive_attributes_with_joint()
        for sensitive in all_sensitive_attributes:

            print("Sensitive attribute:" + sensitive)

            detailed_files = dict((k, create_detailed_file(
                                          dataset_obj.get_results_filename(sensitive, k),
                                          dataset_obj,
                                          processed_dataset.get_sensitive_values(k), k))
                for k in train_test_splits.keys())

            for algorithm in ALGORITHMS:
                if not algorithm.get_name() in algorithms_to_run:
                    continue

                print("    Algorithm: %s" % algorithm.get_name())
                print("       supported types: %s" % algorithm.get_supported_data_types())
                for i in range(0, num_trials):
                    for supported_tag in algorithm.get_supported_data_types():
                        train, test = train_test_splits[supported_tag][i]
                        params, results = run_eval_alg(algorithm, train, test, dataset_obj,
                                                       processed_dataset, all_sensitive_attributes,
                                                       sensitive, supported_tag)
                        write_alg_results(detailed_files[supported_tag],
                                          algorithm.get_name(), params, results)

            print("Results written to:")
            for supported_tag in algorithm.get_supported_data_types():
                print("    " + dataset_obj.get_results_filename(sensitive, supported_tag))

            for detailed_file in detailed_files.values():
                detailed_file.close()

def write_alg_results(file_handle, alg_name, params, results_list):
    line = alg_name + ','
    line += str(params) + ','  ## TODO: do something more parseable with multiple params here
    line += ','.join(str(x) for x in results_list) + '\n'
    file_handle.write(line)
    # Make sure the file is written to disk line-by-line:
    file_handle.flush()
    os.fsync(file_handle.fileno())

def run_eval_alg(algorithm, train, test, dataset, processed_data, all_sensitive_attributes,
                 single_sensitive, tag):
    """
    Runs the algorithm and gets the resulting metric evaluations.
    """
    privileged_vals = dataset.get_privileged_class_names_with_joint(tag)
    positive_val = dataset.get_positive_class_val(tag)

    # get the actual classifications and sensitive attributes
    actual = test[dataset.get_class_attribute()].values.tolist()
    sensitive = test[single_sensitive].values.tolist()

    predicted, params =  run_alg(algorithm, train, test, dataset, all_sensitive_attributes,
                                 single_sensitive, privileged_vals, positive_val)

    # make dictionary mapping sensitive names to sensitive attr test data lists
    dict_sensitive_lists = {}
    for sens in all_sensitive_attributes:
        dict_sensitive_lists[sens] = test[sens].values.tolist()

    sensitive_dict = processed_data.get_sensitive_values(tag)
    one_run_results = []
    for metric in get_metrics(dataset, sensitive_dict, tag):
        result = metric.calc(actual, predicted, dict_sensitive_lists, single_sensitive,
                             privileged_vals, positive_val)
        one_run_results.append(result)

    return params, one_run_results

def run_alg(algorithm, train, test, dataset, all_sensitive_attributes, single_sensitive,
            privileged_vals, positive_val):
    class_attr = dataset.get_class_attribute()
    params = algorithm.get_default_params()

    # Note: the training and test set here still include the sensitive attributes because
    # some fairness aware algorithms may need those in the dataset.  They should be removed
    # before any model training is done.
    predictions = algorithm.run(train, test, class_attr, positive_val, all_sensitive_attributes,
                                single_sensitive, privileged_vals, params)

    return predictions, params

def get_metrics_list(dataset, sensitive_dict, tag):
    return [metric.get_name() for metric in get_metrics(dataset, sensitive_dict, tag)]

def get_detailed_metrics_header(dataset, sensitive_dict, tag):
    return ','.join(['algorithm', 'params'] + get_metrics_list(dataset, sensitive_dict, tag))

def get_dict_sensitive_vals(dict_sensitive_lists):
    """
    Takes a dictionary mapping sensitive attributes to lists in the test data and returns a
    dictionary mapping sensitive attributes to lists containing each sensitive value only once.
    """
    newdict = {}
    for sens in dict_sensitive_lists:
         sensitive = dict_sensitive_lists[sens]
         newdict[sens] = list(set(sensitive))
    return newdict

def create_detailed_file(filename, dataset, sensitive_dict, tag):
    f = open(filename, 'w')
    f.write(get_detailed_metrics_header(dataset, sensitive_dict, tag) + '\n')
    return f

def main():
    fire.Fire(run)

if __name__ == '__main__':
    main()
