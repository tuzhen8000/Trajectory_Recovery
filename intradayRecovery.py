
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

import numpy as np
import time
import cPickle
import os
from collections import Counter
from scipy.optimize import linear_sum_assignment


def getPreInformation(input1_path, input2_path):
    '''
    input base_dict and next_base
    :param input1_path: a string, file path storing next_base
    :param input2_path: a string, file path storing base_dict
    :return: next_base: a dict, predicted next base matrix
                        next_base[base1-1][base2-1] = base3 means base1 -> base2 -> base3
              base_dist: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    '''
    f1 = open(input1_path, 'rb')
    f2 = open(input2_path, 'rb')

    # predicted next base matrix
    # example: next_base[base1-1][base2-1] = base3 means base1 -> base2 -> base3
    next_base = cPickle.load(f1)

    # base distance matrix
    # example: base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    base_dist = cPickle.load(f2)

    f1.close()
    f2.close()
    
    return next_base, base_dist
    
def getTrajectory(tra_path):
    '''
    input all the users' trajectories
    :param tra_path: a string, file path storing all the users' trajectories
    :return: tra_base: a list, every item is also a baseID(int) list in temporal order like [87,85,98,...]
              time: a list of time slot ID , default = [0,1,2,3,...,336]
    '''
    f1 = open(tra_path, 'r')
    tra_base = []  # base list of each trajectory in time order 
    count = 0
    for line1 in f1:
        count += 1
        if count % 100 == 0:
            print 'user number: ', count
        
        line1 = line1.strip()
        base = line1.split()
        tra_base.append([int(b) for b in base])    
    time = range(len(base))  # all the time of trajectories are the same range
    f1.close()

    temp = []
    for b in tra_base:
        temp.extend(b)
    print len(Counter(temp))
    
    return tra_base, time
    
def computeBaseAccessInfo(path, tra_base, time, usernum, time_gra):
    '''
    compute how many users in each base station at every time slot
    :param path: a string, file path storing base_access if there exists
    :param tra_base:a list, every item is also a baseID(int) list in temporal order like [87,85,98,...]
    :param time: a list of time slot ID , default = [0,1,2,3,...,336]
    :param usernum: int, the number of users
    :param time_gra: int, default = 30
    :return: base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    '''
    base_access = {}
    
    if os.path.exists(path):
        print '\tloading existing base access info......'
        base_access = pickleLoad([path])
    else:
        print '\tlinking base access info......'
        base_access = {}
        for base in tra_base:
            # compute how many users in each base station at every time slot
            base_access = updateBaseAccess(usernum, base, time, base_access, time_gra)
            # {baseID:{day1:[2,3,1,...],...,day7:[3,2,3,...]}}
        pickleSave(path, [base_access])
        # f = open(path, 'wb')
        # cPickle.dump(base_access, f)
        # f.close()
    
    return base_access
    
def updateBaseAccess(usernum, base, time, base_access, time_gra):
    '''
    update base_access when one more user is added
    :param usernum: int, the number of users
    :param base: a baseID(int) list in temporal order like [87,85,98,...]
    :param time: a list of time slot ID , default = [0,1,2,3,...,336]
    :param base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    :param time_gra: int, default = 30
    :return: base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    '''
    # format of base_access: {baseID:{day1:[2,3,1,...],...,day7:[3,2,3,...]}}
    
    day_timeslot_num = 24*60/time_gra  # the number of time slots every day has
    
    for b, t in zip(base, time):
        day = t/day_timeslot_num
        timeslot_id = t % day_timeslot_num
        if b in base_access:
            if day in base_access[b]:
                base_access[b][day][timeslot_id] += 1
            else:
                base_access[b][day] = []
                for i in xrange(day_timeslot_num):
                    base_access[b][day].append(0)
                base_access[b][day][timeslot_id] += 1
        else:
            base_access[b] = {}
            base_access[b][day] = []
            for i in xrange(day_timeslot_num):
                base_access[b][day].append(0)
            base_access[b][day][timeslot_id] += 1
    return base_access
    
