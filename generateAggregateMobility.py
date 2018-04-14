
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
import cPickle
import os

def getContTimeTra(baseloc, input1_path, input2_path, output1_path, output2_path, time_gra, time_len, usernum):
    '''
    get users' continuous whole trajectories by adding missing records, since in some time slots
    there are no records (missed records)
    :param baseloc: a list, contain gps of every baseID
                    baseloc[baseID-1] = [longitude, latitude]
                    where baseID is an integer, longitude and latitude are float.
    :param input1_path: a string, file path of base data after preprocessing
                        format of file's each line: baseID1 \0 baseID2 \0 baseID3
                        example of file's each line: 87 87 100 123
    :param input2_path: a string, file path of time data after preprocessing
                        format: timeslotID1 \0 timeslotID2 \0 timeslotID3
                        example of file's each line: 87 87 100 123
    :param output1_path: a string, file path of base data after location interpolation
    :param output2_path: a string, file path of time data after location interpolation
    :param time_gra: int, default = 30
    :param time_len: an int integer, the length of original data's duration
    :param usernum: int, the number of users
    :return: tra_base: a list, every list is 336-length list representing a user's continuous whole trajectory
             tra_time: a list, default = [0,1,2,...,335]
    '''
    f1 = open(input1_path, 'r')
    f2 = open(input2_path, 'r')
    f3 = open(output1_path, 'w')
    f4 = open(output2_path, 'w')
    count = 0
    tra_base = []
    for line1 in f1:
        count += 1

        line2 = f2.readline()
        line1 = line1.strip().split()
        line2 = line2.strip().split()
        base = [int(b) for b in line1]  # min_baseID is 1 not 0
        time = [int(t) for t in line2]

        pointnum_thr = int(time_len/time_gra*0.8)  # require 80% of time has records
        max_pointnum = int(time_len/time_gra)
        if len(base) >= pointnum_thr:
            new_base, new_time = addMissingRecords(base, time, baseloc, max_pointnum)
            tra_base.append(new_base)
            for b, t in zip(new_base, new_time):
                f3.write(str(b)+' ')
                f4.write(str(t)+' ')
            f3.write('\n')
            f4.write('\n')
            print len(tra_base)
            if len(tra_base) >= usernum:
                break

    f1.close()
    f2.close()
    f3.close()
    f4.close()
    return tra_base, new_time

def getBaseloc(file_path):
    '''
    get gps of every baseID
    :param file_path: a string, file path storing gps of evert baseID
            format of file's every line: longitude \t latitude
            example of file's every line: 121.409700000000    31.1024100000000
    :return: baseloc: a list, contain gps of every baseID
                       baseloc[baseID-1] = [longitude, latitude]
                       where baseID is an integer, longitude and latitude are float.
    '''
    f = open(file_path, 'r')
    baseloc = []
    for line in f:
        line = line.strip()
        gps = line.split()
        # example: 121.409700000000	\t 31.1024100000000
        baseloc.append([float(gps[0]), float(gps[1])])
    f.close()
    return baseloc

def addMissingRecords(base, time, baseloc, max_pointnum):
    '''
    based on neighboring records, add missed records when there is no record in that time slot
    :param base: a list, accessing base stations (baseID) in temporal order
                    where every item is an int integer like 87
    :param time: a list, recorded time (time slot ID) in temporal order
                    where every item is an int integer like 1
    :param baseloc:a list, contain gps of every baseID
                    baseloc[baseID-1] = [longitude, latitude]
                    where baseID is an integer, longitude and latitude are float.
    :param max_pointnum: an int integer, (defalut=336)
                         the number of points when every time slot has a recorded point without missing
    :return:new_base: a list, all the baseIDs containing added base stations in temporal order
                       where every item is an int integer, the number of items is max_pointnum
             new_time: a list, all the time slot IDs in temporal order
                       format: [0,1,2,...,max_pointnum-1]
    '''
    new_base = []
    new_time = []

    # 1. add missing points before the first record
    if time[0] != 0:
        for i in xrange(time[0]):
            new_base.append(base[0])
            new_time.append(i)
    new_base.append(base[0])
    new_time.append(time[0])

    # 2. add missing points in the blank time of the trajectory by using interpolation
    L = len(base)
    for i in xrange(1, L):
        if time[i]-time[i-1] != 1:
            missing_time = range(time[i-1]+1, time[i])
            missing_num = len(missing_time)
            missing_base = baseInterpolation(base[i-1], base[i], missing_num, baseloc)
            new_base.extend(missing_base)
            new_time.extend(missing_time)
        new_base.append(base[i])
        new_time.append(time[i])

    # 3. add missing points after the last record
    if time[-1] != max_pointnum-1:
        for i in xrange(time[-1]+1, max_pointnum):
            new_base.append(base[-1])
            new_time.append(i)
    return new_base, new_time

