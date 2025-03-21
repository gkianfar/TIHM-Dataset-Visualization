import pandas as pd
import matplotlib.pyplot as plt
import numpy as np
import random
import seaborn as sns
from matplotlib import cm
import matplotlib.patches as mpatches
from collections.abc import Iterable
from sklearn.preprocessing import StandardScaler
import os
import warnings
warnings.filterwarnings('ignore')

## Set colour palette
ibm_colorblind = ['#648FFF', '#FE6100', '#DC267F', '#785EF0', '#FFB000','#48A9A6']
sns.set_palette(ibm_colorblind)


def correct_col_type(df,col):
    raw_type = str(type(df[col].dtype)).split('.')[-1].split('\'')[0].lower()
    #print(col,raw_type)
    if 'object' in raw_type:
        if 'date' in col or 'timestamp' in col or 'datetime' in col:
            return pd.to_datetime(df[col])
        else:
            return df[col].astype('category')
    else:
        return df[col]


def gen_date_col(df, tcol):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df[tcol].dt.date
    return df



def gen_date_col(df, tcol):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df['date'] = df[tcol].dt.date
    return df


def load_datasets(DPATH):

    ### Labels
    f = 'Labels.csv'
    fpth = os.path.join(DPATH,f)
    labels_df = pd.read_csv(fpth)
    for col in labels_df.columns:
        labels_df[col] = correct_col_type(labels_df,col)
    if 'date' in labels_df.columns:
        labels_df = labels_df.rename(columns={'date':'timestamp'})
        labels_df['timestamp'] = pd.to_datetime(labels_df['timestamp'])
        labels_df['date'] = labels_df['timestamp'].dt.date
        labels_df['time'] = labels_df['timestamp'].dt.time

    if 'type' in labels_df.columns:
        labels_df = labels_df.rename(columns={'type':'label'})

    ### Activity
    f = 'Activity.csv'
    fpth = os.path.join(DPATH,f)
    df = pd.read_csv(fpth)
    for col in df.columns:
        df[col] = correct_col_type(df,col)
    if 'date' in df.columns:
        activity_df = df.rename(columns={'date':'timestamp'})
        activity_df['timestamp'] = pd.to_datetime(activity_df['timestamp'])
        activity_df['date'] = activity_df['timestamp'].dt.date
        activity_df['time'] = activity_df['timestamp'].dt.time


    ### Physiology
    f = 'Physiology.csv'
    fpth = os.path.join(DPATH,f)
    df = pd.read_csv(fpth)
    for col in df.columns:
        df[col] = correct_col_type(df,col)
    if 'date' in df.columns:
        physiology_df = df.rename(columns={'date':'timestamp'})
        physiology_df['timestamp'] = pd.to_datetime(physiology_df['timestamp'])
        physiology_df['date'] = physiology_df['timestamp'].dt.date
        physiology_df['time'] = physiology_df['timestamp'].dt.time

    # Sleep
    f = 'Sleep.csv'
    fpth = os.path.join(DPATH,f)
    df = pd.read_csv(fpth)
    for col in df.columns:
        df[col] = correct_col_type(df,col)
    if 'date' in df.columns:
        sleep_df = df.rename(columns={'date':'timestamp'})
        sleep_df['timestamp'] = pd.to_datetime(sleep_df['timestamp'])
        sleep_df['date'] = sleep_df['timestamp'].dt.date
        sleep_df['time'] = sleep_df['timestamp'].dt.time

    # Demographics dataset
    f = 'Demographics.csv'
    fpth = os.path.join(DPATH,f)
    demographics_df = pd.read_csv(fpth)
    for col in demographics_df.columns:
        demographics_df[col] = correct_col_type(demographics_df,col)

    return activity_df, physiology_df, sleep_df, labels_df, demographics_df



def get_impossible_count(activity_df,transition_matrix,threshold,occurence_threshold):
  patients = activity_df['patient_id'].unique()

  impossible_activity_count = {}

  for p in patients:

      impossible_activity_count[p] = []

      patient_matrix = transition_matrix[p]  # Extract patient's transition matrix
      indices = np.where((patient_matrix < threshold))  # Find indices

      patient_impossible_transitions = list(zip(*indices))
      days = activity_df['date'][activity_df['patient_id'] == p].unique()
      days = np.sort(days)

      for i, d in enumerate(days):
          counter = 0
          df = activity_df[(activity_df['patient_id'] == p) & (activity_df['date'] == d)]
          sequence = df['location_name'].tolist()
          timestamp = df['timestamp'].tolist()
          if not sequence:
              continue

          for s, t in zip(sequence[1:], timestamp[1:]):

              init_state = s
              init_time = t
              if (init_state,s) in patient_impossible_transitions:
                counter+=1
          if counter>occurence_threshold:
            impossible_activity_count[p].append((d,counter))
      if not impossible_activity_count[p]:
        del impossible_activity_count[p]
  return impossible_activity_count

