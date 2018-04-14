
# Copyright (c) 2017 Tsinghua University. All Rights Reserved.

# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at

#     http://www.apache.org/licenses/LICENSE-2.0

# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

# This Python file uses the following encoding: utf-8

import pickle
import scipy.stats
from intradayRecovery import *


def getBaseDis(path):
    '''
    input baseDis containing all the distances between two base stations
    :param:
    :return: a dict, base distance matrix
                     base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    '''

    f = open(path, 'rb')
    baseDis = cPickle.load(f)
    f.close()
    print 'get baseDis!'
    return baseDis

def getDayTra(day_list):
    '''
    input recovered trajectories of given dayIDs in day_list
    :param day_list: a list, the dayIDs of single day's recovered trajectories
    :return: dayTrace_set: a dict, dict[key]=value
                            where key is a int dayID in day_list, value is a list of recovered trajectories on that day
    '''
    dayTrace_set = {}   # every value is a list, storing one-day trajectories

    for day_num in day_list:
        f3 = open('pickles\\day'+str(day_num)+'_dayTrace.pkl', 'r')
        dayTra = pickle.load(f3)
        dayTrace_set[day_num] = dayTra
        f3.close()

    print 'get recover trajectory on each day!'
    return dayTrace_set

def getWeekTra(dayTrace_set, baseDis, usernum, day_list, time_gra):
    '''
    get recovered trajectories of the whole week by connecting neighboring two days one by one
    :param dayTrace_set:a dict, dict[key]=value
                        where key is a int dayID in day_list, value is a list of recovered trajectories on that day
    :param baseDis: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :param usernum: int, the number of users
    :param day_list: a list, the dayIDs of single day's recovered trajectories
    :param time_gra: int, dafault = 30
    :return: weekTra: a list, each item is a list of baseID in time temporal of the whole week
    '''
    # obtain information gain between neighboring day's trajectory
    temp_weekTra = dayTrace_set[day_list[0]]

    for day_num in day_list[1:]:
        print 'connect '+str(day_num-1)+'-'+str(day_num)+'!'
        temp_weekTra = infoGainConnectConcurrent(temp_weekTra, dayTrace_set[day_num], usernum, time_gra)
        print 'get '+str(day_num+1)+' days\' recovery trajectory!'

    weekTra = temp_weekTra
    print 'recover trajectory of the whole week!'

    return weekTra

def infoGainConnectConcurrent(dayTrace1, dayTrace2, usernum, time_gra):
    '''
    connect recovered trajectories of neighboring two days by considering individual daily mobility regularity,
    which means an individual's trajectories on different days are similar while different individuals' trajectories
    on different days are quite different.
    Inforamtion gain is able to measure the similarity and differences.
    :param dayTrace1: a list, each item is a list of baseID in time temporal on last day
    :param dayTrace2: a list, each item is a list of baseID in time temporal on next day
    :param usernum: int, the number of users
    :param time_gra: int, dafault = 30
    :return: connect_trace: a list, each item is a list of baseID in time temporal on neighboring two days
    '''
    # Function: day Trajectory connection(regularity)

    # ----------1. calculate information gain ---------------
    from multiprocessing import Pool
    # processors = 20  # spark
    processors = 4  # local computer

    N = usernum
    l_bounds = range(0, N, N/(processors-1))
    u_bounds = l_bounds[1:] + [N]
    bounds = zip(l_bounds, u_bounds)

    arg_dicts = [{
        "l_bound": b[0],
        "u_bound": b[1],
        "count": N,
        "dt1": dayTrace1,
        "dt2": dayTrace2
    } for b in bounds]

    # do multiprocessing
    pool = Pool(processors)
    results = pool.map(info_gain_calc_unit, arg_dicts)
    pool.close()
    pool.join()

    info_gain = []
    for result in results:
        info_gain.extend(result)
    info_gain = np.array(info_gain)

    # ---------2. find optimal match between two days' trajectories----------
    # method: night_info+bestAssignment
    night_base1 = getNightBase(dayTrace1, time_gra)
    night_base2 = getNightBase(dayTrace2, time_gra)
    night_base1 = np.array(night_base1)
    night_base2 = np.array(night_base2)

    info_gain_list, row_list, column_list = getSplitUser(night_base1, night_base2, info_gain)

    row_ind = []
    col_ind = []
    for matrix, row, column in zip(info_gain_list, row_list, column_list):
         temp_row_ind, temp_col_ind = bestAssignment(matrix)
         row_ind.extend([row[x] for x in temp_row_ind])
         col_ind.extend([column[x] for x in temp_col_ind])


    # ---------3. connect two days' trajectories----------
    connect_trace = []
    for i, j in zip(row_ind, col_ind):
        temp_trace = dayTrace1[i][:]
        temp_trace.extend(dayTrace2[j][:])
        connect_trace.append(temp_trace)

    return connect_trace

