from metrics.Average import Average
from metrics.FilterSensitive import FilterSensitive
from metrics.Metric import Metric
from metrics.Ratio import Ratio

class SensitiveMetric(Metric):
     """
     Takes the given metric and creates a version of it that is conditioned on a sensitive
     attribute.
     """
     def __init__(self, metric_class):
          Metric.__init__(self)
          self.metric = metric_class
          self.name = self.metric().get_name()   # to be modified as this metric is expanded

     def calc(self, actual, predicted, dict_of_sensitive_lists, single_sensitive_name,
              unprotected_vals, positive_pred):
          sfilter = FilterSensitive(self.metric())
          sfilter.set_sensitive_to_filter(self.sensitive_attr, self.sensitive_val)
          return sfilter.calc(actual, predicted, dict_of_sensitive_lists, single_sensitive_name,
                              unprotected_vals, positive_pred)

     def expand_per_dataset(self, dataset, sensitive_dict, tag):
          objects_list = []
          for sensitive in dataset.get_sensitive_attributes_with_joint():
               objects_list += self.make_metric_objects(sensitive, sensitive_dict, dataset, tag)
          return objects_list

     def make_metric_objects(self, sensitive_name, sensitive_values, dataset, tag):
          privileged_val = self.get_privileged_for_attr(sensitive_name, dataset, tag)

          objs_list = []
          ratios_list = []
          for val in sensitive_values[sensitive_name]:
              # adding sensitive variants of the given metric to the objects list
              objs_list.append(self.make_sensitive_obj(sensitive_name, val))

              # adding ratio of sensitive variants of the given metric to the ratios list
              if val != privileged_val:
                  ratios_list.append(self.make_ratio_obj(sensitive_name, val, privileged_val))
          avg = Average(objs_list, sensitive_name + '-' + self.metric().get_name())
          ratio_avg = Average(ratios_list,
                              sensitive_name + '-' + self.metric().get_name() + 'Ratio')
          return objs_list + [avg] + ratios_list + [ratio_avg]

     def make_sensitive_obj(self, sensitive_attr, sensitive_val):
          obj = self.__class__(self.metric)
          obj.set_sensitive_to_filter(sensitive_attr, sensitive_val)
          return obj

     def make_ratio_obj(self, sensitive_attr, sensitive_val, privileged):
          privileged_metric = self.make_sensitive_obj(sensitive_attr, privileged)
          unprivileged_metric = self.make_sensitive_obj(sensitive_attr, sensitive_val)
          return Ratio(unprivileged_metric, privileged_metric)

     def get_privileged_for_attr(self, sensitive_attr, dataset, tag):
          sensitive_attributes = dataset.get_sensitive_attributes_with_joint()
          privileged_vals = dataset.get_privileged_class_names_with_joint(tag)
          for sens, priv in zip(sensitive_attributes, privileged_vals):
               if sens == sensitive_attr:
                    return priv
          print("ERROR: couldn't find privileged value for attribute:" + str(sensitive_attr))
          return None

     def set_sensitive_to_filter(self, sensitive_name, sensitive_val):
          """
          Set the attribute and value to filter, i.e., to calculate this metric for.
          """
          self.sensitive_attr = sensitive_name
          self.sensitive_val = sensitive_val
          self.name = str(sensitive_val) + "-" + self.name