def get_transition_matrix(activity_df):
    patients = activity_df['patient_id'].unique()
    states = activity_df['location_name'].unique().tolist()
    n_state = len(states)
    transition_matrix = {}

    state_map = dict(zip(states, range(n_state)))
    state_map_reverse = {v:k for k, v in state_map.items()}

    activity_df['location_name'] = activity_df['location_name'].copy().map(state_map)



    for p in patients:
        transition_matrix[p] = np.zeros((n_state, n_state))
        days = activity_df['date'][activity_df['patient_id'] == p].unique()
        days = np.sort(days)
        flag = True

        for i, d in enumerate(days):
            df = activity_df[(activity_df['patient_id'] == p) & (activity_df['date'] == d)]
            sequence = df['location_name'].tolist()
            timestamp = df['timestamp'].tolist()
            if not sequence:
                continue

            if flag:
                init_state = sequence[0]
                init_time = timestamp[0]

            for s, t in zip(sequence[1:], timestamp[1:]):

                transition_matrix[p][init_state][s] += 1
                init_state = s
                init_time = t


            if i != len(days) - 1:
                if (days[i+1] - d).days == 1:
                    flag = False
                else:
                    flag = True

    for p in patients:
      #transition_matrix[p] = np.minimum(transition_matrix[p],transition_matrix[p].T)
      transition_matrix[p] = (transition_matrix[p] + transition_matrix[p].T) // 2
      sum_all_transitions = np.sum(transition_matrix[p])
      transition_matrix[p] = transition_matrix[p]/sum_all_transitions
    
    return transition_matrix, state_map_reverse