def info_gain_calc_unit(arg_dict):
    '''
    calculate part of info_gain matrix
    :param arg_dict: 1) l_nound, u_bound: int, calculate the info_gain between the l_bound-th ~ u_bound-th users's
                                          trajectories in dt1 and all the n users's trajectories in dt2
                     2) count: int, the number of users
                     3) dt1, dt2: list, each item is a user's trajectory (list of baseID)
    :return: info_gain: a (u_bound-l_bound)x(n) info_gain matrix
    '''
    l_bound = arg_dict["l_bound"]
    u_bound = arg_dict["u_bound"]
    print "This process will calc %d - %d" % (l_bound, u_bound)
    n = arg_dict["count"]
    dayTrace1 = arg_dict["dt1"]
    dayTrace2 = arg_dict["dt2"]

    Counter1 = []
    Counter2 = []
    Sunc1 = []
    Sunc2 = []
    for i in xrange(n):
        Counter1.append(Counter(dayTrace1[i]))
        Counter2.append(Counter(dayTrace2[i]))
        Sunc1.append(scipy.stats.entropy(np.array(Counter1[-1].values())/(float(np.sum(Counter1[-1].values())))))
        Sunc2.append(scipy.stats.entropy(np.array(Counter2[-1].values())/(float(np.sum(Counter1[-1].values())))))

    info_gain = []
    for i in xrange(l_bound, u_bound):
        info_gain.append([])
        print 'info_gain_present %d%%' % ((i-l_bound)*100/(u_bound-l_bound))
        for j in xrange(n):
            # print 'info_gain:', i, j
            info_gain[-1].append(calSuncDiff(Counter1[i], Counter2[j], Sunc1[i], Sunc2[j]))

    return info_gain

def calSuncDiff(count1, count2, S1, S2):
    '''
    calculate the information gain
    :param count1: a dict, count[key]=value, where key is a baseID and value is a int integer counting how many times
    the user access the base station on last day
    :param count2: a dict, count[key]=value, where key is a baseID and value is a int integer counting how many times
    the user access the base station on next day
    :param S1: the entropy of a user's trajectory on last day
    :param S2: the entropy of a user's trajectory on next day
    :return: int, 100000 times the information gain
    '''
    newcount = dict(Counter(count1.copy())+Counter(count2.copy()))

    n1 = float(np.sum(count1.values()))
    n2 = float(np.sum(count2.values()))

    S = scipy.stats.entropy((np.array(newcount.values()))/(n1+n2))
    result = S -S1*n1/(n1+n2) - S2*n2/(n1+n2)
    return int(result*(10**5))

def getNightBase(dayTrace, time_gra):
    '''
    find the most frequent visited baseID of each user's trajectory at night, this base station is likely to be home
    :param dayTrace: a list, ecah item is a user's recovered trajectories, that's a list of baseID in temporal order
    :param time_gra: int, dafault = 30
    :return: nightBase: a list, each item is the most frequent visited baseID for a user's trajectory at night
    '''
    nightBase = []
    for trace in dayTrace:
        night_topBase = getTopBase(trace, time_gra)
        nightBase.append(night_topBase)
    return nightBase