def getNightTra(usernum, day_num, path1, base_dist, base_access, time_gra):
    '''
    get individual trajectories at night from aggregated trajectories
    if the file exists, read it; else recover individual trajectories at night from aggregated data (base_access)
    :param usernum: int, the number of users
    :param day_num: int, the dayID
    :param path1: a string storing recovered trajectories at night of a single day
    :param base_dist: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :param base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    :param time_gra: int, default = 30
    :return: night_tra: a list, each item is a user's recovered baseID list at night of the day_num-th day
    '''



    if os.path.exists(path1):
        f1 = open(path1, 'rb')
        nightTra = cPickle.load(f1)
        # daytimeTrace = cPickle.load(f2)
    else:
        nightTra = recoverNightTrajectory(base_access, day_num, base_dist, usernum, time_gra)
        f1 = open(path1, 'wb')
        cPickle.dump(nightTra, f1)
        # f2 = open(path2, 'wb')
        # cPickle.dump(daytimeTrace, f2)
    f1.close()
    # f2.close()

    return nightTra

def recoverNightTrajectory(base_access, day_num, base_dist, usernum, time_gra):
    '''
    recover individual trajectories at night from aggregated data (base_access)
    :param base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    :param day_num: int, the number of users
    :param base_dist: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :param usernum: int, the number of users
    :param time_gra: int, default = 30
    :return: nightTra: a list, each item is a user's recovered baseID list at night of the day_num-th day
    '''
    path1 = 'pickles/day'+str(day_num)+'_nightPoints'+'.pkl'
    path3 = 'pickles/day'+str(day_num)+'_staticNightTrajectory'+'.pkl'

    min_daytime_timeslot_id = 6*60/time_gra   # value is 12
    k = min_daytime_timeslot_id

    # 1. recover static trajectories at night
    if os.path.exists(path1):
        sta_nightTra, nightPoints = pickleLoad([path1, path3])

    else:
        sta_nightTra = []
        nightPoints = []
        for i in xrange(0, k):
            nightPoints.append([])
        count = 0
        for base in base_access:
            if day_num in base_access[base]:
                day_stats = base_access[base][day_num]
                # example: [2,3,1,5,...] represents the number of users accessing base at each time slot
                # the length is 48
                minValue = min(day_stats[0:k])
                temp_trace = [base]*k
                for i in xrange(0, minValue):
                    sta_nightTra.append(temp_trace[:])
                for i in xrange(0, k):
                    if day_stats[i] > minValue:
                        nightPoints[i].append((base, day_stats[i] - minValue))

            else:
                continue

        pickleSave([path1, path3], [sta_nightTra, nightPoints])

    # 2. recover dynamic trajectories at night
    paths = 'pickles/day'+str(day_num)+'_tempDynamicNightTrajectory'+'.pkl'
    if os.path.exists(paths):
        temp_dyn_nightTra = pickleLoad([paths])
        j = len(temp_dyn_nightTra[0])
        if j < k:
            for i in xrange(j, k):
                print 'day_num: ', day_num, ' time slot id: ', i
                predict_base = [x[-1] for x in temp_dyn_nightTra]
                real_base = []
                for item in nightPoints[i]:  # (baseID, accessing user number) in the first time slot
                    b = item[0]
                    b_usernum = item[1]
                    for i in xrange(b_usernum):
                        real_base.append(b)
                nextPoint = connectPoints(predict_base, real_base, base_dist)
                # base_dist stores the distance between two base stations
                temp_dyn_nightTra = updateTrajectory(temp_dyn_nightTra, nextPoint)
                pickleSave([paths], [temp_dyn_nightTra])

    else:
        temp_dyn_nightTra = []
        for item in nightPoints[0]:  # (baseID, accessing user number) in the first time slot
            b = item[0]
            b_usernum = item[1]
            for i in xrange(b_usernum):
                temp_dyn_nightTra.append([b])
        for i in xrange(1, k):  # k is min_daytime_timeslot_id, k=12
            print 'day_num: ', day_num, ' time slot id: ', i
            predict_base = [x[-1] for x in temp_dyn_nightTra]
            real_base = []
            for item in nightPoints[i]:  # (baseID, accessing user number) in the first time slot
                b = item[0]
                b_usernum = item[1]
                for i in xrange(b_usernum):
                    real_base.append(b)
            nextPoint = connectPoints(predict_base, real_base, base_dist)
            # base_dist stores the distance between two base stations
            temp_dyn_nightTra = updateTrajectory(temp_dyn_nightTra, nextPoint)
            pickleSave([paths], [temp_dyn_nightTra])

    nightTra = sta_nightTra
    nightTra.extend(temp_dyn_nightTra)
    return nightTra