class AGITATION_DATASET():
  def __init__(self,dataset, location_names, physiology_names):
    num_samples = len(dataset)
    self.patient_id = [dataset[i][0] for i in range(num_samples) ]
    self.start_time = [dataset[i][1] for i in range(num_samples) ]
    self.end_time = [dataset[i][2] for i in range(num_samples) ]
    self.activity = [dataset[i][3] for i in range(num_samples) ]
    self.non_agitation = [dataset[i][4] for i in range(num_samples) ]
    self.agitation_params = [dataset[i][5] for i in range(num_samples) ]
    self.age = [dataset[i][6] for i in range(num_samples) ]
    self.gender = [dataset[i][7] for i in range(num_samples) ]
    self.week_day = [dataset[i][8] for i in range(num_samples) ]

    # Initiate the dataframe with basic informations
    self.init_df()
    self.location_names = location_names
    self.location_columns = []
    self.location_columns.extend(self.location_names)
    relative_cols = []
    mean_cols = []
    std_cols = []
    for location in self.location_names:
      relative_cols.append(location+'_count_relative')
      mean_cols.append('normal_'+location+'_count_mean')
      std_cols.append('normal_'+location+'_count_std')
    self.location_columns.extend(relative_cols)
    self.location_columns.extend(mean_cols)
    self.location_columns.extend(std_cols)
    self.physiology_names = physiology_names

  def __len__(self):
    return len(self.patient_id)
  def init_df(self):
    self.feature_df = pd.DataFrame(np.column_stack((self.patient_id,
                      self.start_time, self.end_time, self.week_day, self.age, self.gender)),
                       columns=['patient_id', 'start_time', 'end_time', 'week_day','age', 'gender'])
    
    print(f'df shape {self.feature_df.shape}')
  def activity_change(self, inplace = True):

    print('Activity change function')
    activity_change = []
    print(f'p len:{self.__len__()}')
    for index in range(self.__len__()):
      dummy = self.activity[index]
      dummy = np.array(dummy)
      if len(dummy)>0:  
        result = np.concatenate([[np.NaN], dummy[1:] != dummy[:-1]])
        changed = np.nansum(result)
      else:
        changed = 0

      normal_activity_changes = []
      count_sample = 0
      normal_activity_samples = len(self.non_agitation[index])
      
      print(f"non_agit: {len(self.non_agitation[index])}")
      for arr in self.non_agitation[index]:
        arr = np.array(arr)
        if len(arr)>0:          
          result = arr[1:] != arr[:-1]
          count_sample+=1
          normal_activity_changes.append(np.nansum(result))
        else:
          normal_activity_changes.append(0)

      # Calculate sample mean and standard deviation
      normal_activity_change_mean = np.mean(normal_activity_changes)
      normal_activity_change_std = np.std(normal_activity_changes)
      relative_change = (changed - normal_activity_change_mean)/normal_activity_change_std
      if relative_change is None:
        print("relative_change is None")
        relative_change = 0
      elif np.isnan(relative_change):
        print("relative_change is np.nan")
        relative_change = 0
        
      activity_change.append([changed, relative_change, normal_activity_change_mean, normal_activity_change_std,normal_activity_samples])
      activity_change_df = pd.DataFrame(activity_change, columns=['change_count', 'change_relative', 'normal_change_mean','normal_change_std','normal_samples'])
    if inplace:
      self.feature_df = pd.concat([self.feature_df,activity_change_df],axis=1)
    else:
      return activity_change_df
  def activity_count(self, inplace = True):
    print('Activity count function')

    activity_count = []
    for index in range(self.__len__()):
      dummy = self.activity[index]
      dummy = np.array(dummy)
      count_df = pd.Series(dummy).value_counts()
      #print(count_df)
      result = []
      for location in self.location_names:
        if location in count_df.index:
          result.append(count_df.loc[location])
        else:
          result.append(0)


      normal_activity_counts = []
      print(f"non_agit: {len(self.non_agitation[index])}")
      if len(self.non_agitation[index])==1:
        print(self.non_agitation[index])
      for arr in self.non_agitation[index]:
        arr = np.array(arr)         
        count_df = pd.Series(arr).value_counts()
        result = []
        for location in self.location_names:
          if location in count_df.index:
            result.append(count_df.loc[location])
          else:
            result.append(0)

        normal_activity_counts.append(result)
      normal_activity_counts = np.array(normal_activity_counts)
      activity_count_mean = np.mean(normal_activity_counts, axis=0)
      activity_count_std = np.std(normal_activity_counts, axis=0)
      activity_count_relative = (np.array(result) - activity_count_mean)/activity_count_std
      # Filling NaN values with 0, although it is in correct but we should feel with something
      activity_count_relative = [0 if np.isnan(x) else x for x in activity_count_relative]

      #print(f'rel {activity_count_relative.shape}')
      #print(f'mean {activity_count_mean.shape}')
      #print(f'std {activity_count_std.shape}')
      #print(f'result {len(result)}')
      #print("Shapes of arrays before concatenation:")
      #print("result:", np.shape(result))
      #print("activity_count_relative:", np.shape(activity_count_relative))
      #print("activity_count_mean:", np.shape(activity_count_mean))
      #print("activity_count_std:", np.shape(activity_count_std))

      activity_count.append(np.concatenate([result,activity_count_relative, activity_count_mean,activity_count_std]))


    activity_count_df = pd.DataFrame(activity_count,
              columns=self.location_columns)

    if inplace:
      self.feature_df = pd.concat([self.feature_df,activity_count_df],axis=1)
    else:
      return activity_count_df

  def feature_extraction(self, inplace = True):
    #self.init_df()
    self.activity_change(inplace)
    self.activity_count(inplace)
    self.physiology_features(inplace)
    if inplace:
      print('Feature dataframe got updated!')
    else:
      return self.feature_df

  def physiology_features(self, inplace = True):
    physiology_features = []
    for index in range(self.__len__()):
      dummy = self.agitation_params[index]
      dict_dummy = dict(dummy)

      result = []
      for param in self.physiology_names:
        if param in dict_dummy.keys():
          result.append(dict_dummy[param])
        else:
          result.append(0)
      physiology_features.append(result)
      physiology_df = pd.DataFrame(physiology_features,columns=self.physiology_names)

    if inplace:
      self.feature_df = pd.concat([self.feature_df,physiology_df],axis=1)
    else:
      return physiology_df
  def set_label(self,label):
    self.feature_df['label'] = label

  def save_df(self,path):
    self.feature_df.to_csv(path)

def save_concat_datasets(df_list,path):
  df_list = pd.concat(df_list)
  df_list.to_csv(path)