def getTopBase(trace, time_gra):
    '''
    get a user's records at night and find the top frequently-visited baseID
    :param trace: a list, a user's recovered trajectories, that's a list of baseID in temporal order
    :param time_gra: int, dafault = 30
    :return: topBase: a int baseID, the top frequently-visited baseID for this user's records at night
    '''
    k1 = 24*60/time_gra  # 48
    k = 6*60/time_gra  # 12
    N = len(trace)/k1
    ind = []
    for i in xrange(0, N):
        ind.extend(range(k1*i, k1*i+k))
    nightBases = list((np.array(trace[:]))[ind])
    stats = (Counter(nightBases)).items()
    stats = zip(*stats)
    topBase = stats[0][np.argmax(np.array(stats[1]))]
    return topBase

def getSplitUser(night_base1, night_base2, info_gain):
    '''
    split the info_gain matrix into submatrices based on night
    :param night_base1: a list, each item is the most frequent visited baseID of each user's trajectory at night
                        on last day
    :param night_base2: a list, each item is the most frequent visited baseID of each user's trajectory at night
                        on next day
    :param info_gain: matrix, each item info_gian[i,j] is the information gain of i-th user in night_base1 and
                      j-th user in night_base2
    :return: info_gain_list: list of submatrices
             row_list: a list, the i-th item records matrix's i-th row's row index in the original N*N matrix
             col_list: a list, the j-th item records matrix's j-th column's column index in the original N*N matrix
    '''
    # input is array
    stats1 = Counter(night_base1)
    stats2 = Counter(night_base2)

    row_list = [[]]  # item of index 0 are unshared base stations of night_base1
    col_list = [[]]  # item of index 0 are unshared base stations of night_base2
    N1 = night_base1.shape[0]
    all_rows = np.array(range(N1))
    N2 = night_base2.shape[0]
    all_cols = np.array(range(N2))

    for key in stats1:
        if key in stats2:
            temp_row = all_rows[night_base1 == key]
            temp_col = all_cols[night_base2 == key]
            if stats1[key] < stats2[key]:
                temp_info_gain = info_gain[temp_row]
                temp_info_gain = temp_info_gain[:, temp_col]
                k = stats2[key] - stats1[key]
                select_col = (np.argsort(np.sum(temp_info_gain, axis=0)))[(-k):]  # sum of every column
                col_list[0].extend(temp_col[select_col])
                temp_col = np.delete(temp_col, select_col)

            elif stats2[key] < stats1[key]:
                temp_info_gain = info_gain[temp_row]
                temp_info_gain = temp_info_gain[:, temp_col]
                k = stats1[key] - stats2[key]
                select_row = (np.argsort(np.sum(temp_info_gain, axis=1)))[(-k):]  # sum of every row
                row_list[0].extend(temp_row[select_row])
                temp_row = np.delete(temp_row, select_row)

            row_list.append(temp_row)
            col_list.append(temp_col)
            del stats2[key]
        else:
            row_list[0].extend(all_rows[night_base1 == key])

    if len(stats2) != 0:
        for key in stats2:
            col_list[0].extend(all_cols[night_base2 == key])

    info_gain_list = []
    if row_list[0] != []:
        r = row_list[0]
        c = col_list[0]
        temp_info_gain = info_gain[r]
        temp_info_gain = temp_info_gain[:, c]
        info_gain_list.append(temp_info_gain)
        flag = 1
    else:
        flag = 0

    for r, c in zip(row_list[1:], col_list[1:]):
        temp_info_gain = info_gain[r]
        temp_info_gain = temp_info_gain[:, c]
        info_gain_list.append(temp_info_gain)
    if flag == 0:
        del row_list[0]
        del col_list[0]
    return info_gain_list, row_list, col_list

def main():
    # parameters
    usernum = 10  # 100000
    day_list = range(7)
    time_gra = 30   # 30 minutes
    path = '\\data\\baseDistance.pkl'   # store baseDis

    # 1. input single day' recovery trajectory and extra information
    dayTrace_set = getDayTra(day_list)
    baseDis = getBaseDis(path)  # distance between two base stations

    # 2.recover trajectory during the whole week
    weekTra = getWeekTra(dayTrace_set, baseDis, usernum, day_list, time_gra)

    # 3. save
    paths = 'recovery results\\week'
    saveRecoverTrace(paths, weekTra)

if __name__ == "__main__":
    main()