def getDaytimeTrajectory(path1, base_access, nightTra, day_num, base_dist, next_base, usernum, time_gra):
    '''
    get individual trajectories during daytime from aggregated trajectories
    if the file exists, read it; else recover individual trajectories during daytime from aggregated data (base_access)
    :param path1: a string storing recovered trajectories of a single day
    :param nightTra: night_tra: a list, each item is a user's recovered baseID list at night of the day_num-th day
    :param next_base: a dict, predicted next base matrix
                        next_base[base1-1][base2-1] = base3 means base1 -> base2 -> base3
    :param base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    :param day_num: int, the number of users
    :param base_dist: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :param usernum: int, the number of users
    :param time_gra: int, default = 30
    :return: daytimeTra: a list, each item is a user's recovered baseID list of the day_num-th day
    '''
    if os.path.exists(path1):
        f1 = open(path1, 'rb')
        daytimeTra = cPickle.load(f1)
        f1.close()
    else:
        daytimeTra = \
            recoverDaytimeTrajectory(nightTra, base_access, next_base, base_dist, day_num, usernum, time_gra)
        f1 = open(path1, 'wb')
        cPickle.dump(daytimeTra, f1)
        f1.close()
    return daytimeTra

def recoverDaytimeTrajectory(nightTra, base_access, next_base, base_dist, day_num, usernum, time_gra):
    '''
    continue recovering individual trajectories during daytime from aggregated data (base_access)]
    :param nightTra: night_tra: a list, each item is a user's recovered baseID list at night of the day_num-th day
    :param next_base: a dict, predicted next base matrix
                        next_base[base1-1][base2-1] = base3 means base1 -> base2 -> base3
    :param base_access: a dict, count how many users in each base station at every time slot
                          format: {baseIDX:{day1:[2,3,1,...],...,day7:[3,2,3,...]}} where everyday has 48 time slot
                          means that 2 users access baseIDX at the first time slot on day1 and ...
    :param day_num: int, the number of users
    :param base_dist: a dict, base distance matrix
                        base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :param usernum: int, the number of users
    :param time_gra: int, default = 30
    :return: daytimeTra: a list, each item is a user's recovered baseID list of the day_num-th day
    '''
    min_daytime_timeslot_id = 6*60/time_gra   # value is 12
    max_daytime_timeslot_id = 24*60/time_gra - 1  # value is 47
    k = min_daytime_timeslot_id
    k1 = max_daytime_timeslot_id + 1

    path1 = 'pickles/day'+str(day_num)+'_daytimePoints'+'.pkl'
    if os.path.exists(path1):
        daytimePoints = pickleLoad([path1])
    else:
        daytimePoints = []
        for i in xrange(k, k1):
            daytimePoints.append([])
        for base in base_access:
            if day_num in base_access[base]:
                day_stats = base_access[base][day_num]
                # example: [2,3,1,5,...] represents the number of users accessing base at each time slot
                # the length is 48
                for i in xrange(k, k1):
                    if day_stats[i] > 0:
                        daytimePoints[i-k].append((base, day_stats[i]))
        pickleSave([path1], [daytimePoints])

    # recover dynamic trajectories at night
    paths = 'pickles/day'+str(day_num)+'_tempDaytimeTrajectory'+'.pkl'
    if os.path.exists(paths):
        temp_daytimeTra = pickleLoad([paths])
        j = len(temp_daytimeTra[0])
        if j < k1:
            for i in xrange(j, k1):
                print 'day_num: ', day_num, ' time slot id: ', i
                predict_base = getPredictBase(temp_daytimeTra, next_base)
                real_base = []
                for item in daytimePoints[i-k]:  # (baseID, accessing user number) in the first time slot
                    b = item[0]
                    b_usernum = item[1]
                    for i in xrange(b_usernum):
                        real_base.append(b)
                nextPoint = connectPoints(predict_base, real_base, base_dist)
                # base_dist stores the distance between two base stations
                temp_daytimeTra = updateTrajectory(temp_daytimeTra, nextPoint)
                pickleSave([paths], [temp_daytimeTra])

    else:
        temp_daytimeTra = nightTra
        for i in xrange(k, k1):  # k is min_daytime_timeslot_id, k=12
            print 'day_num: ', day_num, ' time slot id: ', i
            predict_base = getPredictBase(temp_daytimeTra, next_base)
            real_base = []
            for item in daytimePoints[i-k]:  # (baseID, accessing user number) in the first time slot
                b = item[0]
                b_usernum = item[1]
                for i in xrange(b_usernum):
                    real_base.append(b)
            nextPoint = connectPoints(predict_base, real_base, base_dist)
            # base_dist stores the distance between two base stations
            temp_daytimeTra = updateTrajectory(temp_daytimeTra, nextPoint)
            pickleSave([paths, path1], [temp_daytimeTra])
            
    daytimeTra = temp_daytimeTra
    return daytimeTra

