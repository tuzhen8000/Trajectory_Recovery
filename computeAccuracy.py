
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
from interdayRecovery import *
from intradayRecovery import *

def getAccuracy(recover_trace, real_trace, baseDis):
    '''
    calculate the average accuracy and distance error between real and recovered trajectory datasets
    :param recover_trace: a list, represents recovered trajectory dataset
                       each item is a list, a user's recovered trajectory's accessed baseIDs in temporal order
    :param real_trace: a list, represents real trajectory dataset
                       each item is a list, a user's original trajectory's accessed baseIDs in temporal order
    :param baseDis: a dict, baseDis[(base1, base2)] = distance representing the distance between base1 and base2
                    where base1 and base2 are both int and base1 is smaller than base2
    :return: average_accuracy: float, an average value of all the user trajectories' recovery accuracy
              average_error: float, an average value of all the user trajectories' recovery error
    '''
    matchIndex = []
    commonIndex = range(len(real_trace))
    traceDistance = []
    accuracy = []
    count = 0
    for x in real_trace:
        count += 1
        print 'count:', count

        M = len(recover_trace)
        temp_accuracy = np.sum((np.repeat([x], [M], axis=0) - np.array(recover_trace)) == 0, axis=1)

        inx = np.argmax(np.array(temp_accuracy))
        accuracy.append(round(temp_accuracy[inx]/float(len(x)), 4))
        matchIndex.append(commonIndex[inx])
        traceDistance.extend(getTraceDis(x, recover_trace[inx], baseDis))
        del recover_trace[inx]
        del commonIndex[inx]
    average_accuracy = np.mean(accuracy)
    average_error = np.mean(traceDistance)

    return average_accuracy, average_error
        
def getTraceDis(real_trace, recover_trace, baseDis):
    '''
    get the distance (error) between real and recovered base station for each time slot
    when the prediction is correct, the distance is zero.
    :param real_trace: a list, original trajectory's accessed base stations in temporal order
    :param recover_trace: a list, recovered trajectory's accessed base stations in temporal order
    :param baseDis: a dict, baseDis[(base1, base2)] = distance requiring that base1 is smaller than base2
                    where base1 and base2 are both int
    :return: dis: a list, every item is float and
                   represents the distance (error) between real and recovered base station for a time slot
    '''

    dis = []
    N = len(real_trace)
    for k1, k2 in zip(real_trace, recover_trace):
        if k1 == k2:
            dis.append(0)
        elif k1 > k2:
            k1, k2 = k2, k1
            dis.append((baseDis[k1-1][k2-k1-1])**1)
        else:
            dis.append((baseDis[k1-1][k2-k1-1])**1)
    return dis

def main():
    # set parameters
    usernum = 1000
    day_num = 0
    time_gra = 30
    period = 'night'  # 'daytime', 'day', 'week'
    k = 6*60/time_gra
    k1 = 24*60/time_gra
    tra_path = 'data\\trace_base'
    recoverTra_path = 'recovery results\\week'

    baseDis = getBaseDis()
    real_trace, _ = getTrajectory(tra_path)
    recover_trace, _ = getTrajectory(recoverTra_path)

    if period == 'week':
        time_range = [0, 7*k1]
    if period == 'daytime':
        recover_trace = [x[day_num*k1:(day_num+1)*k1] for x in recover_trace]
        real_trace = [x[day_num*k1:(day_num+1)*k1] for x in real_trace]
        time_range = [day_num*k1, (day_num+1)*k1]
    if period == 'night':
        recover_trace = [x[day_num*k1:day_num*k1+k] for x in recover_trace]
        real_trace = [x[day_num*k1:day_num*k1+k] for x in real_trace]
        time_range = [day_num*k1, day_num*k1+k]

    average_accuracy, average_error = getAccuracy(recover_trace, real_trace, baseDis)

    f1 = open('results.txt', 'a')
    f1.write(str(usernum)+' '+str(time_range[0])+' '+str(time_range[1])+'\n')
    f1.write(str(average_accuracy)+' '+str(average_error)+'\n')
    f1.write('\n')
    f1.close()


if __name__ == "__main__":
    main()