def find_numerical_column_names(df):
    """
    Function to collect the names of numerical columns in a DataFrame.

    Args:
    df (pd.DataFrame): The DataFrame to analyze.

    Returns:
    list: A list of column names that are numerical.
    """
    # Collect column names where the dtype is numerical
    numerical_columns = [col for col in df.columns if np.issubdtype(df[col].dtype, np.number)]
    return numerical_columns

def count_zeros(x):
  return len(x)-np.sum(x)

def count_ones(x):
  return np.sum(x)

def save_to_csv(results, file_path):
    df = pd.DataFrame([results])  # Convert dictionary to DataFrame

    # Check if file exists
    if os.path.exists(file_path):
        df.to_csv(file_path, mode='a', index=False, header=False)  # Append without header
    else:
        df.to_csv(file_path, mode='w', index=False, header=True)  # Create new file


# Function to label 'outside' in the 'location_name' column for gaps between 'Front Door' and 'Back Door'
def label_outside(df, threshold_minutes=2):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')
    new_rows = []

    for i in range(len(df) - 1):
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        current_time = current_row['timestamp']
        next_time = next_row['timestamp']

        # Check if the time difference exceeds the threshold
        if (next_time - current_time).total_seconds() / 60.0 > threshold_minutes:
            if (current_row['location_name'] in ['Front Door', 'Back Door'])  and (next_row['location_name'] in ['Front Door', 'Back Door']):
                while (next_time - current_time).total_seconds() / 60.0 > threshold_minutes:
                    current_time += pd.Timedelta(minutes=threshold_minutes)
                    if current_time >= next_time:
                        break
                    new_row = current_row.copy()
                    new_row['timestamp'] = current_time
                    new_row['location_name'] = 'outside'
                    new_rows.append(new_row)

    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
    return df

# Function to check if a time is between 10:00 PM and 8:00 AM
def is_night(time):
    return time >= pd.Timestamp("22:00:00").time() or time <= pd.Timestamp("08:00:00").time()

# Function to fill night gaps with 'Bedroom' entries every 5 minutes
def fill_night_gaps_with_bedroom(df, threshold_minutes=5):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')

    new_rows = []
    for i in range(len(df) - 1):
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        current_time = current_row['timestamp']
        next_time = next_row['timestamp']

        while (next_time - current_time).total_seconds() / 60.0 > threshold_minutes and is_night(current_time.time()):
            current_time += pd.Timedelta(minutes=threshold_minutes)
            if current_time >= next_time:
                break
            new_row = current_row.copy()
            new_row['timestamp'] = current_time
            new_row['location_name'] = 'Bedroom'
            new_rows.append(new_row)

    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
    return df

# Function to fill gaps with forward fill and backward fill for specified locations
def fill_gaps_with_forward_backward(df, threshold_minutes=3):
    df['timestamp'] = pd.to_datetime(df['timestamp'])
    df = df.sort_values(by='timestamp')

    backward_fill_locations = ['Front Door', 'Back Door', 'Fridge Door']
    new_rows = []

    for i in range(len(df) - 1):
        current_row = df.iloc[i]
        next_row = df.iloc[i + 1]
        current_time = current_row['timestamp']
        next_time = next_row['timestamp']

        if (next_time - current_time).total_seconds() / 60.0 > threshold_minutes:
            if current_row['location_name'] in backward_fill_locations and next_row['location_name'] not in backward_fill_locations:
                # Perform backward fill for the whole gap
                fill_time = next_time
                while (fill_time - current_time).total_seconds() / 60.0 > threshold_minutes:
                    fill_time -= pd.Timedelta(minutes=threshold_minutes)
                    if fill_time <= current_time:
                        break
                    new_row = next_row.copy()
                    new_row['timestamp'] = fill_time
                    new_row['location_name'] = next_row['location_name']
                    new_rows.append(new_row)

            else:
                # Perform forward fill for the whole gap
                fill_time = current_time
                while (next_time - fill_time).total_seconds() / 60.0 > threshold_minutes:
                    fill_time += pd.Timedelta(minutes=threshold_minutes)
                    if fill_time >= next_time:
                        break
                    new_row = current_row.copy()
                    new_row['timestamp'] = fill_time
                    new_row['location_name'] = current_row['location_name']
                    new_rows.append(new_row)

    df = pd.concat([df, pd.DataFrame(new_rows)], ignore_index=True).sort_values(by='timestamp').reset_index(drop=True)
    return df