def getPredictBase(daytimeTra, next_base):
    '''
    for each subtrajectory in daytimeTra, obtain its next baseID assuming the same velocity in neighboring time slots.
    :param daytimeTra: a list, each item is a user's recovered subtrajectory (a baseID list)
    :param next_base: a dict, predicted next base matrix
                      next_base[base1-1][base2-1] = base3 means base1 -> base2 -> base3
    :return: pridict_base: a list, each item is a subtrajectory's next baseID
    '''
    predict_base = []
    for tra in daytimeTra:
        base = next_base[tra[-2]-1][tra[-1]-1]
        predict_base.append(base)
    return predict_base

def connectPoints(predict_base, real_base, base_dist):
    '''
    find optimal matched baseID from the real baseID list for each recovered subtrajectory
    1. we obtain predicted baseID for every recovered subtrajectory according to the velocity model
    2. we compute the distance(error) of N predicted baseIDs and N real baseIDs and get a NxN matrix, then the problem
       transfers to finding a solution to match each row with a unique column when the sum of the relevant values
       is minimized. In other words, the distance error of the predicted and matched real records is minimized.
    3. we use bestAssignment to find the optimal match
    :param predict_base: a baseID list, each item is a predicted baseID of a recovered subtrajectory
    :param real_base: a baseID list, each item is a real recorded baseID
    :param base_dist: a dict, base distance matrix
                       base_dist[base1-1][base2-1] = dist means the spatial distance between base1 and base2
    :return: nextPoint: a list, each item is matched real recorded baseID of a recovered subtrajectory
    '''
    nextPoint = []

    dict1 = Counter(predict_base)
    dict2 = Counter(real_base)
    share_base = list(set(dict1.keys()) & set(dict2.keys()))
    share_dict = {}
    calc_ind1 = []  # index of left bases in last time slot
    calcBase1 = []  # left bases in last time slot
    calcBase2 = []  # left bases in next time slot
    for b in share_base:
        share_dict[b] = min(dict1[b], dict2[b])
    i = 0
    for b in predict_base:
        if b in share_dict:
            nextPoint.append(b)
            share_dict[b] -= 1
            if share_dict[b] == 0:
                del share_dict[b]
            dict2[b] -= 1
            if dict2[b] == 0:
                del dict2[b]
        else:
            nextPoint.append(None)
            calc_ind1.append(i)
            calcBase1.append(b)
        i += 1
    for b in dict2:
        for i in xrange(dict2[b]):
            calcBase2.append(b)

    if len(calcBase1) != 0:
        matrix = []
        for b1 in calcBase1:
            matrix.append([])
            for b2 in calcBase2:
                if b2 < b1:
                    k1, k2 = b2, b1
                else:
                    k1, k2 = b1, b2
                dis = base_dist[k1-1][k2-k1-1]
                matrix[-1].append(dis)

        # Function: best assignment
        matrix = np.array(matrix)
        # 1. find optimal matching by bestAssignment
        matrix_list = [matrix]
        row_list = [range(len(calcBase1))]
        column_list = [range(len(calcBase1))]

        row_ind = []
        col_ind = []
        for matrix, row, column in zip(matrix_list, row_list, column_list):
             temp_row_ind, temp_col_ind = bestAssignment(matrix)
             row_ind.extend([row[x] for x in temp_row_ind])
             col_ind.extend([column[x] for x in temp_col_ind])
        # 2. update nextPoint
        for r, c in zip(row_ind, col_ind):
            nextPoint[calc_ind1[r]] = calcBase2[c]
    return nextPoint

def bestAssignment(cost):
    '''
    find an optimal solution to match each row(worker) with a unique column(work) to minimize the total cost
    :param cost: a square matrix, cost[i,j] is the cost that i-th worker dose j-th work
    :return: row_inx: a list representing each row's cluster label
              col_ind: a list representing each column's cluster label
    '''
    t1 = time.time()
    row_ind, col_ind = linear_sum_assignment(cost)
    t2 = time.time()
    # print 'time of bestAssignment', t2-t1
    return row_ind, col_ind