def baseInterpolation(base1, base2, missing_num, baseloc):
    '''
    add missing base stations between base1 and base2 by location interpolation
    example: base list: [base1, unknown, unknown, unknown, base2] then missing_num = 3
            by linear interpolation we get 3 base stations to replace unknown base stations
            finally we get [base1, A, B, C，base2], return [A,B,C]
    :param base1: int, the first base station ID
    :param base2: int, the last base station ID
    :param missing_num: the number of missing base stations between base1 and base2
    :param baseloc: a list, contain gps of every baseID
                    baseloc[baseID-1] = [longitude, latitude]
                    where baseID is an integer, longitude and latitude are float.
    :return: a list, added base stations (base IDs) by linear interpolation
    '''
    missing_base = []
    if base1 == base2:
        for i in xrange(missing_num):
            missing_base.append(base1)
    else:
        gps1 = baseloc[base1-1]  # baseID starts from 1, while index of baseloc starts from 0
        gps2 = baseloc[base2-1]
        for i in xrange(1, missing_num+1):
            temp_gps = [gps1[0]+(gps2[0]-gps1[0])*i/(missing_num+1), gps1[1]+(gps2[1]-gps1[1])*i/(missing_num+1)]
            missing_base.append(getNearestBase(temp_gps, baseloc))
    return missing_base

def getNearestBase(gps, baseloc):
    '''
    find given gps's nearest base station (baseID)
    :param gps: a list, [longitude, latitude], two items are float
    :param baseloc:  list, contain gps of every baseID
                       baseloc[baseID-1] = [longitude, latitude]
                       where baseID is an integer, longitude and latitude are float.
    :return: nearest_base: an int integer, the baseID of nearest base station
    '''
    dis = []
    for loc in baseloc:
        dis.append(gpsDistance(loc, gps))
    nearest_base = np.argmin(np.array(dis)) + 1  # baseID starts from 1, while index of array starts from 0
    return nearest_base

def gpsDistance(gps1, gps2):
    '''
    calculate the distance of between gps1 and gps2 in physical world
    :param gps1: a list, [longitude, latitude], two items are float
    :param gps2: a list, [longitude, latitude], two items are float
    :return: distance: float
    '''
    if gps1 == gps2:
        return 0.0
    else:
        lon2m_shanghai = 95013.7300129
        lat2m_shanghai = 111138.62533333
        delta1 = abs(gps1[0]-gps2[0])
        delta2 = abs(gps1[1]-gps2[1])
        distance = ((delta1*lon2m_shanghai)**2+(delta2*lat2m_shanghai)**2)**0.5
        return distance

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

def main():
    # parameters
    baseloc_path = 'raw data\\Baselocation'
    input1_path = 'data\\original_base'
    input2_path = '.data\\original_time'
    output1_path = 'data\\trace_base'
    output2_path = 'data\\trace_time'

    time_gra = 30  # 30 minutes
    time_len = 60*24*7
    usernum = 10
    
    baseloc = getBaseloc(baseloc_path)
    tra_base, time = getContTimeTra(
        baseloc, input1_path, input2_path, output1_path, output2_path, time_gra, time_len, usernum)

    # generate aggregated mobility data
    path = 'data\\aggregateMobility_'+str(usernum)+'.pkl'   # store base_access
    base_access = computeBaseAccessInfo(path, tra_base, time, usernum, time_gra)
    if not os.path.exists(path):
        pickleSave([path], [base_access])





if __name__ == '__main__':
    main()