def updateTrajectory(Trace, nextPoint):
    '''
    connect previous trajectory with predicted next baseID
    the i-th baseID in nextPoint is the predicted next baseID of the i-th subtrajectory in Trace
    :param Trace: a list, each item is a baseID list representing a user's previous recovered trajectory
    :param nextPoint: a list, each item is a baseID representing a user's predicted next baseID
    :return: newTrace: a list, each item is a new baseID list that the predicted next baseID is added.
    '''
    newTrace = []
    for x, y in zip(Trace, nextPoint):
        newTrace.append(x)
        newTrace[-1].append(y)
    return newTrace

def pickleSave(path_list, data_list):
    '''
    save data in given file path
    :param path_list: a list of string, each string is a file path to load data
    :param data_list: a list of data to to saved as *.pkl
    :return: True
    '''
    for path, data in zip(path_list, data_list):
        f = open(path, 'wb')
        cPickle.dump(data, f)
        f.close()
    return True

def pickleLoad(path_list):
    '''
    load data (*.pkl) in given file path
    :param path_list: a list of string, each string is a file path to load data
    :return: data_list: a list of loaded data
    '''
    data_list = []
    for path in path_list:
        f = open(path, 'rb')
        data_list.append(cPickle.load(f))
        f.close()
    if len(data_list) == 1:
        data_list = data_list[0]
    return data_list

def main(usernum, input1_path, input2_path, time_gra, connect_days):
    '''
    recover individual trajectories from aggregated trajectory data
    :param usernum: int, the number of users
    :param input1_path: a string, file path storing next_base
    :param input2_path: a string, file path storing base_dict
    :param time_gra: int, dafault = 30
    :param connect_days: a list, the dayIDs of recovered trajectories
    :return: True
    '''
    # 1. input pre-calculated information
    next_base, base_dist = getPreInformation(input1_path, input2_path)
    print 'Step1: Finish loading baseDistance and nextBase Matrix!'

    # 2. obtain aggregated mobility data: information of accessing base-station
    path = 'data\\aggregateMobility_'+str(usernum)+'.pkl'   # store base_access
    base_access = pickleLoad([path])
    # base_access: a dict, store how many users in each base station at every time slot
    print 'Step2: Finish loading base access info!'

    base_access = pickleLoad([path])
    count = 0
    for key in base_access:
        if 0 in base_access[key]:
            count += base_access[key][0][0]
    print count


    # 3. connect everyday trajectory
    for i in connect_days:
        day_num = i

        # 3.1 connect trajectory at night
        # store night trajectories on each day
        path1 = 'pickles\\day'+str(day_num)+'_nightTrajectory'+'.pkl'

        nightTra = getNightTra(usernum, day_num, path1, base_dist, base_access, time_gra)

        # 3.2 continue connecting trajectories during daytime
        path1 = 'pickles\\day'+str(day_num)+'_daytimeTrajectory'+'.pkl'
        daytimeTra = \
            getDaytimeTrajectory(path1, base_access, nightTra, day_num, base_dist, next_base, usernum, time_gra)

        # 3.3 save recovered(connected) trajectories
        paths = 'recovery results\\day'+str(day_num)+'.txt'
        if not (os.path.exists(paths)):
            saveRecoverTrace(paths, daytimeTra)
        path1 = 'pickles\\day'+str(day_num)+'_dayTrace.pkl'
        f1 = open(path1, 'w')
        cPickle.dump(daytimeTra, f1)
        f1.close()
        print 'day:'+str(day_num)+' trajectory recovery finished!'

    return True

def saveRecoverTrace(paths, data):
    '''
    save data in given file path
    :param paths: a string, the file path the data will be saved
    :param data: a list, each item is a list of integers
    :return: None
    '''
    f3 = open(paths, 'w')
    for tra in data:
        for x in tra:
            f3.write(str(x)+' ')
        f3.write('\n')
    f3.close()

def runMain():
    # set parameters
    usernum = 100000
    time_gra = 30    # time granularity 30 minutes
    connect_days = range(7)
    input1_path = 'data\\nextBase.pkl'      # predicted next base matrix
    input2_path = 'data\\baseDistance.pkl'  # base distance matrix

    # choose user trajectory of Index [0, usernum) from the whole data
    t1 = time.time()
    main(usernum, input1_path, input2_path, time_gra, connect_days)
    t2 = time.time()
    print 'total time:(min)', (t2-t1)/60

    return True


if __name__ == "__main__":
    runMain()